"""Page 2: 参数调节 — 实时滑块调参 + 即时结果预览"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import numpy as np

from app.components.param_controls import (
    render_param_group, get_config_from_session, get_params_dict,
    reset_params,
)
from app.pipeline.runner import run_pipeline_with_steps
from app.viz.plotly_figs import fig_result_overlay, fig_area_histogram


def main():
    st.title('参数调节')

    data = st.session_state.get('raw_data')
    if data is None:
        st.info('👈 请先在**首页**加载数据')
        return

    left, right = st.columns([1, 2])

    with left:
        st.markdown('### ⚙️ 参数设置')

        with st.expander('🔧 预处理', expanded=True):
            render_param_group('预处理')
        with st.expander('✂️ 分割', expanded=True):
            render_param_group('分割')
        with st.expander('🔍 提取', expanded=True):
            render_param_group('提取')
        with st.expander('📐 简化/过滤', expanded=True):
            render_param_group('简化')
            render_param_group('过滤')

        col1, col2 = st.columns(2)
        with col1:
            if st.button('🔄 重置默认', use_container_width=True):
                reset_params()
                st.rerun()
        with col2:
            auto_run = st.toggle('自动运行', True, help='参数改变后自动重新追踪')

        run_clicked = st.button('▶️ 手动运行', type='primary', use_container_width=True,
                               disabled=auto_run)

    with right:
        st.markdown('### 📊 追踪结果')

        # 决定是否需要运行
        need_run = run_clicked
        if auto_run:
            current_params = get_params_dict()
            last_hash = st.session_state.get('_last_params_hash', '')
            new_hash = str(sorted(current_params.items()))
            if new_hash != last_hash:
                need_run = True
                st.session_state['_last_params_hash'] = new_hash

        if need_run or 'pipeline_result' not in st.session_state or \
           st.session_state.get('_force_rerun'):
            with st.spinner('追踪中...'):
                cfg = get_config_from_session()
                result = run_pipeline_with_steps(data, cfg)
                st.session_state['pipeline_result'] = result
                st.session_state['_force_rerun'] = False

        result = st.session_state.get('pipeline_result')

        if result:
            filtered = result.get('filtered', [])
            areas = result.get('areas', [])

            # 统计指标
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric('多边形数', len(filtered))
            with c2:
                st.metric('最小面积', f'{min(areas):.0f} px²' if areas else 'N/A')
            with c3:
                st.metric('最大面积', f'{max(areas):.0f} px²' if areas else 'N/A')
            with c4:
                st.metric('耗时', f"{result.get('elapsed', 0):.3f}s")

            # 结果图
            fig = fig_result_overlay(
                data, filtered,
                binary=result.get('binary'),
                areas=areas,
                title=f'追踪结果 — {len(filtered)} 个多边形',
            )
            st.plotly_chart(fig, use_container_width=True, key='param_tune_result')

            # 面积直方图
            if areas:
                fig_hist = fig_area_histogram(areas)
                st.plotly_chart(fig_hist, use_container_width=True, key='param_tune_hist')

            # 导出
            _export_section(filtered)

        else:
            st.info('点击 "手动运行" 或打开 "自动运行" 来开始追踪')


def _export_section(polygons):
    """导出按钮"""
    import json
    st.divider()
    st.markdown('### 📥 导出结果')

    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[float(pt[1]), float(pt[0])] for pt in poly]]
                },
                "properties": {
                    "id": i,
                    "area_pixels": float(
                        sum(0.5 * abs(
                            poly[j, 1] * poly[(j + 1) % len(poly), 0] -
                            poly[j, 0] * poly[(j + 1) % len(poly), 1]
                        ) for j in range(len(poly)))
                    )
                }
            }
            for i, poly in enumerate(polygons) if len(poly) >= 3
        ]
    }

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            '📥 下载 GeoJSON',
            json.dumps(geojson_data, indent=2, ensure_ascii=False),
            'fault_polygons.geojson',
            'application/geo+json',
            use_container_width=True,
        )
    with col2:
        txt_buf = _make_txt(polygons)
        st.download_button(
            '📥 下载 TXT (GeoEast格式)',
            txt_buf,
            'fault_polygons.txt',
            'text/plain',
            use_container_width=True,
        )


def _make_txt(polygons) -> str:
    lines = []
    for i, poly in enumerate(polygons):
        if len(poly) < 3:
            continue
        area = float(sum(0.5 * abs(
            poly[j, 1] * poly[(j + 1) % len(poly), 0] -
            poly[j, 0] * poly[(j + 1) % len(poly), 1]
        ) for j in range(len(poly))))
        lines.append(f'> polygon_{i}  area={area:.2f}')
        for pt in poly:
            lines.append(f'{pt[0]:.2f} {pt[1]:.2f}')
        lines.append(f'{poly[0, 0]:.2f} {poly[0, 1]:.2f}')
    return '\n'.join(lines)


if __name__ == '__main__':
    main()
