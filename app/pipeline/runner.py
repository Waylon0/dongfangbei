"""桥接现有 src/ 模块的流水线封装

扩展 run_pipeline()，额外返回分步展示所需的中间数据。
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.filters import threshold_otsu
from skimage.morphology import skeletonize

from config import Config
from src.preprocess import normalize
from src.segment import segment_fault_regions
from src.polygon_extract import extract_fault_polygons
from src.vectorize import simplify_polygon, filter_by_area, polygon_area


def _find_junctions(skel: np.ndarray) -> list:
    """找骨架图中的交叉点（度数 >= 3）"""
    coords = np.argwhere(skel > 0)
    junctions = []
    h, w = skel.shape
    for r, c in coords:
        r, c = int(r), int(c)
        cnt = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr, cc = r + dr, c + dc
                if 0 <= rr < h and 0 <= cc < w and skel[rr, cc]:
                    cnt += 1
        if cnt >= 3:
            junctions.append((r, c))
    return junctions


def run_pipeline_with_steps(data: np.ndarray, cfg: Config = None) -> dict:
    """运行完整流水线并返回每步中间数据。

    Returns:
        dict with keys:
        - binary: 二值掩膜
        - binary_before_morph: 形态学前的二值图
        - data_smoothed: 高斯平滑后的数据
        - contours: 原始轮廓列表
        - skeleton: 骨架图
        - junctions: 交叉点列表
        - vectorized: 矢量简化后的多边形
        - filtered: 面积过滤后的多边形
        - areas: 面积列表
        - elapsed: 运行时间(秒)
    """
    if cfg is None:
        cfg = Config()

    t0 = time.perf_counter()
    data_norm = normalize(data)

    # 步骤1-2: 二值分割
    smoothed = gaussian_filter(data_norm, sigma=cfg.gaussian_sigma)
    thresh = threshold_otsu(smoothed) * cfg.otsu_scale
    binary_before_morph = (smoothed >= thresh).astype(np.uint8)

    # 步骤3: 形态学处理
    binary = segment_fault_regions(
        data,
        sigma=cfg.gaussian_sigma,
        otsu_scale=cfg.otsu_scale,
        closing_radius=cfg.closing_radius,
        opening_radius=cfg.opening_radius,
    )

    # 步骤4: 轮廓提取
    contours = extract_fault_polygons(
        binary,
        min_component_area=cfg.min_component_area,
        separate_intersections=cfg.separate_intersections,
        smooth_sigma=cfg.contour_smooth_sigma,
    )

    # 步骤5: 骨架 + 交叉点
    skel = skeletonize(binary.astype(bool))
    junctions = _find_junctions(skel)

    # 步骤6: 矢量简化 + 平滑
    vectorized = [
        simplify_polygon(c, cfg.dp_epsilon, cfg.smooth_iterations)
        for c in contours
    ]

    # 面积过滤
    filtered = filter_by_area(vectorized, cfg.min_polygon_area)
    areas = [polygon_area(p) for p in filtered]

    elapsed = time.perf_counter() - t0

    return {
        'binary': binary,
        'binary_before_morph': binary_before_morph,
        'data_smoothed': smoothed,
        'contours': contours,
        'skeleton': skel,
        'junctions': junctions,
        'vectorized': vectorized,
        'filtered': filtered,
        'areas': areas,
        'elapsed': elapsed,
    }
