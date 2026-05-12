"""Plotly 图表生成 — 所有步骤图、叠加图、交互地图"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List
from .plotly_template import (
    CYAN, PURPLE, ORANGE, GREEN, PINK, GOLD,
    BG, TEXT, TEXT_MUTED, COLORS, dark_layout,
)


def _polygon_trace(poly: np.ndarray, color: str, name: str = '',
                   width: float = 2.0, fill: float = 0.12,
                   showlegend: bool = True,
                   customdata: list = None) -> go.Scatter:
    """为单个多边形创建 go.Scatter trace。"""
    hover = (
        '<b>%{text}</b><br>'
        'Area: %{customdata[0]:.1f} px²<br>'
        'Vertices: %{customdata[1]}<extra></extra>'
    ) if customdata else None

    text = name if customdata else None
    return go.Scatter(
        x=poly[:, 1], y=poly[:, 0],
        mode='lines',
        line=dict(color=color, width=width),
        fill='toself' if fill > 0 else 'none',
        fillcolor=f'rgba({_hex_to_rgba(color, fill)})',
        name=name,
        text=text,
        customdata=customdata,
        hovertemplate=hover,
        showlegend=showlegend,
        hoverlabel=dict(bgcolor='#141928', bordercolor=color, font_size=12),
    )


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """#00E5FF -> rgba(0, 229, 255, alpha)"""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'{r},{g},{b},{alpha}'


# ============================================================
#  步骤1-7 图表
# ============================================================

def fig_step1_raw_data(data: np.ndarray) -> go.Figure:
    """步骤1：原始断层属性数据 heatmap"""
    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=data, colorscale='RdBu_r', zmin=0, zmax=1,
        colorbar=dict(title='Fault Likelihood', title_font_color=TEXT,
                      tickfont_color=TEXT),
        hovertemplate='Row: %{y}<br>Col: %{x}<br>Value: %{z:.4f}<extra></extra>',
    ))
    y_size, x_size = data.shape
    fig.update_layout(**dark_layout(
        title=f'Step 1: Input — Fault Attribute Data ({y_size} x {x_size})',
    ))
    return fig


def fig_step2_preprocessed(data_smoothed: np.ndarray,
                           binary: np.ndarray) -> go.Figure:
    """步骤2：高斯平滑 + Otsu 二值化"""
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.08,
                        subplot_titles=['Gaussian Smoothed', 'Otsu Binary'])
    fig.add_trace(go.Heatmap(
        z=data_smoothed, colorscale='RdBu_r', zmin=0, zmax=1,
        colorbar=dict(title='', tickfont_color=TEXT, len=0.45, y=0.5),
        showscale=False,
    ), row=1, col=1)
    fig.add_trace(go.Heatmap(
        z=binary, colorscale=[[0, BG], [1, CYAN]], zmin=0, zmax=1,
        showscale=False,
    ), row=1, col=2)
    fig.update_layout(**dark_layout(
        title='Step 2: Preprocessing — Smoothing + Binarization',
    ))
    for ax in ['xaxis', 'xaxis2']:
        fig.update_layout(**{f'{ax}_title': 'Col'})
    fig.update_layout(yaxis_title='Row', yaxis2_title='Row')
    return fig


def fig_step3_morphology(binary_before: np.ndarray,
                         binary_after: np.ndarray) -> go.Figure:
    """步骤3：形态学处理前后对比 + 差异图"""
    diff = binary_after.astype(int) - binary_before.astype(int)

    fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.06,
                        subplot_titles=['Before Morphology',
                                        'After Closing+Opening',
                                        'Changes'])
    fig.add_trace(go.Heatmap(
        z=binary_before, colorscale=[[0, BG], [1, '#556677']],
        zmin=0, zmax=1, showscale=False,
    ), row=1, col=1)
    fig.add_trace(go.Heatmap(
        z=binary_after, colorscale=[[0, BG], [1, CYAN]], zmin=0, zmax=1,
        showscale=False,
    ), row=1, col=2)
    fig.add_trace(go.Heatmap(
        z=diff, colorscale=[[0, ORANGE], [0.5, BG], [1, GREEN]],
        zmin=-1, zmax=1, showscale=False,
    ), row=1, col=3)
    fig.update_layout(**dark_layout(
        title='Step 3: Morphological Processing — Closing + Opening',
    ))
    for ax in ['xaxis', 'xaxis2', 'xaxis3']:
        fig.update_layout(**{f'{ax}_title': 'Col'})
    fig.update_layout(yaxis_title='Row', yaxis2_title='Row', yaxis3_title='Row')
    return fig


