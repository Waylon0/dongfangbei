"""演示脚本 — 分步展示断层多边形自动追踪流水线

用于比赛汇报/答辩。每一步都生成图片，
可以直接放进 PPT 里逐页讲解。
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from config import Config
from src.preprocess import normalize
from src.segment import segment_fault_regions
from src.polygon_extract import extract_fault_polygons
from src.vectorize import simplify_polygon, filter_by_area, polygon_area
from skimage.measure import find_contours
from skimage.morphology import skeletonize as skel_morph
from scipy.ndimage import gaussian_filter

os.makedirs('demo_output', exist_ok=True)


# ============================================================
#  第0步：生成演示用的合成数据
# ============================================================
def generate_demo_data():
    """生成包含多种断层形态的演示数据：
    - 一条主断层（贯穿）
    - 一条分支断层（Y字形交叉）
    - 两条相交断层（X形交叉）
    - 一条孤立小断层
    """
    h, w = 300, 400
    data = np.full((h, w), 0.05)
    rng = np.random.default_rng(42)

    # 添加轻微随机噪声
    data += rng.normal(0, 0.02, (h, w))

    # 断层1: 主断层（贯穿南北，略有弯曲）
    cx = np.linspace(100, 300, h) + 30 * np.sin(np.linspace(0, 2 * np.pi, h))
    for r in range(h):
        c = int(cx[r])
        _paint_spot(data, r, c, radius=5, strength=0.9)

    # 断层2: 分支（从主断层分叉出去，Y形交叉）
    branch_start = 120
    for i in range(branch_start, 260):
        r = int(branch_start + i * 0.6)
        c = int(cx[branch_start] + (i - 80) * 1.2)
        if 0 <= r < h and 0 <= c < w:
            _paint_spot(data, r, c, radius=3, strength=0.7)

    # 断层3+4: 两条相交断层（X形交叉）
    for i in range(180):
        r = 80 + i
        c = 50 + i
        if 0 <= r < h and 0 <= c < w:
            _paint_spot(data, r, c, radius=3, strength=0.8)
    for i in range(180):
        r = 80 + i
        c = 230 - i
        if 0 <= r < h and 0 <= c < w:
            _paint_spot(data, r, c, radius=3, strength=0.8)

    # 断层5: 孤立小断层
    for i in range(50):
        r = int(230 + i * 0.7)
        c = int(300 + 20 * np.sin(i * 0.1))
        if 0 <= r < h and 0 <= c < w:
            _paint_spot(data, r, c, radius=2, strength=0.5)

    return np.clip(data, 0, 1)


def _paint_spot(data, r, c, radius=3, strength=1.0):
    """在指定位置画一个高斯衰减的斑点"""
    h, w = data.shape
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            rr, cc = r + dr, c + dc
            if 0 <= rr < h and 0 <= cc < w:
                dist = np.sqrt(dr ** 2 + dc ** 2)
                wgt = np.exp(-0.5 * (dist / (radius / 2)) ** 2)
                data[rr, cc] = max(data[rr, cc], strength * wgt)


# ============================================================
#  下面的函数每调用一次 = 演示的一页
# ============================================================

def step1_raw_data(data, save_path):
    """第1步：原始断层属性数据"""
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(data, cmap='seismic', aspect='auto', origin='upper',
                   vmin=0, vmax=1)
    plt.colorbar(im, ax=ax, label='Fault Likelihood')
    ax.set_title('Step 1: Input — Fault Attribute Data', fontsize=14)
    ax.set_xlabel('Inline')
    ax.set_ylabel('Crossline')
    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'  [Step 1] Saved: {save_path}')


def step2_preprocessed(data, binary, save_path):
    """第2步：预处理 — 去噪 + 二值化"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].imshow(data, cmap='seismic', aspect='auto', origin='upper')
    axes[0].set_title('After Gaussian Smoothing', fontsize=13)

    axes[1].imshow(binary, cmap='gray', aspect='auto', origin='upper')
    axes[1].set_title('After Otsu Binarization', fontsize=13)

    fig.suptitle('Step 2: Preprocessing', fontsize=15)
    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'  [Step 2] Saved: {save_path}')


def step3_morphology(binary_before, binary_after, save_path):
    """第3步：形态学处理 — 闭运算填孔 + 开运算去噪"""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    axes[0].imshow(binary_before, cmap='gray', aspect='auto', origin='upper')
    axes[0].set_title('Before Morphology', fontsize=13)

    # 差异图：新增/移除的像素
    diff = binary_after.astype(int) - binary_before.astype(int)
    axes[1].imshow(binary_after, cmap='gray', aspect='auto', origin='upper')
    axes[1].set_title('After Closing + Opening', fontsize=13)

    axes[2].imshow(diff, cmap='RdBu', aspect='auto', origin='upper', vmin=-1, vmax=1)
    axes[2].set_title('Changes (blue=added, red=removed)', fontsize=13)

    fig.suptitle('Step 3: Morphological Processing', fontsize=15)
    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'  [Step 3] Saved: {save_path}')


