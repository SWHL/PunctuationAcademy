# -*- coding: utf-8 -*-
"""
标点学堂 - 工具函数：加载内置文章、解析上传 TXT、生成填空展示、单框拆分答案、对比答案。
"""
import json
import random
import re
from pathlib import Path

# 单框答案分隔符（支持多种，提交时统一拆分）
ANSWER_SEP = "、"
ANSWER_SEP_ALT = ","

# 中文标点集合（用于自动挖空）
CN_PUNCTUATION = set("，。、；：""''（）【】—…")

# 题型列表（与数据中 punctuation_type 一致）
PUNCTUATION_TYPES = ["逗号", "句号", "顿号", "分号", "冒号", "引号", "括号", "省略号", "破折号"]

# 单题题干最大字符数（超过的不参与抽题）
MAX_STEM_LENGTH = 100


def _data_path():
    return Path(__file__).resolve().parent / "data" / "articles.json"


def load_builtin_articles():
    """加载内置文章，打平为题目列表。每题形如 {"text": str, "blanks": [{"pos", "char", "hint", "punctuation_type"}, ...]}"""
    path = _data_path()
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = []
    for art in data.get("articles", []):
        for seg in art.get("segments", []):
            if seg.get("text") and seg.get("blanks"):
                questions.append(
                    {"text": seg["text"], "blanks": seg["blanks"], "title": art.get("title", ""), "source": art.get("source", "")}
                )
    return questions


def _normalize_blanks(blanks):
    """确保 blanks 中每项有 punctuation_type（用于上传解析后的题）。"""
    out = []
    for b in blanks:
        item = dict(b)
        if "punctuation_type" not in item and "hint" in item:
            item["punctuation_type"] = item["hint"]
        elif "punctuation_type" not in item:
            item["punctuation_type"] = "其他"
        out.append(item)
    return out


def _split_by_sentence(text: str) -> list:
    """按句号分割为若干句（不把【】内的句号当作分隔符），每句保留句号。"""
    if not text or not text.strip():
        return []
    # 找出作为分隔符的句号位置（不在【】内）
    in_bracket = False
    split_positions = [-1]
    for i, c in enumerate(text):
        if c == "【":
            in_bracket = True
        elif c == "】":
            in_bracket = False
        elif c == "。" and not in_bracket:
            split_positions.append(i)
    split_positions.append(len(text))
    out = []
    for k in range(len(split_positions) - 1):
        start = split_positions[k] + 1
        end = split_positions[k + 1]
        s = text[start:end].strip()
        if not s:
            continue
        # 句末已有句号（或以【。】结尾）则不补
        if not s.endswith("。") and not s.endswith("【。】"):
            s = s + "。"
        out.append(s)
    return out


def parse_uploaded_txt(content: str) -> list:
    """
    解析用户上传的 TXT 内容。
    - 按句号分割为一段段小题干，再逐段解析。
    - 若包含 【 或 】：按显式标注解析（【标点】为挖空）。
    - 否则：按纯段落自动挖空（识别标点后随机选 2～5 处）。
    返回与内置题目相同结构的列表：[{"text", "blanks", "title", "source"}, ...]
    """
    if not (content or content.strip()):
        return []
    content = content.strip()
    if "【" in content or "】" in content:
        return _parse_explicit(content)
    return _parse_auto_blank(content)


def _parse_explicit(content: str) -> list:
    """显式标注：【X】表示空位。先按空行分大段，再按句号分句，逐句解析。"""
    result = []
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    for para in paragraphs:
        sentences = _split_by_sentence(para)
        for sent in sentences:
            if "【" not in sent and "】" not in sent:
                continue
            matches = list(re.finditer(r"【([^】]*)】", sent))
            if not matches:
                continue
            full_text = re.sub(r"【([^】]*)】", r"\1", sent)
            blanks = []
            for m in matches:
                ans = m.group(1).strip() or " "
                before_seg = sent[: m.start()]
                before_full = re.sub(r"【([^】]*)】", r"\1", before_seg)
                pos_in_full = len(before_full)
                ptype = _char_to_hint(ans) if len(ans) == 1 else (ans if ans in PUNCTUATION_TYPES else "其他")
                blanks.append({"pos": pos_in_full, "char": ans, "hint": ans, "punctuation_type": ptype})
            if full_text and blanks:
                result.append({"text": full_text, "blanks": _normalize_blanks(blanks), "title": "自定义上传", "source": "用户上传"})
    return result


def _parse_auto_blank(content: str) -> list:
    """纯段落：先按空行分大段，再按句号分句，每句单独识别标点并随机挖空 2～5 处。"""
    result = []
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    for para in paragraphs:
        sentences = _split_by_sentence(para)
        for sent in sentences:
            if len(sent) < 2:
                continue
            positions = [(i, c) for i, c in enumerate(sent) if c in CN_PUNCTUATION]
            if len(positions) < 2:
                continue
            n = min(random.randint(2, 5), len(positions))
            chosen = random.sample(positions, n)
            chosen.sort(key=lambda x: x[0])
            blanks = []
            for pos, char in chosen:
                hint = _char_to_hint(char)
                blanks.append({"pos": pos, "char": char, "hint": hint, "punctuation_type": hint})
            if blanks:
                result.append({"text": sent, "blanks": blanks, "title": "自定义上传", "source": "用户上传"})
    return result


def _char_to_hint(char: str) -> str:
    m = {"，": "逗号", "。": "句号", "、": "顿号", "；": "分号", "：": "冒号", '"': "引号", "'": "引号", "（": "括号", "）": "括号", "【": "括号", "】": "括号", "—": "破折号", "…": "省略号"}
    return m.get(char, "其他")


# 空位占位符：用下划线表示填空处，不再用序号
BLANK_PLACEHOLDER = "___"