def fig_step4_contours(binary: np.ndarray,
                       contours: List) -> go.Figure:
    """步骤4：连通域轮廓提取"""
    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=binary, colorscale=[[0, BG], [1, 'rgba(85,102,119,0.3)']],
        zmin=0, zmax=1, showscale=False,
    ))
    for i, c in enumerate(contours):
        pts = np.array(c)
        color = COLORS[i % len(COLORS)]
        fig.add_trace(go.Scatter(
            x=pts[:, 1], y=pts[:, 0],
            mode='lines+markers',
            line=dict(color=color, width=2.5),
            marker=dict(size=4, color=color, symbol='circle'),
            name=f'Contour {i + 1}',
        ))
    fig.update_layout(**dark_layout(
        title=f'Step 4: Contour Extraction — {len(contours)} Closed Polygons',
    ))
    return fig


def fig_step5_intersections(binary: np.ndarray, skeleton: np.ndarray,
                            junctions: list) -> go.Figure:
    """步骤5：骨架化 + 交叉点检测"""
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.08,
                        subplot_titles=['Connected Region', 'Skeleton + Junctions'])

    fig.add_trace(go.Heatmap(
        z=binary, colorscale=[[0, BG], [1, CYAN]], zmin=0, zmax=1,
        showscale=False,
    ), row=1, col=1)

    # 骨架叠加
    skel_overlay = np.where(skeleton > 0, 1, np.nan)
    fig.add_trace(go.Heatmap(
        z=skel_overlay, colorscale=[[0, CYAN], [1, GREEN]],
        zmin=0, zmax=1, showscale=False, opacity=0.9,
    ), row=1, col=2)

    if junctions:
        jr = [j[0] for j in junctions]
        jc = [j[1] for j in junctions]
        fig.add_trace(go.Scatter(
            x=jc, y=jr, mode='markers',
            marker=dict(size=10, color=ORANGE, symbol='x', line_width=2),
            name=f'Junctions ({len(junctions)})',
        ), row=1, col=2)

    fig.update_layout(**dark_layout(
        title=f'Step 5: Skeletonization + Junction Detection',
    ))
    for ax in ['xaxis', 'xaxis2']:
        fig.update_layout(**{f'{ax}_title': 'Col'})
    fig.update_layout(yaxis_title='Row', yaxis2_title='Row')
    return fig


def fig_step6_final(data: np.ndarray,
                    filtered: List[np.ndarray],
                    areas: List[float] = None) -> go.Figure:
    """步骤6：最终结果 — 简化多边形叠加"""
    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=data, colorscale='RdBu_r', zmin=0, zmax=1, opacity=0.55,
        colorbar=dict(title='Fault Likelihood', title_font_color=TEXT,
                      tickfont_color=TEXT, len=0.8),
        hovertemplate='Value: %{z:.3f}<extra></extra>',
    ))
    for i, poly in enumerate(filtered):
        color = COLORS[i % len(COLORS)]
        area_val = areas[i] if areas is not None else 0
        n_verts = len(poly)
        fig.add_trace(_polygon_trace(
            poly, color, name=f'Fault {i + 1}',
            width=2.5, fill=0.15,
            customdata=[area_val, n_verts],
        ))
    fig.update_layout(**dark_layout(
        title=f'Step 6: Final Result — {len(filtered)} Fault Polygons',
    ))
    fig.update_layout(showlegend=len(filtered) <= 12)
    return fig