def step4_contours(binary, contours, save_path):
    """第4步：轮廓提取 — 连通域分析 + 闭合轮廓"""
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.imshow(binary, cmap='gray', aspect='auto', origin='upper', alpha=0.5)

    colors = cm.tab10.colors
    for i, c in enumerate(contours):
        pts = np.array(c)
        color = colors[i % len(colors)]
        ax.plot(pts[:, 1], pts[:, 0], color=color, linewidth=2.5,
                label=f'Contour {i + 1}')
        # 标记起点，验证闭合
        ax.scatter(pts[0, 1], pts[0, 0], color=color, s=50, zorder=5)

    ax.set_title(f'Step 4: Contour Extraction — {len(contours)} Closed Polygons Found',
                 fontsize=14)
    ax.set_xlabel('Inline')
    ax.set_ylabel('Crossline')
    ax.legend(fontsize=8, loc='upper right')
    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'  [Step 4] Saved: {save_path}')


def step5_intersection_handling(binary, save_path):
    """第5步：交叉断层处理 — 骨架化 + 交叉点检测"""
    region = binary
    skel = skel_morph(region)
    junctions = _find_junctions(skel)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].imshow(region, cmap='gray', aspect='auto', origin='upper')
    axes[0].set_title('Connected Fault Region', fontsize=13)

    axes[1].imshow(skel, cmap='gray', aspect='auto', origin='upper')
    for r, c in junctions:
        axes[1].scatter(c, r, color='red', s=60, zorder=5, marker='X')
    axes[1].set_title(f'Skeleton + Junctions ({len(junctions)} detected)',
                      fontsize=13)

    fig.suptitle('Step 5: Intersection Detection & Separation', fontsize=15)
    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'  [Step 5] Saved: {save_path}')


def _find_junctions(skel):
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


def step6_final(data, filtered, save_path):
    """第6步：最终结果 — 简化平滑后的多边形叠加在原始数据上"""
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.imshow(data, cmap='seismic', aspect='auto', origin='upper', alpha=0.6)

    colors = cm.tab10.colors
    for i, poly in enumerate(filtered):
        color = colors[i % len(colors)]
        area = polygon_area(poly)
        ax.plot(poly[:, 1], poly[:, 0], color=color, linewidth=2.5,
                label=f'Fault {i + 1} ({area:.0f} px²)')
        ax.fill(poly[:, 1], poly[:, 0], color=color, alpha=0.15)

    ax.set_title(f'Step 6: Final Result — {len(filtered)} Fault Polygons',
                 fontsize=14)
    ax.set_xlabel('Inline')
    ax.set_ylabel('Crossline')
    ax.legend(fontsize=8, loc='upper right')
    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'  [Step 6] Saved: {save_path}')


def step7_overview(data, binary, filtered, save_path):
    """第7步：总览图 — 全部流程一页展示，适合放汇报末尾"""
    fig = plt.figure(figsize=(16, 12))

    # 1. 原始数据
    ax1 = fig.add_subplot(2, 3, 1)
    ax1.imshow(data, cmap='seismic', aspect='auto', origin='upper')
    ax1.set_title('① Input Attribute Data', fontsize=12)

    # 2. 二值化
    ax2 = fig.add_subplot(2, 3, 2)
    ax2.imshow(binary, cmap='gray', aspect='auto', origin='upper')
    ax2.set_title('② Binary Segmentation', fontsize=12)

    # 3. 原始轮廓
    ax3 = fig.add_subplot(2, 3, 3)
    ax3.imshow(binary, cmap='gray', aspect='auto', origin='upper', alpha=0.4)
    raw_contours = find_contours(binary.astype(float), level=0.5)
    for c in raw_contours:
        ax3.plot(c[:, 1], c[:, 0], 'cyan', linewidth=0.8)
    ax3.set_title('③ Raw Contours', fontsize=12)

    # 4. 简化后
    ax4 = fig.add_subplot(2, 3, 4)
    ax4.imshow(data, cmap='seismic', aspect='auto', origin='upper', alpha=0.4)
    for poly in filtered:
        ax4.plot(poly[:, 1], poly[:, 0], linewidth=2)
    ax4.set_title('④ Simplified Polygons', fontsize=12)

    # 5. 面积分布
    ax5 = fig.add_subplot(2, 3, 5)
    areas = [polygon_area(p) for p in filtered]
    colors = cm.tab10.colors
    bars = ax5.bar(range(len(areas)), sorted(areas, reverse=True),
                   color=[colors[i % len(colors)] for i in range(len(areas))])
    ax5.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='min_area=50')
    ax5.set_xlabel('Polygon Rank')
    ax5.set_ylabel('Area (px²)')
    ax5.set_title('⑤ Area Distribution', fontsize=12)
    ax5.legend()

    # 6. 最终结果
    ax6 = fig.add_subplot(2, 3, 6)
    ax6.imshow(data, cmap='seismic', aspect='auto', origin='upper', alpha=0.5)
    for i, poly in enumerate(filtered):
        color = colors[i % len(colors)]
        ax6.plot(poly[:, 1], poly[:, 0], color=color, linewidth=2.5)
        ax6.fill(poly[:, 1], poly[:, 0], color=color, alpha=0.15)
    ax6.set_title(f'⑥ Final: {len(filtered)} Fault Polygons', fontsize=12)

    fig.suptitle('Fault Polygon Automatic Tracking — Pipeline Overview',
                 fontsize=16, fontweight='bold')
    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'  [Step 7] Saved: {save_path}')


