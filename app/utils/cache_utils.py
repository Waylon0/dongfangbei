"""Streamlit 缓存工具"""

import hashlib
import json

import streamlit as st
import numpy as np


def params_to_hash(cfg, data_shape: tuple) -> str:
    """将配置参数和数据形状哈希为短字符串。"""
    d = {
        'gaussian_sigma': cfg.gaussian_sigma,
        'use_clahe': cfg.use_clahe,
        'clahe_clip_limit': cfg.clahe_clip_limit,
        'clahe_grid_size': cfg.clahe_grid_size,
        'otsu_scale': cfg.otsu_scale,
        'closing_radius': cfg.closing_radius,
        'opening_radius': cfg.opening_radius,
        'min_component_area': cfg.min_component_area,
        'separate_intersections': cfg.separate_intersections,
        'contour_smooth_sigma': cfg.contour_smooth_sigma,
        'dp_epsilon': cfg.dp_epsilon,
        'smooth_iterations': cfg.smooth_iterations,
        'min_polygon_area': cfg.min_polygon_area,
        'data_shape': list(data_shape),
    }
    raw = json.dumps(d, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def data_to_hash(data: np.ndarray) -> str:
    """将 numpy 数组哈希为短字符串（仅用于小数据缓存 key）。"""
    subset = data[::4, ::4] if data.size > 100000 else data
    return hashlib.md5(subset.tobytes()).hexdigest()[:12]


@st.cache_data(ttl=600, show_spinner="正在运行断层追踪流水线...")
def cached_run_pipeline(data_bytes: bytes, data_shape: tuple, params_key: str,
                        **params_kwargs) -> dict:
    """带缓存的流水线运行。

    Args:
        data_bytes: numpy 数组的序列化字节
        data_shape: 用于反序列化
        params_key: 参数哈希（用于缓存失效）
        params_kwargs: 传递给 Config 的具体参数值
    """
    from config import Config
    from app.pipeline.runner import run_pipeline_with_steps

    data = np.frombuffer(data_bytes, dtype=np.float64).reshape(data_shape)

    cfg = Config()
    for k, v in params_kwargs.items():
        if hasattr(cfg, k):
            setattr(cfg, k, v)

    return run_pipeline_with_steps(data, cfg)