def get_segments(text: str, blanks: list) -> list:
    """
    按 blanks 的 pos 将 text 拆成 (len(blanks)+1) 段，用于内联填空布局。
    返回 [text[0:pos0], text[pos0+1:pos1], ..., text[pos_n-1+1:]]。
    """
    if not blanks:
        return [text] if text else [""]
    sorted_blanks = sorted(blanks, key=lambda b: b["pos"])
    segments = []
    start = 0
    for b in sorted_blanks:
        pos = b["pos"]
        segments.append(text[start:pos])
        start = pos + 1
    segments.append(text[start:])
    return segments


def build_display_text(text: str, blanks: list) -> str:
    """根据 text 和 blanks 生成带空位的展示文本，空位用下划线 ___ 表示。"""
    if not blanks:
        return text
    blank_positions = {b["pos"] for b in blanks}
    result = []
    i = 0
    while i < len(text):
        if i in blank_positions:
            result.append(BLANK_PLACEHOLDER)
            i += 1
        else:
            result.append(text[i])
            i += 1
    return "".join(result)


def split_single_box_answer(user_input: str) -> list:
    """将单框内的用户答案按约定分隔符拆成列表（支持顿号、逗号、斜杠、空格）。"""
    if not user_input or not user_input.strip():
        return []
    s = user_input.strip()
    for sep in (ANSWER_SEP, ANSWER_SEP_ALT, "/", " "):
        if sep in s:
            return [p.strip() for p in s.split(sep) if p.strip()]
    return [s]


def split_answer_lines(user_input: str) -> list:
    """按行拆分答案（每行一个标点），空行忽略。"""
    if not user_input or not user_input.strip():
        return []
    return [ln.strip() for ln in user_input.strip().split("\n") if ln.strip()]


def compare_answers(user_answers: list, correct_blanks: list) -> tuple:
    """
    对比用户答案列表与正确答案（blanks 的 char 列表）。
    返回 (correct_count, total, details)，details 为 [{"user", "correct", "ok"}, ...]。
    """
    correct_chars = [b["char"] for b in correct_blanks]
    total = len(correct_chars)
    details = []
    for i in range(total):
        user = user_answers[i] if i < len(user_answers) else ""
        correct = correct_chars[i]
        ok = user.strip() == correct.strip()
        details.append({"user": user, "correct": correct, "ok": ok})
    correct_count = sum(1 for d in details if d["ok"])
    return correct_count, total, details


def filter_questions_by_type(questions: list, selected_types: list) -> list:
    """仅保留至少有一个 blank 的 punctuation_type 在 selected_types 中的题目。"""
    if not selected_types:
        return questions
    out = []
    for q in questions:
        for b in q.get("blanks", []):
            if b.get("punctuation_type") in selected_types:
                out.append(q)
                break
    return out


def pick_random_question(questions: list, selected_types: list):
    """从题目池中按题型筛选、题干不超过 MAX_STEM_LENGTH 字后随机选一题；无题时返回 None。"""
    pool = filter_questions_by_type(questions, selected_types)
    pool = [q for q in pool if len(q.get("text", "")) <= MAX_STEM_LENGTH]
    if not pool:
        return None
    return random.choice(pool)


def build_user_filled_text(text: str, blanks: list, user_answers: list) -> str:
    """根据用户答案列表，还原用户填写的完整段落（空白处用？补全）。"""
    sorted_blanks = sorted(blanks, key=lambda b: b["pos"])
    result = []
    idx = 0
    for i, b in enumerate(sorted_blanks):
        pos = b["pos"]
        result.append(text[idx:pos])
        result.append(user_answers[i] if i < len(user_answers) and user_answers[i].strip() else "？")
        idx = pos + 1
    result.append(text[idx:])
    return "".join(result)


def build_result_html(correct_text: str, blanks: list, user_answers: list, details: list) -> str:
    """
    生成结果区 HTML：完整正确答案、用户填写的段落（错误标点标黄）。
    details 来自 compare_answers 的第三项。
    """
    import html
    sorted_blanks = sorted(blanks, key=lambda b: b["pos"])
    # 用户段落，错误处包一层黄色背景
    parts = []
    idx = 0
    for i, b in enumerate(sorted_blanks):
        pos = b["pos"]
        parts.append(html.escape(correct_text[idx:pos]))
        user_char = user_answers[i] if i < len(user_answers) else ""
        if not user_char.strip():
            user_char = "？"
        if i < len(details) and not details[i]["ok"]:
            parts.append(f'<span style="background:#ffeb3b;">{html.escape(user_char)}</span>')
        else:
            parts.append(html.escape(user_char))
        idx = pos + 1
    parts.append(html.escape(correct_text[idx:]))
    user_display = "".join(parts)
    correct_escaped = html.escape(correct_text)
    return f"""<div class="result-card" style="
    margin-top: 1em; padding: 1.2em; border-radius: 12px;
    background: var(--block-background-fill, #f9f9f9);
    border: 1px solid var(--border-color-primary, #e8e8e8);
">
  <div style="margin-bottom: 1em;">
    <div style="font-weight: 600; color: #2e7d32; margin-bottom: 0.35em;">✓ 正确答案</div>
    <p style="margin: 0; line-height: 1.75; font-size: 1.05rem;">{correct_escaped}</p>
  </div>
  <div style="margin-bottom: 0.5em;">
    <div style="font-weight: 600; margin-bottom: 0.35em;">您的答案</div>
    <p style="margin: 0; line-height: 1.75; font-size: 1.05rem;">{user_display}</p>
  </div>
  <p style="margin: 0.5em 0 0; color: #757575; font-size: 0.85rem;">标黄处为错误标点</p>
</div>"""
