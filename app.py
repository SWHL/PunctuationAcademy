# -*- coding: utf-8 -*-
"""
标点学堂 / Punctuation Academy
Gradio 入口：内置文章 + 用户上传 TXT、题型筛选、单框作答、答案对比。
"""

import gradio as gr

import html as html_module

from utils import (
    build_display_text,
    build_result_html,
    compare_answers,
    load_builtin_articles,
    parse_uploaded_txt,
    pick_random_question,
)

MAX_BLANKS = 10

# 启动时加载内置题目
BUILTIN_QUESTIONS = load_builtin_articles()


def on_upload(file):
    """用户上传 TXT 后解析，返回提示信息；实际题目列表通过 state 在下一轮传递。"""
    if file is None:
        return "", []
    try:
        with open(file.name, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"解析失败：{e}", []
    questions = parse_uploaded_txt(content)
    if not questions:
        return (
            "未能解析出题目（请检查格式：显式标注用【标点】；纯段落将自动挖空）。",
            [],
        )
    return (
        f"已解析，共 {len(questions)} 段可练习。点击「开始 / 换一题」即可使用。",
        questions,
    )


def on_paste(content, current_uploaded):
    """用户粘贴范文后解析，并入当前题库（与文件上传的题目合并），返回提示与合并后的题目列表。"""
    if not content or not content.strip():
        return "请先粘贴范文内容。", (current_uploaded or [])
    questions = parse_uploaded_txt(content.strip())
    if not questions:
        return (
            "未能解析出题目（请检查格式：显式标注用【标点】；纯段落将自动挖空）。",
            current_uploaded or [],
        )
    merged = (current_uploaded or []) + questions
    return (
        f"本次解析 {len(questions)} 段，已加入题库；当前共 {len(merged)} 段可练习。",
        merged,
    )


def _sentence_to_html(sentence: str) -> str:
    """将整句（含 ___ 空位）转为题目区 HTML 一行显示。"""
    if not sentence:
        return '<p class="question-sentence" style="line-height:1.9; font-size:1.05rem; margin:0; word-break:keep-all;"></p>'
    escaped = html_module.escape(sentence)
    return (
        f'<p class="question-sentence" style="'
        "line-height:1.9; font-size:1.05rem; margin:0; word-break:keep-all;"
        f'">{escaped}</p>'
    )


def format_stats(total: int, answered: int) -> str:
    """格式化统计：总题数、剩余、已答。"""
    remaining = max(0, total - answered)
    return f"**总题数：{total}** &nbsp; **剩余：{remaining}** &nbsp; **已答：{answered}**"


def on_start(uploaded_questions, answered_count=0):
    """开始/换一题：有用户上传则只用用户题库，否则用内置；返回题目句（___）、空位、提示、state、清空结果、统计。"""
    hint_placeholder = '<p style="color:#888; margin-top:0.2em; font-size:0.95em;"></p>'
    empty_result = ""

    # 用户上传/粘贴过题目则只显示用户题库，否则用系统自带
    pool = (uploaded_questions or []) if (uploaded_questions and len(uploaded_questions) > 0) else BUILTIN_QUESTIONS
    total = len(pool)
    stats_str = format_stats(total, answered_count)

    def hide_update():
        return gr.update(value="", visible=False)

    def show_empty():
        return gr.update(value="", visible=True)

    if not pool:
        display_html = _sentence_to_html("暂无题目。请使用内置题目或上传/粘贴范文。")
        box_updates = [hide_update() for _ in range(MAX_BLANKS)]
        return display_html, *box_updates, hint_placeholder, None, uploaded_questions, empty_result, stats_str
    q = pick_random_question(pool, [])
    if q is None:
        display_html = _sentence_to_html("暂无符合长度要求的题目，可尝试上传更多范文。")
        box_updates = [hide_update() for _ in range(MAX_BLANKS)]
        return display_html, *box_updates, hint_placeholder, None, uploaded_questions, empty_result, stats_str

    display_txt = build_display_text(q["text"], q["blanks"])
    display_html = _sentence_to_html(display_txt)
    n = len(q["blanks"])
    box_updates = [show_empty() for _ in range(n)] + [hide_update() for _ in range(MAX_BLANKS - n)]
    hint_html = (
        '<p style="color:#888; margin-top:0.5em; font-size:0.95em;">在下方空位处按顺序填入标点（每格一个）。</p>'
    )
    return display_html, *box_updates, hint_html, q, uploaded_questions, empty_result, stats_str


def on_submit(*answer_box_values_and_state):
    """提交答案：对比结果、更新已答数、返回统计。"""
    n_boxes = MAX_BLANKS
    answer_box_values = list(answer_box_values_and_state[:n_boxes])
    uploaded = answer_box_values_and_state[n_boxes] if len(answer_box_values_and_state) > n_boxes else []
    current = (
        answer_box_values_and_state[n_boxes + 1]
        if len(answer_box_values_and_state) > n_boxes + 1
        else None
    )
    answered_count = (
        int(answer_box_values_and_state[n_boxes + 2])
        if len(answer_box_values_and_state) > n_boxes + 2
        else 0
    )
    no_question_msg = '<p style="color:#888;">请先点击「开始 / 换一题」获取题目。</p>'
    pool_size = len(BUILTIN_QUESTIONS) + len(uploaded or [])
    if current is None:
        return no_question_msg, answered_count, format_stats(pool_size, answered_count)
    n = len(current["blanks"])
    user_list = [(answer_box_values[i] or "").strip() for i in range(n)]
    correct_count, total_blanks, details = compare_answers(user_list, current["blanks"])
    html_block = build_result_html(
        current["text"], current["blanks"], user_list, details
    )
    summary = (
        f'<p style="font-size: 1.1rem; margin-bottom: 0.3em;">'
        f'<strong>结果：</strong> <span style="color: #2e7d32;">{correct_count}/{total_blanks}</span> 正确'
        f'</p>'
    )
    new_answered = answered_count + 1
    return summary + html_block, new_answered, format_stats(pool_size, new_answered)


CUSTOM_CSS = """
/* 顶部标题区 */
.academy-header {
    text-align: center;
    padding: 1.2em 0 0.8em;
    margin-bottom: 0.5em;
    border-bottom: 1px solid var(--border-color-primary, #e0e0e0);
}
.academy-header h1 {
    font-size: 1.75rem;
    font-weight: 600;
    margin: 0;
    letter-spacing: 0.02em;
}
.academy-subtitle {
    color: var(--body-text-color-secondary, #666);
    font-size: 0.95rem;
    margin-top: 0.35em;
}
/* 左侧卡片 */
.source-panel {
    background: var(--block-background-fill, #fafafa);
    border-radius: 12px;
    padding: 1em 1.1em;
    border: 1px solid var(--border-color-primary, #e8e8e8);
}
/* 练习区题目框 */
.question-block {
    background: var(--block-background-fill, #fafafa);
    border-radius: 10px;
    padding: 1em 1.2em;
    border: 1px solid var(--border-color-primary, #e8e8e8);
    margin-bottom: 0.8em;
    line-height: 1.7;
    font-size: 1.05rem;
}
/* 题目整句：一段显示，不拆行 */
.question-sentence-wrap {
    margin-bottom: 0.5em;
}
.question-sentence-wrap .question-sentence {
    line-height: 1.9;
    font-size: 1.05rem;
    margin: 0;
    word-break: keep-all;
}
/* 空位输入框一行 */
.blanks-row {
    gap: 6px 10px;
    align-items: center;
}
.blanks-row .blank-input input,
.blanks-row input[type="text"] {
    width: 2.8em !important;
    min-width: 2.8em !important;
    max-width: 2.8em !important;
    padding: 4px 6px;
    border: 1px solid var(--border-color-primary, #ccc);
    border-radius: 4px;
    text-align: center;
    font-size: 1rem;
}
/* 主按钮 */
.primary-btn { font-weight: 600; }
/* 小提示 */
.small-hint { color: var(--body-text-color-secondary, #888); font-size: 0.9em; margin-top: -0.2em; }
"""


def build_ui():
    with gr.Blocks() as demo:
        gr.HTML(
            '<div class="academy-header">'
            '<h1>标点学堂 · Punctuation Academy</h1>'
            '<p class="academy-subtitle">使用内置规范文章或上传 TXT，在空位处按顺序填入正确标点</p>'
            '</div>'
        )

        uploaded_questions = gr.State([])
        current_question = gr.State(None)
        answered_count = gr.State(0)

        with gr.Row():
            with gr.Column(scale=1):
                with gr.Group(elem_classes=["source-panel"]):
                    gr.Markdown("#### 📂 题目来源")
                    file = gr.File(
                        label="上传 TXT（可选）",
                        file_types=[".txt"],
                        type="filepath",
                    )
                    gr.Markdown("**或粘贴范文**")
                    paste_box = gr.Textbox(
                        label="",
                        placeholder="将范文粘贴到此处，支持整段复制…",
                        lines=4,
                        max_lines=8,
                    )
                    btn_paste = gr.Button("解析并加入题库", variant="secondary")
                    upload_msg = gr.Markdown("", elem_classes=["upload-msg"])
                    gr.HTML(
                        '<p style="margin-top:0.6em; color:#666; font-size:0.9em;">'
                        '可从 <a href="https://www.people.com.cn/" target="_blank" rel="noopener noreferrer">人民日报</a> '
                        '选择范文，复制后粘贴到上方框内即可。</p>'
                    )

            with gr.Column(scale=2):
                gr.Markdown("#### ✏️ 练习区")
                stats_display = gr.Markdown("")
                with gr.Group():
                    gr.Markdown("**题目**（在空位处填入标点）")
                    question_display = gr.HTML(
                        _sentence_to_html("点击「开始 / 换一题」加载题目。"),
                        elem_classes=["question-sentence-wrap"],
                    )
                    answer_hint = gr.HTML("")
                    gr.Markdown("**空位**（按从左到右顺序填写）")
                    with gr.Row(elem_classes=["blanks-row"]):
                        answer_boxes = []
                        for i in range(MAX_BLANKS):
                            box = gr.Textbox(
                                show_label=False,
                                placeholder="",
                                max_lines=1,
                                min_width=48,
                                scale=0,
                                visible=False,
                                elem_classes=["blank-input"],
                            )
                            answer_boxes.append(box)
                with gr.Row():
                    btn_submit = gr.Button("提交答案", variant="primary", elem_classes=["primary-btn"])
                    btn_start = gr.Button("开始 / 换一题", variant="primary", elem_classes=["primary-btn"])
                result = gr.HTML("")

        # 上传 TXT → 解析并存入 state
        def on_upload_wrap(f):
            msg, qs = on_upload(f)
            return msg, qs

        file.change(
            fn=on_upload_wrap, inputs=[file], outputs=[upload_msg, uploaded_questions]
        )

        # 粘贴范文 → 解析并加入题库，并自动打开第一题
        def on_paste_and_start(content, uq):
            msg, merged = on_paste(content, uq)
            if not merged:
                pool_size = len(uq) if (uq and len(uq) > 0) else len(BUILTIN_QUESTIONS)
                empty_boxes = [gr.update(value="", visible=False)] * MAX_BLANKS
                return (
                    msg, merged,
                    _sentence_to_html("暂无题目。"), *empty_boxes,
                    "", None, merged, "", 0, format_stats(pool_size, 0),
                )
            start_out = on_start(merged, 0)
            return msg, merged, *start_out[0:15], 0, start_out[15]

        btn_paste.click(
            fn=on_paste_and_start,
            inputs=[paste_box, uploaded_questions],
            outputs=[
                upload_msg,
                uploaded_questions,
                question_display,
                *answer_boxes,
                answer_hint,
                current_question,
                uploaded_questions,
                result,
                answered_count,
                stats_display,
            ],
        )

        # 开始/换一题：更新题目、清空空位与结果区、更新统计
        btn_start.click(
            fn=on_start,
            inputs=[uploaded_questions, answered_count],
            outputs=[
                question_display,
                *answer_boxes,
                answer_hint,
                current_question,
                uploaded_questions,
                result,
                stats_display,
            ],
        )

        # 提交：显示结果、已答+1、更新统计
        def submit_wrap(*inputs):
            return on_submit(*inputs)

        btn_submit.click(
            fn=submit_wrap,
            inputs=[*answer_boxes, uploaded_questions, current_question, answered_count],
            outputs=[result, answered_count, stats_display],
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(theme=gr.themes.Soft(), css=CUSTOM_CSS)
