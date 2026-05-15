"""Page 3: 交互探索 — 全屏交互地图 + 多边形详情"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import numpy as np

from app.components.interactive_map import (
    render_layer_controls, render_polygon_detail, render_polygon_list,
)
from app.viz.plotly_figs import fig_interactive_map


def main():
    st.title('交互式数据探索')

    data = st.session_state.get('raw_data')
    result = st.session_state.get('pipeline_result')

    if data is None or result is None:
        st.info('👈 请先在**首页**加载数据并运行流水线')
        return

    polygons = result.get('filtered', [])
    areas = result.get('areas', [])
    binary = result.get('binary')

    if not polygons:
        st.warning('未检测到断层多边形，请调整参数')
        return

    # 初始化选中状态
    if 'selected_polygon_idx' not in st.session_state:
        st.session_state['selected_polygon_idx'] = None

    # 图层控制
    layer_state = render_layer_controls()

    # 主布局：地图 + 侧边面板
    map_col, panel_col = st.columns([3, 1])

    with map_col:
        selected_idx = st.session_state.get('selected_polygon_idx')

        fig = fig_interactive_map(
            data, polygons,
            binary=binary,
            areas=areas,
            show_layers={
                'heatmap': layer_state['heatmap'],
                'mask_contours': layer_state['mask_contours'],
                'raw_contours': layer_state['raw_contours'],
                'polygons': layer_state['polygons'],
                'polygon_fill': layer_state['polygon_fill'],
            },
            selected_idx=selected_idx,
            height=650,
        )
        # 调整热力图透明度
        if layer_state['heatmap'] and fig.data:
            for trace in fig.data:
                if isinstance(trace, type(fig.data[0])) and hasattr(trace, 'opacity'):
                    if trace.type == 'heatmap':
                        trace.opacity = layer_state.get('heatmap_alpha', 0.55)

        clicked = st.plotly_chart(
            fig, use_container_width=True,
            key='explore_map',
            on_select='rerun',
            selection_mode='points',
        )

        # 处理点击
        if clicked and clicked.selection and clicked.selection.points:
            pt = clicked.selection.points[0]
            if hasattr(pt, 'customdata') and pt.customdata and len(pt.customdata) >= 3:
                st.session_state['selected_polygon_idx'] = int(pt.customdata[2])

    with panel_col:
        st.markdown('### 🎯 多边形详情')
        selected_idx = st.session_state.get('selected_polygon_idx')
        if selected_idx is not None and selected_idx < len(polygons):
            render_polygon_detail(polygons[selected_idx], selected_idx)
        else:
            st.info('点击地图中的多边形查看详情')

        st.divider()
        st.markdown('### 📋 多边形列表')
        render_polygon_list(polygons, areas, selected_idx)


if __name__ == '__main__':
    main()
