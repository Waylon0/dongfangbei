"""Fault Polygon Auto-Tracking — Streamlit 主入口

多页应用框架 + 侧边栏 + 数据加载 + 流水线执行。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import numpy as np
import time

# === 页面配置（必须是第一个 st 命令）===
st.set_page_config(
    page_title='断层多边形自动追踪',
    page_icon='🔬',
    layout='wide',
    initial_sidebar_state='expanded',
)

# === 加载自定义 CSS ===
css_path = Path(__file__).parent / 'assets' / 'custom.css'
if css_path.exists():
    st.markdown(f'<style>{css_path.read_text(encoding="utf-8")}</style>',
                unsafe_allow_html=True)

# === 导入项目模块 ===
from config import Config
from src.vectorize import polygon_area as calc_area
from app.components.sidebar import render_sidebar
from app.components.param_controls import get_config_from_session, get_params_dict
from app.utils.cache_utils import params_to_hash, data_to_hash
from app.pipeline.runner import run_pipeline_with_steps


def main():
    _init_session()

    # 侧边栏
    action = render_sidebar()

    # 处理数据加载
    _handle_data_action(action)

    # 处理运行触发
    _handle_run_trigger()

    # === 主区域：首页 ===
    _render_home_page()


def _init_session():
    """初始化所有 session_state 变量"""
    defaults = {
        'raw_data': None,
        'pipeline_result': None,
        '_trigger_run': False,
        'selected_polygon_idx': None,
        'current_step': 1,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _handle_data_action(action: dict):
    """处理侧边栏的数据操作"""
    if action.get('action') == 'generate':
        st.session_state['raw_data'] = action['data']
        st.session_state['pipeline_result'] = None
    elif action.get('action') == 'upload':
        st.session_state['raw_data'] = action['data']
        st.session_state['pipeline_result'] = None


def _handle_run_trigger():
    """处理流水线运行触发"""
    if st.session_state.get('_trigger_run'):
        data = st.session_state.get('raw_data')
        if data is None:
            st.warning('请先加载数据')
            st.session_state['_trigger_run'] = False
            return

        cfg = get_config_from_session()
        with st.spinner('正在运行断层追踪流水线...'):
            result = run_pipeline_with_steps(data, cfg)
            st.session_state['pipeline_result'] = result
            st.session_state['_trigger_run'] = False
        st.toast('✅ 追踪完成！', icon='🎉')


def _render_home_page():
    """首页内容"""
    st.markdown("""
    <h1 style="text-align:center; margin-bottom:0;">
        断层多边形自动追踪
    </h1>
    <p style="text-align:center; color:#8890A8; margin-top:5px;">
        Automatic Fault Polygon Tracking — 东方杯赛题7
    </p>
    """, unsafe_allow_html=True)

    data = st.session_state.get('raw_data')
    result = st.session_state.get('pipeline_result')

    if data is None and result is None:
        _render_welcome()
    elif data is not None and result is None:
        _render_data_ready(data)
    elif result is not None:
        _render_results_summary(data, result)


def _render_welcome():
    # Hero 横幅
    st.markdown("""
    <div style="
        position:relative;
        background:linear-gradient(135deg, rgba(0,229,255,0.04) 0%, rgba(123,47,190,0.06) 50%, rgba(0,229,255,0.02) 100%);
        border:1px solid rgba(0,229,255,0.15);
        border-radius:12px;
        padding:40px 30px;
        margin:20px 0;
        text-align:center;
        overflow:hidden;
    ">
        <div style="
            position:absolute; top:0; left:0; right:0; height:2px;
            background:linear-gradient(90deg, transparent, #00E5FF, #7B2FBE, #00E5FF, transparent);
            animation:scan-line 3s linear infinite;
        "></div>
        <div style="position:relative; z-index:1;">
            <h2 style="color:#00E5FF; font-size:1.5rem; margin-bottom:12px; letter-spacing:2px; font-weight:600;">
                ⚡ 开始断层追踪
            </h2>
            <p style="color:#B0B8CC; font-size:0.95rem; max-width:650px; margin:0 auto 8px auto; line-height:1.6;">
                基于平面断层属性数据的 <span style="color:#00E5FF; font-weight:600;">自动多边形追踪系统</span>
            </p>
            <p style="color:#66708A; font-size:0.8rem; max-width:550px; margin:0 auto;">
                ① 左侧面板生成或上传数据 &nbsp;→&nbsp;
                ② 调整算法参数 &nbsp;→&nbsp;
                ③ 点击运行按钮 &nbsp;→&nbsp;
                ④ 切换页面探索结果
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 功能卡片
    col1, col2, col3, col4 = st.columns(4)
    cards = [
        ('📊', '分步演示', '7步流水线', '逐步骤查看处理过程，支持自动播放与AI语音讲解，适合答辩展示。'),
        ('⚙️', '实时调参', '拖拽即刷新', '13个算法参数实时调节，自动运行模式让调参效率提升10倍。'),
        ('🗺️', '交互探索', '点击多边形', 'Plotly全屏地图支持缩放/平移/悬停，点击查看每个多边形详情。'),
        ('📈', '结果对比', '双参数集', '左右并排对比不同参数效果，一键导出GeoJSON和GeoEast格式。'),
    ]
    for col, (icon, title, subtitle, desc) in zip([col1, col2, col3, col4], cards):
        with col:
            st.markdown(f"""
            <div style="
                background:linear-gradient(180deg, rgba(20,25,40,0.8), rgba(10,14,26,0.9));
                border:1px solid rgba(0,229,255,0.1);
                border-radius:8px;
                padding:22px 16px;
                text-align:center;
                height:200px;
                transition:all 0.3s;
            " onmouseover="this.style.borderColor='#00E5FF';this.style.boxShadow='0 0 20px rgba(0,229,255,0.1)'"
               onmouseout="this.style.borderColor='rgba(0,229,255,0.1)';this.style.boxShadow='none'">
                <div style="font-size:2rem; margin-bottom:8px;">{icon}</div>
                <div style="color:#00E5FF; font-weight:600; font-size:0.95rem; margin-bottom:4px;">{title}</div>
                <div style="color:#7B2FBE; font-size:0.75rem; margin-bottom:8px; letter-spacing:1px;">{subtitle}</div>
                <div style="color:#8890A8; font-size:0.72rem; line-height:1.5;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)


def _render_data_ready(data: np.ndarray):
    st.markdown(f"""
    <div style="
        position:relative;
        background:linear-gradient(135deg, rgba(0,229,255,0.04), rgba(123,47,190,0.05));
        border:1px solid rgba(0,229,255,0.2);
        border-radius:8px;
        padding:24px;
        margin:20px 0;
        text-align:center;
        overflow:hidden;
    ">
        <div style="
            position:absolute; top:0; left:0; right:0; height:1px;
            background:linear-gradient(90deg, transparent, #00E5FF, transparent);
        "></div>
        <h3 style="color:#00E5FF; margin-bottom:8px; font-size:1.1rem;">📊 数据已就绪</h3>
        <div style="display:flex; justify-content:center; gap:40px; margin:12px 0;">
            <div>
                <span style="color:#66708A; font-size:0.75rem;">数据尺寸</span><br>
                <span style="color:#E0E6F0; font-weight:600; font-size:1.1rem;">{data.shape[0]} x {data.shape[1]}</span>
            </div>
            <div>
                <span style="color:#66708A; font-size:0.75rem;">值范围</span><br>
                <span style="color:#E0E6F0; font-weight:600; font-size:1.1rem;">[{data.min():.3f}, {data.max():.3f}]</span>
            </div>
        </div>
        <p style="color:#8890A8; font-size:0.8rem; margin:0;">
            点击左侧 <b style="color:#7B2FBE;">▶️ 运行断层追踪</b> 开始处理
        </p>
    </div>
    """, unsafe_allow_html=True)

    from app.viz.plotly_figs import fig_step1_raw_data
    fig = fig_step1_raw_data(data)
    st.plotly_chart(fig, use_container_width=True, key='home_preview')


def _render_results_summary(data: np.ndarray, result: dict):
    filtered = result.get('filtered', [])
    areas = result.get('areas', [])
    elapsed = result.get('elapsed', 0)

    # 结果标题横幅
    st.markdown(f"""
    <div style="
        position:relative;
        background:linear-gradient(135deg, rgba(0,229,255,0.05), rgba(123,47,190,0.07));
        border:1px solid rgba(123,47,190,0.2);
        border-radius:8px;
        padding:18px 24px;
        margin:16px 0;
        text-align:center;
        overflow:hidden;
    ">
        <div style="
            position:absolute; bottom:0; left:0; right:0; height:1px;
            background:linear-gradient(90deg, transparent, #7B2FBE, transparent);
        "></div>
        <span style="color:#00E5FF; font-weight:700; font-size:1.1rem;">✅ 追踪完成</span>
        <span style="color:#66708A; font-size:0.8rem; margin-left:16px;">
            耗时 {elapsed:.3f}s &nbsp;|&nbsp; {len(result.get('contours', []))} 个原始轮廓 &nbsp;|&nbsp; {len(result.get('junctions', []))} 个交叉点
        </span>
    </div>
    """, unsafe_allow_html=True)

    # 统计卡片行
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric('多边形数量', len(filtered))
    with col2:
        st.metric('最小面积', f'{min(areas):.1f} px²' if areas else 'N/A')
    with col3:
        st.metric('最大面积', f'{max(areas):.1f} px²' if areas else 'N/A')
    with col4:
        st.metric('平均面积', f'{np.mean(areas):.1f} px²' if areas else 'N/A')
    with col5:
        st.metric('运行时间', f'{elapsed:.3f}s')

    st.divider()

    from app.viz.plotly_figs import fig_result_overlay
    fig = fig_result_overlay(
        data, filtered,
        binary=result.get('binary'),
        areas=areas,
        title='追踪结果预览',
    )
    st.plotly_chart(fig, use_container_width=True, key='home_result')

    st.caption('💡 切换到上方页面标签查看更多：分步演示 / 参数调节 / 交互探索 / 结果对比')

    st.caption('💡 切换到上方页面标签查看更多功能：分步演示 / 参数调节 / 交互探索 / 结果对比')


if __name__ == '__main__':
    main()