def fig_step7_overview(data: np.ndarray, binary: np.ndarray,
                       filtered: List[np.ndarray],
                       areas: List[float]) -> go.Figure:
    """步骤7：流水线总览 (2x3 grid)"""
    from skimage.measure import find_contours

    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=[
            '① Input Attribute', '② Binary Mask', '③ Raw Contours',
            '④ Simplified Polygons', '⑤ Area Distribution', '⑥ Final Overlay',
        ],
        horizontal_spacing=0.06, vertical_spacing=0.1,
        specs=[
            [{'type': 'heatmap'}, {'type': 'heatmap'}, {'type': 'xy'}],
            [{'type': 'xy'}, {'type': 'xy'}, {'type': 'xy'}],
        ],
    )

    # ①
    fig.add_trace(go.Heatmap(z=data, colorscale='RdBu_r', zmin=0, zmax=1,
                             showscale=False), row=1, col=1)
    # ②
    fig.add_trace(go.Heatmap(z=binary, colorscale=[[0, BG], [1, CYAN]],
                             zmin=0, zmax=1, showscale=False), row=1, col=2)
    # ③
    raw_contours = find_contours(binary.astype(float), level=0.5)
    for c in raw_contours:
        fig.add_trace(go.Scatter(x=c[:, 1], y=c[:, 0], mode='lines',
                                 line=dict(color=TEXT_MUTED, width=0.6),
                                 showlegend=False), row=1, col=3)

    # ④
    for i, poly in enumerate(filtered):
        color = COLORS[i % len(COLORS)]
        fig.add_trace(go.Scatter(
            x=poly[:, 1], y=poly[:, 0], mode='lines',
            line=dict(color=color, width=1.8), showlegend=False,
        ), row=2, col=1)

    # ⑤
    sorted_areas = sorted(areas, reverse=True)
    bar_colors = [COLORS[i % len(COLORS)] for i in range(len(sorted_areas))]
    fig.add_trace(go.Bar(
        x=list(range(len(sorted_areas))), y=sorted_areas,
        marker_color=bar_colors, showlegend=False,
        hovertemplate='Rank: %{x}<br>Area: %{y:.1f} px²<extra></extra>',
    ), row=2, col=2)
    fig.add_hline(y=50, line_dash='dash', line_color=ORANGE,
                  annotation_text='min=50px', row=2, col=2)

    # ⑥
    fig.add_trace(go.Heatmap(z=data, colorscale='RdBu_r', zmin=0, zmax=1,
                             opacity=0.45, showscale=False), row=2, col=3)
    for i, poly in enumerate(filtered):
        color = COLORS[i % len(COLORS)]
        fig.add_trace(go.Scatter(
            x=poly[:, 1], y=poly[:, 0], mode='lines',
            line=dict(color=color, width=2),
            fill='toself', fillcolor=f'rgba({_hex_to_rgba(color, 0.15)})',
            showlegend=False,
        ), row=2, col=3)

    fig.update_layout(**dark_layout(
        title='Step 7: Pipeline Overview',
        height=750,
    ))
    # 为每个子图设置标题
    for ann in fig.layout.annotations:
        ann.font.color = TEXT
    return fig


# ============================================================
#  通用叠加图（参数调节页用）
# ============================================================

def fig_result_overlay(data: np.ndarray,
                       polygons: List[np.ndarray],
                       binary: np.ndarray = None,
                       areas: List[float] = None,
                       title: str = 'Fault Polygon Extraction',
                       height: int = 550) -> go.Figure:
    """结果叠加图 — 属性底图 + 多边形"""
    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        z=data, colorscale='RdBu_r', zmin=0, zmax=1, opacity=0.55,
        colorbar=dict(title='', tickfont_color=TEXT, len=0.7, thickness=12),
        hovertemplate='Value: %{z:.4f}<extra></extra>',
    ))

    if binary is not None:
        from skimage.measure import find_contours
        edge_contours = find_contours(binary.astype(float), level=0.5)
        for c in edge_contours:
            fig.add_trace(go.Scatter(
                x=c[:, 1], y=c[:, 0], mode='lines',
                line=dict(color='rgba(255,255,255,0.15)', width=0.5),
                showlegend=False, hoverinfo='skip',
            ))

    for i, poly in enumerate(polygons):
        color = COLORS[i % len(COLORS)]
        a = areas[i] if areas is not None else 0
        n = len(poly)
        fig.add_trace(_polygon_trace(
            poly, color, name=f'Fault {i + 1}',
            width=2.3, fill=0.12,
            customdata=[a, n],
        ))

    fig.update_layout(**dark_layout(title=title, height=height))
    fig.update_layout(showlegend=len(polygons) <= 10)
    return fig


# ============================================================
#  交互地图（探索页用）
# ============================================================

