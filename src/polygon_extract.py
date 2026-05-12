"""多边形轮廓提取模块

从断层区域掩膜中提取闭合的多边形轮廓：
1. 连通域分析 → 分离不同断层区域
2. 交叉断层分离 → 骨架化+交叉点检测分拆
3. 闭合轮廓追踪 → 每个区域的边界
"""

import numpy as np
from scipy.ndimage import label
from skimage.measure import find_contours
from skimage.morphology import skeletonize, disk
from skimage.segmentation import clear_border
from typing import List, Tuple


def extract_fault_polygons(binary_mask: np.ndarray,
                            min_component_area: int = 100,
                            separate_intersections: bool = True,
                            smooth_sigma: float = 2.0) -> List[List[Tuple[float, float]]]:
    """从断层区域掩膜提取闭合多边形轮廓。

    参数：
        binary_mask: 断层区域二值掩膜 (2D, 0/1)
        min_component_area: 最小连通域面积，小于此值的区域被丢弃
        separate_intersections: 是否在骨架交叉处分离不同断层
        smooth_sigma: 轮廓高斯平滑σ

    返回：
        多边形列表，每个多边形为 [(row, col), ...] 闭合轮廓点
    """
    # 步骤1：连通域分析
    labeled, n_features = label(binary_mask)

    contours = []
    for region_id in range(1, n_features + 1):
        region = (labeled == region_id)

        # 面积过滤
        if region.sum() < min_component_area:
            continue

        if separate_intersections:
            sub_regions = _separate_intersecting_faults(region)
            for sub in sub_regions:
                if sub.sum() >= min_component_area:
                    c = _extract_contour(sub, smooth_sigma)
                    if c is not None and len(c) >= 4:
                        contours.append(c)
        else:
            c = _extract_contour(region, smooth_sigma)
            if c is not None and len(c) >= 4:
                contours.append(c)

    return contours


def _separate_intersecting_faults(region: np.ndarray) -> List[np.ndarray]:
    """在骨架交叉点处分离连在一起的断层区域。

    思路：
    1. 对区域做骨架化
    2. 找到度数>=3的交叉点
    3. 在交叉点周围断开，分离出子区域
    4. 对每个子区域做膨胀恢复原宽度
    """
    skel = skeletonize(region)
    junctions = _find_junction_points(skel)

    if len(junctions) == 0:
        return [region]

    # 在交叉点处断开
    skel_split = skel.copy()
    h, w = skel.shape
    for r, c in junctions:
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                rr, cc = r + dr, c + dc
                if 0 <= rr < h and 0 <= cc < w:
                    skel_split[rr, cc] = 0

    # 从断开的骨架膨胀恢复区域
    from scipy.ndimage import distance_transform_edt
    from skimage.morphology import disk

    # 对每段骨架单独膨胀并mask回原区域
    labeled_skel, n = label(skel_split)
    sub_regions = []
    for skel_id in range(1, n + 1):
        skel_part = (labeled_skel == skel_id)
        if skel_part.sum() < 5:
            continue
        # 膨胀骨架
        dilated = _dilate_to_original(skel_part, region)
        if dilated.sum() > 5:
            sub_regions.append(dilated)

    return sub_regions if sub_regions else [region]


def _dilate_to_original(skel_part: np.ndarray,
                         original_region: np.ndarray) -> np.ndarray:
    """将骨架片段膨胀回原始区域的大小，但被原始区域边界裁剪"""
    from scipy.ndimage import distance_transform_edt, binary_dilation
    # 计算原始区域内各点到骨架的距离
    dist = distance_transform_edt(original_region)
    # 膨胀，但不超过原始区域边界
    dilated = binary_dilation(skel_part, structure=disk(3), iterations=5)
    return dilated & original_region


def _find_junction_points(skel: np.ndarray) -> List[Tuple[int, int]]:
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


def _extract_contour(region: np.ndarray,
                      smooth_sigma: float = 2.0) -> List[Tuple[float, float]]:
    """从二值区域提取最外层闭合轮廓。

    使用 marching squares 算法 (skimage.measure.find_contours)，
    返回最长的轮廓（即外围边界）。
    """
    from scipy.ndimage import gaussian_filter

    # 对区域边界做轻微平滑，减少锯齿
    region_f = region.astype(np.float64)
    if smooth_sigma > 0:
        region_f = gaussian_filter(region_f, sigma=smooth_sigma)

    contours = find_contours(region_f, level=0.5)

    if not contours:
        return None

    # 取最长的轮廓（外围边界）
    longest = max(contours, key=len)

    # 确保闭合：如果首尾距离 > 1像素，手动闭合
    pts = [(float(p[0]), float(p[1])) for p in longest]
    if len(pts) > 1:
        d = np.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])
        if d > 2.0:
            pts.append(pts[0])

    return pts
