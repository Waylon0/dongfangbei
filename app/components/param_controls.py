"""参数控件工厂 — 从 session_state 读写所有参数"""

import streamlit as st

PARAM_DEFS = [
    # (key, label, min, max, step, default, group)
    ('gaussian_sigma', '高斯滤波 σ', 0.1, 5.0, 0.1, 1.5, '预处理'),
    ('use_clahe', 'CLAHE 对比度增强', None, None, None, False, '预处理'),
    ('clahe_clip_limit', 'CLAHE clip limit', 0.5, 5.0, 0.5, 2.0, '预处理'),
    ('clahe_grid_size', 'CLAHE grid size', 4, 32, 4, 8, '预处理'),
    ('otsu_scale', 'Otsu 阈值缩放', 0.2, 3.0, 0.1, 1.0, '分割'),
    ('closing_radius', '闭运算半径', 0, 20, 1, 5, '分割'),
    ('opening_radius', '开运算半径', 0, 15, 1, 2, '分割'),
    ('min_component_area', '最小连通域面积', 10, 500, 10, 100, '提取'),
    ('separate_intersections', '分离交叉断层', None, None, None, True, '提取'),
    ('contour_smooth_sigma', '轮廓平滑 σ', 0.0, 5.0, 0.5, 2.0, '提取'),
    ('dp_epsilon', 'DP 简化容差', 0.5, 10.0, 0.5, 3.0, '简化'),
    ('smooth_iterations', 'Chaikin 平滑迭代', 0, 8, 1, 2, '简化'),
    ('min_polygon_area', '最小多边形面积', 10.0, 500.0, 10.0, 50.0, '过滤'),
]


def init_params():
    """初始化所有参数到 session_state（仅首次）"""
    for key, _, _, _, _, default, _ in PARAM_DEFS:
        if key not in st.session_state:
            st.session_state[key] = default


def reset_params():
    """重置所有参数为默认值"""
    for key, _, _, _, _, default, _ in PARAM_DEFS:
        st.session_state[key] = default


def render_param_group(group_name: str):
    """渲染一组参数控件。

    group_name: '预处理' / '分割' / '提取' / '简化' / '过滤'
    """
    params = [p for p in PARAM_DEFS if p[6] == group_name]
    for p in params:
        key, label, vmin, vmax, step, default, _ = p
        current = st.session_state.get(key, default)
        if isinstance(default, bool):
            st.toggle(label, value=current, key=key,
                      help=f'默认: {default}')
        elif isinstance(default, float):
            st.slider(label, vmin, vmax, current, step, key=key,
                      help=f'默认: {default}')
        elif isinstance(default, int):
            st.number_input(label, vmin, vmax, current, step, key=key,
                            help=f'默认: {default}')


def get_config_from_session():
    """从 session_state 重建 Config 对象"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from config import Config

    cfg = Config()
    for key, _, _, _, _, default, _ in PARAM_DEFS:
        val = st.session_state.get(key, default)
        setattr(cfg, key, val)
    return cfg


def get_params_dict():
    """返回所有参数的扁平字典"""
    return {p[0]: st.session_state.get(p[0], p[5]) for p in PARAM_DEFS}
