"""主入口 — 断层多边形自动追踪流水线

基于平面断层属性数据，自动提取闭合的断层多边形。
"""

import os
import time
import numpy as np

from config import Config
from src.preprocess import normalize
from src.segment import segment_fault_regions
from src.polygon_extract import extract_fault_polygons
from src.vectorize import (simplify_polygon, filter_by_area,
                            polygon_area, export_geojson, export_polygons_txt)
from src.tracker import track_faults
from src.visualize import plot_result, plot_intermediate, plot_polygon_stats


def generate_synthetic_data(shape: tuple = (300, 400),
                             n_faults: int = 5,
                             noise_level: float = 0.03,
                             seed: int = 42) -> np.ndarray:
    """生成合成测试数据：包含更真实的断层高值区域。

    改进：
    - 断层可以是弯曲的（正弦扰动）
    - 不同断层宽度和强度有差异
    - 加入断缝（模拟真实断层不连续性）
    - 加入沿断层走向的强度渐变
    """
    rng = np.random.default_rng(seed)
    data = np.full(shape, 0.05)
    data += rng.normal(0, noise_level, shape)

    for _ in range(n_faults):
        # 随机生成弯曲断层线：用若干控制点 + 正弦扰动
        r1 = rng.integers(20, shape[0] - 20)
        c1 = rng.integers(0, shape[1] // 5)
        r2 = rng.integers(20, shape[0] - 20)
        c2 = rng.integers(4 * shape[1] // 5, shape[1] - 1)

        strength = rng.uniform(0.5, 0.95)
        width = rng.integers(3, 10)
        # 弯曲幅度和频率
        curvature_amp = rng.uniform(0, 30)
        curvature_freq = rng.uniform(0.005, 0.03)

        # 沿断层画弯曲线
        n_steps = int(max(abs(r2 - r1), abs(c2 - c1))) * 2
        for t in np.linspace(0, 1, n_steps):
            c_pos = c1 + t * (c2 - c1)
            r_base = r1 + t * (r2 - r1)
            # 正弦弯曲
            r_offset = curvature_amp * np.sin(2 * np.pi * curvature_freq * (c_pos - c1))
            r_pos = r_base + r_offset

            for wr in range(-width, width + 1):
                for wc in range(-width, width + 1):
                    rr = int(round(r_pos)) + wr
                    cc = int(round(c_pos)) + wc
                    if 0 <= rr < shape[0] and 0 <= cc < shape[1]:
                        dist = np.sqrt(wr ** 2 + wc ** 2)
                        wgt = np.exp(-0.5 * (dist / max(width, 1)) ** 2)
                        # 沿走向的强度渐变
                        grad = 0.7 + 0.3 * np.sin(np.pi * t)
                        data[rr, cc] = max(data[rr, cc], strength * wgt * grad)

        # 随机加入断缝（1-3个间隙）
        n_gaps = rng.integers(0, 3)
        for _ in range(n_gaps):
            gap_center = rng.uniform(0.2, 0.8)
            gap_width = rng.uniform(0.02, 0.06)
            t_lo, t_hi = gap_center - gap_width, gap_center + gap_width
            for t in np.linspace(max(0, t_lo), min(1, t_hi), 20):
                c_pos = c1 + t * (c2 - c1)
                r_base = r1 + t * (r2 - r1)
                r_offset = curvature_amp * np.sin(2 * np.pi * curvature_freq * (c_pos - c1))
                r_pos = r_base + r_offset
                for wr in range(-width - 2, width + 3):
                    for wc in range(-width - 2, width + 3):
                        rr = int(round(r_pos)) + wr
                        cc = int(round(c_pos)) + wc
                        if 0 <= rr < shape[0] and 0 <= cc < shape[1]:
                            data[rr, cc] = min(data[rr, cc], 0.1)

        # 随机添加分支
        if rng.random() > 0.5:
            branch_t = rng.uniform(0.3, 0.7)
            br = int(r1 + branch_t * (r2 - r1))
            bc = int(c1 + branch_t * (c2 - c1))
            mr = br + rng.integers(-40, 40)
            mc = bc + rng.integers(-40, 40)
            mr = np.clip(mr, 20, shape[0] - 20)
            mc = np.clip(mc, 10, shape[1] - 10)
            _draw_thick_line(data, br, bc, mr, mc,
                              strength=rng.uniform(0.3, 0.6),
                              width=rng.integers(2, 5))

    return np.clip(data, 0, 1)


def _draw_thick_line(data: np.ndarray, r1: int, c1: int,
                      r2: int, c2: int, strength: float = 1.0,
                      width: int = 3):
    """在数组上画具有一定宽度的线（模拟断层区域）"""
    h, w = data.shape
    dr = abs(r2 - r1)
    dc = abs(c2 - c1)
    sr = 1 if r1 < r2 else -1
    sc = 1 if c1 < c2 else -1
    err = dr - dc
    r, c = r1, c1

    while True:
        for wr in range(-width, width + 1):
            for wc in range(-width, width + 1):
                rr, cc = r + wr, c + wc
                if 0 <= rr < h and 0 <= cc < w:
                    dist = np.sqrt(wr ** 2 + wc ** 2)
                    wgt = np.exp(-0.5 * (dist / max(width, 1)) ** 2)
                    data[rr, cc] = max(data[rr, cc], strength * wgt)
        if r == r2 and c == c2:
            break
        e2 = 2 * err
        if e2 > -dc:
            err -= dc
            r += sr
        if e2 < dr:
            err += dr
            c += sc


def run_pipeline(attr_data: np.ndarray, cfg: Config = None) -> dict:
    """运行完整的断层多边形自动追踪流水线。

    返回字典，包含所有中间结果和最终输出。
    """
    if cfg is None:
        cfg = Config()

    t0 = time.perf_counter()

    # 步骤1+2：断层区域分割（阈值二值化 + 形态学处理）
    binary = segment_fault_regions(attr_data,
                                    sigma=cfg.gaussian_sigma,
                                    otsu_scale=cfg.otsu_scale,
                                    closing_radius=cfg.closing_radius,
                                    opening_radius=cfg.opening_radius)

    # 步骤3：断层追踪（连接断续片段）
    binary = track_faults(
        binary,
        max_link_distance=cfg.track_max_link_distance,
        angle_weight=cfg.track_angle_weight,
        min_segment_length=cfg.track_min_segment_length,
        dilate_radius=cfg.track_dilate_radius,
        dilate_iterations=cfg.track_dilate_iterations,
        raw_data=attr_data,
    )

    # 步骤4+5：多边形轮廓提取（连通域 + 交叉分离 + 轮廓追踪）
    contours = extract_fault_polygons(binary,
                                       min_component_area=cfg.min_component_area,
                                       separate_intersections=cfg.separate_intersections,
                                       smooth_sigma=cfg.contour_smooth_sigma)

    # 步骤5：矢量简化 + 平滑
    vectorized = [simplify_polygon(c, cfg.dp_epsilon, cfg.smooth_iterations)
                  for c in contours]

    # 步骤6：面积过滤
    filtered = filter_by_area(vectorized, cfg.min_polygon_area)

    elapsed = time.perf_counter() - t0

    return {
        'binary': binary,
        'contours': contours,
        'vectorized': vectorized,
        'filtered': filtered,
        'elapsed': elapsed,
    }


def main():
    # 确保输出目录存在
    os.makedirs('data', exist_ok=True)

    # 生成合成测试数据
    print("Generating synthetic test data...")
    data = generate_synthetic_data(
        shape=(300, 400),
        n_faults=5,
        noise_level=0.03,
        seed=42
    )
    print(f"  Data shape: {data.shape}, range: [{data.min():.3f}, {data.max():.3f}]")

    # 运行流水线
    cfg = Config()
    print("\nRunning fault polygon extraction pipeline...")
    result = run_pipeline(data, cfg)

    print(f"\n--- Results ---")
    print(f"  Elapsed: {result['elapsed']:.3f}s")
    print(f"  Binary mask pixels: {result['binary'].sum()}")
    print(f"  Raw contours: {len(result['contours'])}")
    print(f"  Vectorized polygons: {len(result['vectorized'])}")
    print(f"  After area filter: {len(result['filtered'])}")

    areas = [polygon_area(p) for p in result['filtered']]
    print(f"  Areas: min={min(areas):.1f}, max={max(areas):.1f}, "
          f"mean={np.mean(areas):.1f}, median={np.median(areas):.1f}")

    # 导出结果
    export_geojson(result['filtered'], 'data/fault_polygons.geojson')
    export_polygons_txt(result['filtered'], 'data/fault_polygons.txt')
    print("\n  Exported: data/fault_polygons.geojson, data/fault_polygons.txt")

    # 可视化
    print("\nGenerating visualizations...")
    plot_intermediate(data, result['binary'],
                       output_path='data/intermediate.png')
    plot_result(data, result['filtered'], result['binary'],
                 output_path='data/final_result.png')
    plot_polygon_stats(result['filtered'], output_path='data/polygon_stats.png')
    print("  Saved: data/intermediate.png, data/final_result.png, data/polygon_stats.png")

    print("\nDone!")


if __name__ == '__main__':
    main()
