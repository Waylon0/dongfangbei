"""流水线 API 端点"""

import sys
import json
import time
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from src.preprocess import normalize
from src.segment import segment_fault_regions
from src.polygon_extract import extract_fault_polygons
from src.vectorize import simplify_polygon, filter_by_area, polygon_area
from src.tracker import track_faults
from src.multiscale import merge_multiscale_results
from scipy.ndimage import gaussian_filter
from skimage.filters import threshold_otsu, threshold_local
from skimage.morphology import skeletonize


router = APIRouter()


class PipelineParams(BaseModel):
    gaussian_sigma: float = 1.5
    use_clahe: bool = False
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8
    otsu_scale: float = 1.0
    use_adaptive_threshold: bool = False
    adaptive_block_size: int = 35
    adaptive_c: float = 0.0
    closing_radius: int = 5
    opening_radius: int = 2
    min_component_area: int = 100
    separate_intersections: bool = True
    contour_smooth_sigma: float = 2.0
    min_polygon_area: float = 50
    dp_epsilon: float = 3.0
    smooth_iterations: int = 2
    scales: list = [1.0, 2.0]
    dedup_overlap_threshold: float = 0.5
    track_max_link_distance: float = 30.0
    track_angle_weight: float = 2.0
    track_min_segment_length: int = 10
    track_dilate_radius: int = 3
    track_dilate_iterations: int = 5


class PipelineRequest(BaseModel):
    data: list
    params: PipelineParams = PipelineParams()


class GenerateRequest(BaseModel):
    rows: int = 300
    cols: int = 400
    n_faults: int = 5
    noise_level: float = 0.03
    seed: int = 42


def _config_from_params(p: PipelineParams) -> Config:
    cfg = Config()
    cfg.gaussian_sigma = p.gaussian_sigma
    cfg.use_clahe = p.use_clahe
    cfg.clahe_clip_limit = p.clahe_clip_limit
    cfg.clahe_grid_size = p.clahe_grid_size
    cfg.otsu_scale = p.otsu_scale
    cfg.use_adaptive_threshold = p.use_adaptive_threshold
    cfg.adaptive_block_size = p.adaptive_block_size
    cfg.adaptive_c = p.adaptive_c
    cfg.closing_radius = p.closing_radius
    cfg.opening_radius = p.opening_radius
    cfg.min_component_area = p.min_component_area
    cfg.separate_intersections = p.separate_intersections
    cfg.contour_smooth_sigma = p.contour_smooth_sigma
    cfg.min_polygon_area = p.min_polygon_area
    cfg.dp_epsilon = p.dp_epsilon
    cfg.smooth_iterations = p.smooth_iterations
    cfg.scales = p.scales
    cfg.dedup_overlap_threshold = p.dedup_overlap_threshold
    cfg.track_max_link_distance = p.track_max_link_distance
    cfg.track_angle_weight = p.track_angle_weight
    cfg.track_min_segment_length = p.track_min_segment_length
    cfg.track_dilate_radius = p.track_dilate_radius
    cfg.track_dilate_iterations = p.track_dilate_iterations
    return cfg


def _find_junctions(skel: np.ndarray) -> list:
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


def _serialize_array(arr) -> list:
    if isinstance(arr, np.ndarray):
        if arr.dtype == bool:
            return arr.astype(int).tolist()
        return arr.tolist()
    return arr


def _serialize_contours(contours: list) -> list:
    result = []
    for c in contours:
        arr = np.array(c) if not isinstance(c, np.ndarray) else c
        result.append(arr.tolist())
    return result