def fig_interactive_map(data: np.ndarray,
                        polygons: List[np.ndarray],
                        binary: np.ndarray = None,
                        areas: List[float] = None,
                        show_layers: dict = None,
                        selected_idx: int = None,
                        height: int = 650) -> go.Figure:
    """全功能交互地图 — 支持图层切换和点击选中。

    show_layers: {'heatmap': bool, 'mask_contours': bool,
                  'raw_contours': bool, 'polygons': bool,
                  'polygon_fill': bool}
    """
    if show_layers is None:
        show_layers = {'heatmap': True, 'mask_contours': False,
                       'raw_contours': False, 'polygons': True,
                       'polygon_fill': True}

    fig = go.Figure()

    # 图层1: 属性底图
    if show_layers.get('heatmap', True):
        fig.add_trace(go.Heatmap(
            z=data, colorscale='RdBu_r', zmin=0, zmax=1, opacity=0.55,
            colorbar=dict(title='Fault Likelihood', title_font_color=TEXT,
                          tickfont_color=TEXT, len=0.8, thickness=10),
            hovertemplate='Row: %{y}<br>Col: %{x}<br>Value: %{z:.4f}<extra></extra>',
            name='Attribute Data',
        ))

    # 图层2: 二值掩膜轮廓
    if show_layers.get('mask_contours', False) and binary is not None:
        from skimage.measure import find_contours
        edge_contours = find_contours(binary.astype(float), level=0.5)
        for c in edge_contours:
            fig.add_trace(go.Scatter(
                x=c[:, 1], y=c[:, 0], mode='lines',
                line=dict(color='rgba(255,255,255,0.2)', width=0.5),
                showlegend=False, hoverinfo='skip',
            ))

    # 图层3: 多边形
    if show_layers.get('polygons', True):
        for i, poly in enumerate(polygons):
            color = COLORS[i % len(COLORS)]
            a = areas[i] if areas is not None else 0
            n = len(poly)
            is_selected = (selected_idx is not None and i == selected_idx)
            w = 4.5 if is_selected else 2.2
            f = 0.25 if is_selected else (0.1 if show_layers.get('polygon_fill', True) else 0)
            fig.add_trace(_polygon_trace(
                poly, color, name=f'Fault {i + 1}',
                width=w, fill=f,
                customdata=[a, n, i],
            ))
            # 选中高亮外发光
            if is_selected:
                fig.add_trace(go.Scatter(
                    x=poly[:, 1], y=poly[:, 0],
                    mode='lines',
                    line=dict(color=color, width=8),
                    opacity=0.3, showlegend=False, hoverinfo='skip',
                ))

    fig.update_layout(**dark_layout(
        title='Interactive Fault Polygon Map',
        height=height,
    ))
    fig.update_layout(
        showlegend=len(polygons) <= 12,
        clickmode='event+select',
    )
    return fig


# ============================================================
#  对比图（对比页用）
# ============================================================

def fig_comparison(data: np.ndarray,
                   polygons_a: List[np.ndarray],
                   polygons_b: List[np.ndarray],
                   label_a: str = 'Param Set A',
                   label_b: str = 'Param Set B',
                   height: int = 500) -> go.Figure:
    """并排对比两个参数集的结果"""
    fig = make_subplots(
        rows=1, cols=2, horizontal_spacing=0.05,
        subplot_titles=[
            f'{label_a} ({len(polygons_a)} polygons)',
            f'{label_b} ({len(polygons_b)} polygons)',
        ],
    )

    for col, polygons, color_key in [(1, polygons_a, 0), (2, polygons_b, 4)]:
        fig.add_trace(go.Heatmap(
            z=data, colorscale='RdBu_r', zmin=0, zmax=1,
            opacity=0.45, showscale=False,
        ), row=1, col=col)

        for i, poly in enumerate(polygons):
            color = COLORS[(i + color_key) % len(COLORS)]
            a_val = len(poly)
            fig.add_trace(go.Scatter(
                x=poly[:, 1], y=poly[:, 0],
                mode='lines',
                line=dict(color=color, width=2.2),
                fill='toself',
                fillcolor=f'rgba({_hex_to_rgba(color, 0.12)})',
                name=f'{label_a} Fault {i + 1}' if col == 1 else f'{label_b} Fault {i + 1}',
                showlegend=False,
            ), row=1, col=col)

    fig.update_layout(**dark_layout(
        title='Parameter Comparison',
        height=height,
    ))
    for ann in fig.layout.annotations:
        ann.font.color = TEXT
    return fig


# ============================================================
#  面积直方图
# ============================================================

def fig_area_histogram(areas: List[float]) -> go.Figure:
    """面积分布直方图"""
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=areas, nbinsx=20,
        marker=dict(color=CYAN, line=dict(color=BG, width=1)),
        hovertemplate='Area: %{x:.1f} px²<br>Count: %{y}<extra></extra>',
    ))
    fig.update_layout(**dark_layout(
        title='Polygon Area Distribution',
        xaxis_title='Area (px²)',
        yaxis_title='Count',
        height=350,
    ))
    return fig
