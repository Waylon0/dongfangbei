"""全局侧边栏 — 数据加载 + 参数折叠面板 + 运行按钮"""

import streamlit as st
import numpy as np
from .param_controls import (
    init_params, reset_params, render_param_group,
    get_config_from_session, get_params_dict,
)

# 将项目根目录加入 sys.path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def render_sidebar() -> dict:
    """渲染整个侧边栏，返回用户操作状态。

    Returns:
        {'action': 'run'|'generate'|'upload'|None, 'data': np.ndarray|None}
    """
    init_params()

    with st.sidebar:
        _render_header()
        st.divider()

        action = _render_data_section()
        st.divider()

        _render_param_section()
        st.divider()

        _render_action_buttons()

    return action


def _render_header():
    st.markdown("""
    <div style="text-align:center; padding:10px 0;">
        <h2 style="margin:0; font-size:1.3rem;">🔬 断层多边形</h2>
        <p style="color:#8890A8; font-size:0.75rem; margin:0;">自动追踪系统 v2.0</p>
    </div>
    """, unsafe_allow_html=True)


def _render_data_section() -> dict:
    """数据加载区域"""
    st.markdown('### 📊 数据源')

    data_source = st.radio(
        '选择数据来源',
        ['合成测试数据', '上传属性文件'],
        label_visibility='collapsed',
    )

    if data_source == '合成测试数据':
        col1, col2 = st.columns(2)
        with col1:
            shape_r = st.number_input('行数', 100, 800, 300, 50, key='syn_rows')
        with col2:
            shape_c = st.number_input('列数', 100, 1000, 400, 50, key='syn_cols')
        col1, col2 = st.columns(2)
        with col1:
            n_faults = st.number_input('断层数量', 1, 20, 5, 1, key='syn_nfaults')
        with col2:
            noise = st.slider('噪声水平', 0.0, 0.2, 0.03, 0.01, key='syn_noise')
        seed = st.number_input('随机种子', 0, 999, 42, 1, key='syn_seed')

        if st.button('🎲 生成合成数据', use_container_width=True):
            from main import generate_synthetic_data
            data = generate_synthetic_data(
                shape=(shape_r, shape_c),
                n_faults=n_faults,
                noise_level=noise,
                seed=seed,
            )
            st.session_state['raw_data'] = data
            st.success(f'已生成 {data.shape} 数据')
            return {'action': 'generate', 'data': data}

    else:
        uploaded = st.file_uploader(
            '上传 .npy 或 .npz 文件',
            type=['npy', 'npz'],
            key='file_upload',
        )
        if uploaded is not None:
            try:
                if uploaded.name.endswith('.npz'):
                    d = np.load(uploaded)
                    key = list(d.keys())[0]
                    data = d[key].astype(np.float64)
                else:
                    data = np.load(uploaded).astype(np.float64)
                st.session_state['raw_data'] = data
                st.success(f'已加载 {data.shape}, range=[{data.min():.3f}, {data.max():.3f}]')
                return {'action': 'upload', 'data': data}
            except Exception as e:
                st.error(f'加载失败: {e}')

    # 显示当前数据信息
    if 'raw_data' in st.session_state and st.session_state['raw_data'] is not None:
        data = st.session_state['raw_data']
        st.caption(f'当前数据: {data.shape} | [{data.min():.3f}, {data.max():.3f}]')

    return {'action': None, 'data': None}


def _render_param_section():
    """参数折叠面板"""
    st.markdown('### ⚙️ 算法参数')

    # 每组参数用 expander 折叠
    groups = [
        ('🔧 预处理参数', '预处理'),
        ('✂️ 分割参数', '分割'),
        ('🔍 提取参数', '提取'),
        ('🔗 追踪参数', '追踪'),
        ('📐 简化/过滤', '简化'),
    ]
    for label, group_name in groups:
        with st.expander(label, expanded=(group_name == '分割')):
            render_param_group(group_name)
            if group_name == '简化':
                render_param_group('过滤')

    col1, col2 = st.columns(2)
    with col1:
        if st.button('🔄 重置默认', use_container_width=True):
            reset_params()
            st.rerun()


def _render_action_buttons():
    """操作按钮区"""
    st.markdown('### 🚀 执行')

    disabled = 'raw_data' not in st.session_state
    if st.button('▶️ 运行断层追踪', type='primary', use_container_width=True,
                 disabled=disabled):
        st.session_state['_trigger_run'] = True

    # 导出按钮（仅在有结果时显示）
    if 'pipeline_result' in st.session_state and st.session_state['pipeline_result'] is not None:
        result = st.session_state['pipeline_result']
        if result.get('filtered'):
            import json

            polygons = result['filtered']
            geojson_data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[float(pt[1]), float(pt[0])] for pt in poly]]
                        },
                        "properties": {"id": i, "area_pixels": float(
                            sum(0.5 * abs(
                                poly[j, 1] * poly[(j + 1) % len(poly), 0] -
                                poly[j, 0] * poly[(j + 1) % len(poly), 1]
                            ) for j in range(len(poly)))
                        )}
                    }
                    for i, poly in enumerate(polygons) if len(poly) >= 3
                ]
            }
            geojson_str = json.dumps(geojson_data, indent=2, ensure_ascii=False)
            st.download_button(
                '📥 下载 GeoJSON', geojson_str,
                file_name='fault_polygons.geojson',
                mime='application/geo+json',
                use_container_width=True,
            )