# ============================================================
#  主流程
# ============================================================
def main():
    print("=" * 60)
    print("  断层多边形自动追踪 — 分步演示")
    print("=" * 60)
    print()

    cfg = Config()

    # 生成数据
    print("Generating demonstration data with multiple fault types...")
    data = generate_demo_data()
    print(f"  Shape: {data.shape}, Range: [{data.min():.3f}, {data.max():.3f}]")
    print(f"  Fault types: main fault, Y-branch, X-intersection, isolated fault")
    print()

    # --- 第1步：原始数据 ---
    print("Step 1/7: Display raw attribute data")
    step1_raw_data(data, 'demo_output/step1_raw_data.png')

    # --- 第2步：预处理 ---
    print("Step 2/7: Preprocessing (Gaussian + Otsu)")
    smoothed = normalize(data)
    smoothed = gaussian_filter(smoothed, sigma=cfg.gaussian_sigma)
    from skimage.filters import threshold_otsu
    thresh = threshold_otsu(smoothed) * cfg.otsu_scale
    binary_before_morph = (smoothed >= thresh).astype(np.uint8)
    step2_preprocessed(data, binary_before_morph, 'demo_output/step2_preprocessed.png')

    # --- 第3步：形态学处理 ---
    print("Step 3/7: Morphological processing (closing + opening)")
    binary = segment_fault_regions(data,
                                    sigma=cfg.gaussian_sigma,
                                    otsu_scale=cfg.otsu_scale,
                                    closing_radius=cfg.closing_radius,
                                    opening_radius=cfg.opening_radius)
    step3_morphology(binary_before_morph, binary, 'demo_output/step3_morphology.png')

    # --- 第4步：轮廓提取 ---
    print("Step 4/7: Contour extraction")
    contours = extract_fault_polygons(binary,
                                       min_component_area=cfg.min_component_area,
                                       separate_intersections=cfg.separate_intersections,
                                       smooth_sigma=cfg.contour_smooth_sigma)
    step4_contours(binary, contours, 'demo_output/step4_contours.png')
    print(f"  Extracted {len(contours)} contours")

    # --- 第5步：交叉处理 ---
    print("Step 5/7: Intersection handling demonstration")
    step5_intersection_handling(binary, 'demo_output/step5_intersections.png')

    # --- 第6步：最终结果 ---
    print("Step 6/7: Final result with simplified & smoothed polygons")
    vectorized = [simplify_polygon(c, cfg.dp_epsilon, cfg.smooth_iterations)
                  for c in contours]
    filtered = filter_by_area(vectorized, cfg.min_polygon_area)
    step6_final(data, filtered, 'demo_output/step6_final.png')

    areas = [polygon_area(p) for p in filtered]
    print(f"  Polygons: {len(filtered)}")
    print(f"  Areas: min={min(areas):.1f}, max={max(areas):.1f}, "
          f"mean={np.mean(areas):.1f}")

    # --- 第7步：总览 ---
    print("Step 7/7: Pipeline overview (one-page summary)")
    step7_overview(data, binary, filtered, 'demo_output/step7_overview.png')

    # --- 总结 ---
    print()
    print("=" * 60)
    print(f"  Demo complete!")
    print(f"  Output: demo_output/step1~7_*.png")
    print(f"  Use these images directly in your presentation slides.")
    print("=" * 60)


if __name__ == '__main__':
    main()
