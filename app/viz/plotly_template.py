"""深色科技风 Plotly 模板"""

import plotly.graph_objects as go
import plotly.io as pio

CYAN = '#00E5FF'
PURPLE = '#7B2FBE'
ORANGE = '#FF6B35'
GREEN = '#39FF14'
PINK = '#FF007F'
GOLD = '#FFD700'
BG = '#0A0E1A'
CARD_BG = '#141928'
TEXT = '#E0E6F0'
TEXT_MUTED = '#8890A8'
GRID = 'rgba(0, 229, 255, 0.08)'

COLORS = [CYAN, PURPLE, ORANGE, GREEN, PINK, GOLD, '#00BFFF', '#FF4500',
          '#BF7FFF', '#00FF88', '#FF88AA', '#88DDFF']


def make_template() -> go.layout.Template:
    t = go.layout.Template()
    t.layout.update(
        plot_bgcolor=BG,
        paper_bgcolor=BG,
        font=dict(color=TEXT, family='sans-serif'),
        xaxis=dict(
            gridcolor=GRID,
            zerolinecolor='rgba(0, 229, 255, 0.15)',
            showgrid=True,
            constrain='domain',
        ),
        yaxis=dict(
            gridcolor=GRID,
            zerolinecolor='rgba(0, 229, 255, 0.15)',
            showgrid=True,
            scaleanchor='x',
            scaleratio=1,
            constrain='domain',
        ),
        colorway=COLORS,
        hoverlabel=dict(
            bgcolor=CARD_BG,
            font_size=13,
            font_family='monospace',
            bordercolor=CYAN,
        ),
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return t


DARK_TEMPLATE = make_template()
pio.templates['fault_dark'] = DARK_TEMPLATE


def dark_layout(title: str = '', width: int = None, height: int = None,
                xaxis_title: str = 'Col', yaxis_title: str = 'Row',
                show_scalebar: bool = False) -> dict:
    """返回统一的深色布局配置。"""
    layout = dict(
        template='fault_dark',
        title=dict(text=title, font=dict(size=16, color=TEXT), x=0.5),
        xaxis=dict(title=xaxis_title, constrain='domain'),
        yaxis=dict(title=yaxis_title, scaleanchor='x', scaleratio=1, constrain='domain'),
        dragmode='pan',
    )
    if width:
        layout['width'] = width
    if height:
        layout['height'] = height
    return layout