@router.post("/api/pipeline")
def run_pipeline(req: PipelineRequest):
    """运行完整断层多边形追踪流水线，返回每步中间数据"""
    try:
        data = np.array(req.data, dtype=np.float64)
        if data.ndim != 2:
            raise HTTPException(400, "data must be a 2D array")
    except Exception as e:
        raise HTTPException(400, f"Invalid data: {e}")

    cfg = _config_from_params(req.params)
    t0 = time.perf_counter()
    data_norm = normalize(data)

    # 步骤1-2: 二值分割（阈值前）
    smoothed = gaussian_filter(data_norm, sigma=cfg.gaussian_sigma)
    if cfg.use_adaptive_threshold:
        block = max(3, cfg.adaptive_block_size)
        if block % 2 == 0:
            block += 1
        img_uint8 = (smoothed * 255).astype(np.uint8)
        local_thresh = threshold_local(img_uint8, block, method='gaussian',
                                        offset=cfg.adaptive_c * 255)
        binary_before_morph = (smoothed >= (local_thresh / 255.0)).astype(np.uint8)
    else:
        thresh = threshold_otsu(smoothed) * cfg.otsu_scale
        binary_before_morph = (smoothed >= thresh).astype(np.uint8)

    # 步骤3: 形态学处理
    binary = segment_fault_regions(
        data, sigma=cfg.gaussian_sigma, otsu_scale=cfg.otsu_scale,
        closing_radius=cfg.closing_radius, opening_radius=cfg.opening_radius,
        use_adaptive_threshold=cfg.use_adaptive_threshold,
        adaptive_block_size=cfg.adaptive_block_size, adaptive_c=cfg.adaptive_c,
    )

    # 步骤3.5: 断层追踪
    binary_before_track = binary.copy()
    binary = track_faults(
        binary, max_link_distance=cfg.track_max_link_distance,
        angle_weight=cfg.track_angle_weight,
        min_segment_length=cfg.track_min_segment_length,
        dilate_radius=cfg.track_dilate_radius,
        dilate_iterations=cfg.track_dilate_iterations,
        raw_data=data,
    )

    # 步骤4: 轮廓提取
    contours = extract_fault_polygons(
        binary, min_component_area=cfg.min_component_area,
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
    filtered = filter_by_area(vectorized, cfg.min_polygon_area)
    areas = [polygon_area(p) for p in filtered]

    # 多尺度融合
    if cfg.scales and len(cfg.scales) > 1:
        all_polygons = [filtered]
        all_areas_list = [areas]
        for scale_sigma in cfg.scales[1:]:
            binary_s = segment_fault_regions(
                data, sigma=scale_sigma, otsu_scale=cfg.otsu_scale,
                closing_radius=cfg.closing_radius, opening_radius=cfg.opening_radius,
            )
            binary_s = track_faults(
                binary_s, max_link_distance=cfg.track_max_link_distance,
                angle_weight=cfg.track_angle_weight,
                min_segment_length=cfg.track_min_segment_length,
                dilate_radius=cfg.track_dilate_radius,
                dilate_iterations=cfg.track_dilate_iterations,
                raw_data=data,
            )
            contours_s = extract_fault_polygons(
                binary_s, min_component_area=cfg.min_component_area,
                separate_intersections=cfg.separate_intersections,
                smooth_sigma=cfg.contour_smooth_sigma,
            )
            vectorized_s = [simplify_polygon(c, cfg.dp_epsilon, cfg.smooth_iterations)
                            for c in contours_s]
            filtered_s = filter_by_area(vectorized_s, cfg.min_polygon_area)
            areas_s = [polygon_area(p) for p in filtered_s]
            all_polygons.append(filtered_s)
            all_areas_list.append(areas_s)
        filtered, areas = merge_multiscale_results(
            all_polygons, all_areas_list, cfg.dedup_overlap_threshold)

    elapsed = time.perf_counter() - t0

    return {
        'data_smoothed': _serialize_array(smoothed),
        'binary_before_morph': _serialize_array(binary_before_morph),
        'binary': _serialize_array(binary),
        'binary_before_track': _serialize_array(binary_before_track),
        'skeleton': _serialize_array(skel),
        'junctions': junctions,
        'contours': _serialize_contours(contours),
        'vectorized': _serialize_contours(vectorized),
        'filtered': _serialize_contours(filtered),
        'areas': areas,
        'elapsed': round(elapsed, 3),
    }


@router.post("/api/generate")
def generate_data(req: GenerateRequest):
    """生成合成测试数据"""
    from main import generate_synthetic_data
    data = generate_synthetic_data(
        shape=(req.rows, req.cols),
        n_faults=req.n_faults,
        noise_level=req.noise_level,
        seed=req.seed,
    )
    return {
        'data': _serialize_array(data),
        'shape': list(data.shape),
        'min': float(data.min()),
        'max': float(data.max()),
    }
