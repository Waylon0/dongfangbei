"""Page 4: 结果对比 — 双参数集并排对比（参数隔离）"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import numpy as np
import pandas as pd

from config import Config
from app.pipeline.runner import run_pipeline_with_steps
from app.viz.plotly_figs import fig_comparison


def _render_isolated_params(prefix: str, cfg: Config):
    """渲染一组独立参数控件，使用 prefix 隔离 session_state key。

    返回更新后的 Config 对象。
    """
    from app.components.param_controls import PARAM_DEFS

    with st.expander('预处理', expanded=False):
        for key, label, vmin, vmax, step, default, group in PARAM_DEFS:
            if group != '预处理':
                continue
            current = st.session_state.get(f'{prefix}_{key}', default)
            if isinstance(default, bool):
                val = st.toggle(label, value=current, key=f'{prefix}_{key}')
            elif isinstance(default, float):
                val = st.slider(label, vmin, vmax, current, step, key=f'{prefix}_{key}')
            elif isinstance(default, int):
                val = st.number_input(label, vmin, vmax, current, step, key=f'{prefix}_{key}')
            setattr(cfg, key, val)

    with st.expander('分割', expanded=False):
        for key, label, vmin, vmax, step, default, group in PARAM_DEFS:
            if group != '分割':
                continue
            current = st.session_state.get(f'{prefix}_{key}', default)
            if isinstance(default, bool):
                val = st.toggle(label, value=current, key=f'{prefix}_{key}')
            elif isinstance(default, float):
                val = st.slider(label, vmin, vmax, current, step, key=f'{prefix}_{key}')
            elif isinstance(default, int):
                val = st.number_input(label, vmin, vmax, current, step, key=f'{prefix}_{key}')
            setattr(cfg, key, val)

    with st.expander('提取', expanded=False):
        for key, label, vmin, vmax, step, default, group in PARAM_DEFS:
            if group != '提取':
                continue
            current = st.session_state.get(f'{prefix}_{key}', default)
            if isinstance(default, bool):
                val = st.toggle(label, value=current, key=f'{prefix}_{key}')
            elif isinstance(default, float):
                val = st.slider(label, vmin, vmax, current, step, key=f'{prefix}_{key}')
            elif isinstance(default, int):
                val = st.number_input(label, vmin, vmax, current, step, key=f'{prefix}_{key}')
            setattr(cfg, key, val)

    with st.expander('追踪', expanded=False):
        for key, label, vmin, vmax, step, default, group in PARAM_DEFS:
            if group != '追踪':
                continue
            current = st.session_state.get(f'{prefix}_{key}', default)
            if isinstance(default, bool):
                val = st.toggle(label, value=current, key=f'{prefix}_{key}')
            elif isinstance(default, float):
                val = st.slider(label, vmin, vmax, current, step, key=f'{prefix}_{key}')
            elif isinstance(default, int):
                val = st.number_input(label, vmin, vmax, current, step, key=f'{prefix}_{key}')
            setattr(cfg, key, val)

    with st.expander('简化/过滤', expanded=False):
        for key, label, vmin, vmax, step, default, group in PARAM_DEFS:
            if group not in ('简化', '过滤'):
                continue
            current = st.session_state.get(f'{prefix}_{key}', default)
            if isinstance(default, bool):
                val = st.toggle(label, value=current, key=f'{prefix}_{key}')
            elif isinstance(default, float):
                val = st.slider(label, vmin, vmax, current, step, key=f'{prefix}_{key}')
            elif isinstance(default, int):
                val = st.number_input(label, vmin, vmax, current, step, key=f'{prefix}_{key}')
            setattr(cfg, key, val)

    return cfg


def main():
    st.title('结果对比')

    data = st.session_state.get('raw_data')
    if data is None:
        st.info('👈 请先在**首页**加载数据')
        return

    st.markdown('### 📊 参数集配置')

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('#### 🔵 参数集 A')
        cfg_a = Config()
        cfg_a = _render_isolated_params('cmp_a', cfg_a)

        if st.button('▶️ 运行 A', type='primary', use_container_width=True):
            with st.spinner('追踪 A...'):
                st.session_state['param_a_results'] = run_pipeline_with_steps(data, cfg_a)

    with col_b:
        st.markdown('#### 🟣 参数集 B')
        cfg_b = Config()
        cfg_b = _render_isolated_params('cmp_b', cfg_b)

        if st.button('▶️ 运行 B', type='primary', use_container_width=True):
            with st.spinner('追踪 B...'):
                st.session_state['param_b_results'] = run_pipeline_with_steps(data, cfg_b)

    # 对比展示
    result_a = st.session_state.get('param_a_results')
    result_b = st.session_state.get('param_b_results')

    if result_a is not None and result_b is not None:
        st.divider()
        st.markdown('### 📈 对比结果')

        poly_a = result_a.get('filtered', [])
        poly_b = result_b.get('filtered', [])
        areas_a = result_a.get('areas', [])
        areas_b = result_b.get('areas', [])

        fig = fig_comparison(
            data, poly_a, poly_b,
            label_a='Param Set A', label_b='Param Set B',
        )
        st.plotly_chart(fig, use_container_width=True, key='compare_fig')

        st.markdown('### 📊 差异统计')
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric('A 多边形数', len(poly_a))
        with c2:
            st.metric('B 多边形数', len(poly_b),
                     delta=len(poly_b) - len(poly_a))
        with c3:
            st.metric('A 平均面积', f'{np.mean(areas_a):.1f} px²' if areas_a else 'N/A')
        with c4:
            st.metric('B 平均面积', f'{np.mean(areas_b):.1f} px²' if areas_b else 'N/A')
        with c5:
            delta_time = result_b.get('elapsed', 0) - result_a.get('elapsed', 0)
            st.metric('A 耗时', f"{result_a.get('elapsed', 0):.3f}s",
                     delta=f'{delta_time:+.3f}s')

        df = pd.DataFrame({
            '指标': ['数量', '最小面积', '最大面积', '平均面积', '中位数面积'],
            '参数集 A': [
                len(poly_a),
                f'{min(areas_a):.1f}' if areas_a else 'N/A',
                f'{max(areas_a):.1f}' if areas_a else 'N/A',
                f'{np.mean(areas_a):.1f}' if areas_a else 'N/A',
                f'{np.median(areas_a):.1f}' if areas_a else 'N/A',
            ],
            '参数集 B': [
                len(poly_b),
                f'{min(areas_b):.1f}' if areas_b else 'N/A',
                f'{max(areas_b):.1f}' if areas_b else 'N/A',
                f'{np.mean(areas_b):.1f}' if areas_b else 'N/A',
                f'{np.median(areas_b):.1f}' if areas_b else 'N/A',
            ],
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

    elif result_a is not None:
        st.info('参数集 A 已就绪，请运行参数集 B')
    elif result_b is not None:
        st.info('参数集 B 已就绪，请运行参数集 A')


if __name__ == '__main__':
    main()
