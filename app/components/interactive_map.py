"""交互地图组件 — 图层切换 + 多边形选择"""

import streamlit as st
import numpy as np


def render_layer_controls() -> dict:
    """渲染图层控制面板，返回图层可见性字典。"""
    with st.expander('🎨 图层控制', expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            show_heatmap = st.checkbox('属性底图', True, key='layer_heatmap')
            show_mask = st.checkbox('二值掩膜轮廓', False, key='layer_mask')
            show_raw_contours = st.checkbox('原始轮廓', False, key='layer_raw')
        with col2:
            show_polygons = st.checkbox('最终多边形', True, key='layer_polygons')
            show_fill = st.checkbox('多边形填充', True, key='layer_fill')
            heatmap_opacity = st.slider('底图透明度', 0.1, 1.0, 0.55, 0.05, key='layer_heatmap_alpha')

        return {
            'heatmap': show_heatmap,
            'mask_contours': show_mask,
            'raw_contours': show_raw_contours,
            'polygons': show_polygons,
            'polygon_fill': show_fill,
            'heatmap_alpha': heatmap_opacity,
        }


def render_polygon_detail(polygon: np.ndarray, idx: int):
    """渲染选中多边形的详情卡片"""
    if polygon is None or len(polygon) < 3:
        st.info('点击地图中的多边形查看详情')
        return

    area = _polygon_area(polygon)
    perimeter = _polygon_perimeter(polygon)
    bbox = _polygon_bbox(polygon)

    st.markdown(f'### 🎯 断层 {idx + 1}')

    col1, col2 = st.columns(2)
    with col1:
        st.metric('面积', f'{area:.1f} px²')
        st.metric('顶点数', len(polygon))
    with col2:
        st.metric('周长', f'{perimeter:.1f} px')
        st.metric('包围盒', f'{bbox[2] - bbox[0]:.0f} x {bbox[3] - bbox[1]:.0f}')

    with st.expander('顶点坐标', expanded=False):
        st.dataframe(
            {'Row': [f'{p[0]:.2f}' for p in polygon[:50]],
             'Col': [f'{p[1]:.2f}' for p in polygon[:50]]},
            use_container_width=True,
        )
        if len(polygon) > 50:
            st.caption(f'... 仅显示前 50 / {len(polygon)} 个顶点')


def render_polygon_list(polygons: list, areas: list,
                        selected_idx: int = None) -> int:
    """渲染多边形列表（按面积排序），返回选中索引"""
    if not areas:
        st.caption('暂无多边形')
        return None

    import pandas as pd

    sorted_idx = np.argsort(areas)[::-1]
    data = []
    for rank, i in enumerate(sorted_idx):
        data.append({
            '排名': rank + 1,
            'ID': i + 1,
            '面积 (px²)': f'{areas[i]:.1f}',
            '顶点数': len(polygons[i]),
        })

    df = pd.DataFrame(data)
    st.dataframe(
        df, use_container_width=True, hide_index=True,
        height=320,
        column_config={
            'ID': st.column_config.NumberColumn('ID', width='small'),
        },
    )

    st.caption('💡 在交互探索页面点击多边形查看详情')
    return None


def _polygon_area(poly: np.ndarray) -> float:
    """Shoelace 面积"""
    if len(poly) < 3:
        return 0.0
    x = poly[:, 1]
    y = poly[:, 0]
    return 0.5 * abs(sum(x[i] * y[(i + 1) % len(poly)] -
                         y[i] * x[(i + 1) % len(poly)]
                         for i in range(len(poly))))


def _polygon_perimeter(poly: np.ndarray) -> float:
    """多边形周长"""
    if len(poly) < 2:
        return 0.0
    diffs = np.diff(poly, axis=0)
    return float(np.sum(np.sqrt(np.sum(diffs ** 2, axis=1))))


def _polygon_bbox(poly: np.ndarray) -> tuple:
    """(min_row, min_col, max_row, max_col)"""
    return (
        float(poly[:, 0].min()), float(poly[:, 1].min()),
        float(poly[:, 0].max()), float(poly[:, 1].max()),
    )
