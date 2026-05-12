"""步骤进度条组件 — 用于分步流水线页面"""

import streamlit as st

STEPS = [
    {'id': 1, 'title': '原始数据', 'icon': '📊',
     'desc': '展示输入的断层属性数据。每个像素值代表该位置的断层响应强度（0-1）。'},
    {'id': 2, 'title': '预处理', 'icon': '🔧',
     'desc': '高斯滤波去噪后，使用 Otsu 自适应阈值将数据二值化，区分断层区域与背景。'},
    {'id': 3, 'title': '形态学处理', 'icon': '✂️',
     'desc': '闭运算填充断层区域内部小孔洞；开运算去除孤立噪点，使断层区域更连续。'},
    {'id': 4, 'title': '轮廓提取', 'icon': '🔍',
     'desc': '对每个连通域使用 marching squares 算法提取闭合轮廓，在骨架交叉处分离相交断层。'},
    {'id': 5, 'title': '交叉点检测', 'icon': '🔀',
     'desc': '骨架化后检测度数≥3的交叉点，用于分离相互交切的断层系统。'},
    {'id': 6, 'title': '最终结果', 'icon': '✅',
     'desc': 'Douglas-Peucker 简化 + Chaikin 平滑后的多边形，叠加在原始属性数据上。'},
    {'id': 7, 'title': '流水线总览', 'icon': '🗺️',
     'desc': '一页展示完整处理流程：从原始数据到最终多边形，附带面积分布统计。'},
]


def render_step_progress(current_step: int):
    """渲染水平步骤进度条。

    Args:
        current_step: 当前步骤编号 (1-7)
    """
    total = len(STEPS)
    cols = st.columns(total)

    for i, step in enumerate(STEPS):
        step_num = i + 1
        with cols[i]:
            if step_num < current_step:
                color = '#7B2FBE'
                bg = 'rgba(123,47,190,0.15)'
                border = '1px solid #7B2FBE'
            elif step_num == current_step:
                color = '#00E5FF'
                bg = 'rgba(0,229,255,0.12)'
                border = '1px solid #00E5FF'
            else:
                color = '#3A3F55'
                bg = 'rgba(58,63,85,0.1)'
                border = '1px solid #3A3F55'

            st.markdown(f"""
            <div style="
                text-align:center;
                padding:8px 4px;
                border-radius:6px;
                background:{bg};
                border:{border};
                font-size:0.7rem;
                color:{color};
                transition:all 0.3s;
            ">
                <div style="font-size:1.2rem;">{step['icon']}</div>
                <div style="margin-top:2px; font-weight:500;">{step_num}. {step['title']}</div>
            </div>
            """, unsafe_allow_html=True)


def render_step_description(step_num: int):
    """渲染当前步骤的文字说明"""
    step = STEPS[step_num - 1]
    st.markdown(f"""
    <div style="
        background:linear-gradient(135deg, rgba(0,229,255,0.08), rgba(123,47,190,0.08));
        border-left:3px solid #00E5FF;
        padding:16px 20px;
        border-radius:6px;
        margin:10px 0;
    ">
        <h4 style="color:#00E5FF; margin:0 0 6px 0;">{step['icon']} 步骤 {step_num}: {step['title']}</h4>
        <p style="color:#E0E6F0; margin:0; font-size:0.9rem;">{step['desc']}</p>
    </div>
    """, unsafe_allow_html=True)


def render_voice_button(step_num: int):
    """使用浏览器 Web Speech API 朗读步骤说明（离线可用）"""
    import json
    step = STEPS[step_num - 1]
    text = f"步骤{step_num}：{step['title']}。{step['desc']}"

    st.components.v1.html(f"""
    <script>
    (function() {{
        const btn = document.getElementById('voice-btn-{step_num}');
        if (btn && !btn._bound) {{
            btn._bound = true;
            btn.addEventListener('click', function() {{
                window.speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance({json.dumps(text, ensure_ascii=False)});
                u.lang = 'zh-CN';
                u.rate = 0.9;
                u.pitch = 1.05;
                window.speechSynthesis.speak(u);
            }});
        }}
    }})();
    </script>
    <button id="voice-btn-{step_num}" style="
        background:rgba(0,229,255,0.1);
        border:1px solid #00E5FF;
        color:#00E5FF;
        border-radius:6px;
        padding:6px 14px;
        cursor:pointer;
        font-size:0.85rem;
        transition:all 0.3s;
    " onmouseover="this.style.background='rgba(0,229,255,0.2)'"
       onmouseout="this.style.background='rgba(0,229,255,0.1)'">
        🔊 AI 语音讲解
    </button>
    """, height=45)


def render_step_controls(current_step: int) -> tuple:
    """渲染步骤控制按钮，返回 (action, new_step)。

    action: 'prev' | 'next' | 'auto' | 'jump' | None
    """
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1.5, 1.5, 3])

    with col1:
        prev_clicked = st.button('◀ 上一步', disabled=current_step <= 1,
                                 use_container_width=True)
    with col2:
        next_clicked = st.button('下一步 ▶', disabled=current_step >= 7,
                                 use_container_width=True)
    with col3:
        auto = st.toggle('自动播放', key='autoplay')

    with col4:
        jump_to = st.selectbox(
            '跳转', list(range(1, 8)), index=current_step - 1,
            label_visibility='collapsed',
        )

    if prev_clicked:
        return ('prev', current_step - 1)
    elif next_clicked:
        return ('next', current_step + 1)
    elif jump_to != current_step:
        return ('jump', jump_to)

    if auto:
        return ('auto', (current_step % 7) + 1)

    return (None, current_step)
