"""Page 1: 分步流水线演示 — 7步可视化展示

适合答辩/演示场合，逐步讲解算法处理流程。
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import time

from app.components.step_viewer import (
    render_step_progress, render_step_description, render_step_controls,
    render_voice_button,
)
from app.viz.plotly_figs import (
    fig_step1_raw_data, fig_step2_preprocessed,
    fig_step3_morphology, fig_step4_contours,
    fig_step5_intersections, fig_step6_final,
    fig_step7_overview,
)


def main():
    st.title('分步流水线演示')

    result = st.session_state.get('pipeline_result')
    data = st.session_state.get('raw_data')

    if result is None or data is None:
        st.info('👈 请先在**首页**加载数据并点击 "运行断层追踪"')
        return

    # 初始化当前步骤
    if 'current_step' not in st.session_state:
        st.session_state['current_step'] = 1

    current = st.session_state['current_step']

    # 步骤进度条
    render_step_progress(current)
    st.divider()

    # 主图区域
    plot_col, desc_col = st.columns([5, 2])

    with plot_col:
        fig = _get_step_figure(current, data, result)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True,
                          key=f'step_fig_{current}')

    with desc_col:
        render_step_description(current)
        render_voice_button(current)

        # 面积统计（步骤6/7）
        if current >= 6 and result.get('areas'):
            areas = result['areas']
            st.markdown('### 📈 统计')
            st.metric('多边形数量', len(areas))
            st.metric('面积范围', f'{min(areas):.1f} - {max(areas):.1f} px²')
            st.metric('总面积', f'{sum(areas):.1f} px²')

    st.divider()

    # 控制栏
    action, new_step = render_step_controls(current)
    if action == 'auto':
        time.sleep(2.5)
        st.session_state['current_step'] = new_step
        st.rerun()
    elif action in ('prev', 'next', 'jump'):
        st.session_state['current_step'] = new_step
        st.rerun()


def _get_step_figure(step: int, data, result):
    """根据步骤号返回对应的 Plotly figure"""
    if step == 1:
        return fig_step1_raw_data(data)
    elif step == 2:
        smoothed = result.get('data_smoothed', data)
        binary_before = result.get('binary_before_morph', result['binary'])
        return fig_step2_preprocessed(smoothed, binary_before)
    elif step == 3:
        binary_before = result.get('binary_before_morph', result['binary'])
        return fig_step3_morphology(binary_before, result['binary'])
    elif step == 4:
        return fig_step4_contours(result['binary'], result.get('contours', []))
    elif step == 5:
        return fig_step5_intersections(
            result['binary'], result.get('skeleton', result['binary']),
            result.get('junctions', []),
        )
    elif step == 6:
        return fig_step6_final(data, result.get('filtered', []),
                              result.get('areas', []))
    elif step == 7:
        return fig_step7_overview(
            data, result['binary'],
            result.get('filtered', []),
            result.get('areas', []),
        )
    return None


if __name__ == '__main__':
    main()
