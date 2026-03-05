# -*- coding: utf-8 -*-
"""
标点学堂 - 核心功能单元测试：utils 加载、解析、填空展示、单框拆分、对比、题型筛选。
"""
import random

import pytest

from utils import (
    load_builtin_articles,
    parse_uploaded_txt,
    get_segments,
    build_display_text,
    split_single_box_answer,
    compare_answers,
    filter_questions_by_type,
    pick_random_question,
    MAX_STEM_LENGTH,
)


# ----- load_builtin_articles -----


def test_load_builtin_articles_returns_list():
    questions = load_builtin_articles()
    assert isinstance(questions, list)


def test_load_builtin_articles_has_expected_structure():
    questions = load_builtin_articles()
    assert len(questions) >= 1
    q = questions[0]
    assert "text" in q and "blanks" in q
    assert isinstance(q["text"], str) and len(q["text"]) > 0
    assert isinstance(q["blanks"], list) and len(q["blanks"]) >= 1
    b = q["blanks"][0]
    assert "pos" in b and "char" in b


def test_load_builtin_articles_blanks_positions_match_text():
    questions = load_builtin_articles()
    for q in questions:
        text = q["text"]
        for b in q["blanks"]:
            pos = b["pos"]
            assert 0 <= pos < len(text), f"pos {pos} out of range for text length {len(text)}"
            assert text[pos] == b["char"], f"text[{pos}]={text[pos]!r} != char {b['char']!r}"


# ----- parse_uploaded_txt：显式标注 -----


def test_parse_uploaded_txt_explicit_single_segment():
    content = "春天来了【，】花园里的花都开了【。】"
    result = parse_uploaded_txt(content)
    assert len(result) == 1
    q = result[0]
    assert q["text"] == "春天来了，花园里的花都开了。"
    assert len(q["blanks"]) == 2
    assert q["blanks"][0]["char"] == "，" and q["blanks"][0]["pos"] == 4
    assert q["blanks"][1]["char"] == "。" and q["blanks"][1]["pos"] == 13


def test_parse_uploaded_txt_explicit_multiple_segments():
    content = "第一段【，】结束。\n\n第二段【。】"
    result = parse_uploaded_txt(content)
    assert len(result) == 2
    assert result[0]["text"] == "第一段，结束。"
    assert result[1]["text"] == "第二段。"


def test_parse_uploaded_txt_explicit_empty_bracket():
    content = "有【】空"
    result = parse_uploaded_txt(content)
    assert len(result) == 1
    # 空【】解析为空格占位，原文变为 "有 空"
    assert "有" in result[0]["text"] and "空" in result[0]["text"]


# ----- parse_uploaded_txt：自动挖空 -----


def test_parse_uploaded_txt_auto_blank_returns_segment_with_blanks():
    content = "春天来了，花园里的花都开了。"
    random.seed(42)
    result = parse_uploaded_txt(content)
    assert len(result) == 1
    q = result[0]
    assert q["text"] == content
    assert 2 <= len(q["blanks"]) <= 5
    for b in q["blanks"]:
        assert 0 <= b["pos"] < len(content)
        assert content[b["pos"]] == b["char"]


def test_parse_uploaded_txt_auto_blank_insufficient_punctuation():
    content = "没有标点"
    result = parse_uploaded_txt(content)
    assert len(result) == 0


def test_parse_uploaded_txt_branch_explicit_vs_auto():
    explicit_content = "一【，】二【。】"
    assert "【" in explicit_content
    result_explicit = parse_uploaded_txt(explicit_content)
    assert len(result_explicit) == 1 and len(result_explicit[0]["blanks"]) == 2

    auto_content = "一，二。"
    result_auto = parse_uploaded_txt(auto_content)
    assert len(result_auto) == 1
    assert 2 <= len(result_auto[0]["blanks"]) <= 5


# ----- parse_uploaded_txt：边界 -----


def test_parse_uploaded_txt_empty():
    assert parse_uploaded_txt("") == []
    assert parse_uploaded_txt("   \n  ") == []


def test_parse_uploaded_txt_split_by_sentence():
    # 按句号分成小题干，每句单独解析（需至少 2 个标点才成题）
    content = "第一句，有标点。第二句，也有。第三句，结束。"
    random.seed(42)
    result = parse_uploaded_txt(content)
    assert len(result) >= 2
    for q in result:
        assert "text" in q and "。" in q["text"]
        assert len(q["text"]) <= 20  # 单句较短


def test_pick_random_question_respects_max_stem_length():
    # 题干超过 MAX_STEM_LENGTH 的题不参与抽取
    long_text = "一" * (MAX_STEM_LENGTH + 1)
    short_text = "春天来了，花开了。"
    questions = [
        {"text": long_text, "blanks": [{"pos": 0, "char": "，", "punctuation_type": "逗号"}]},
        {"text": short_text, "blanks": [{"pos": 4, "char": "，", "punctuation_type": "逗号"}, {"pos": 7, "char": "。", "punctuation_type": "句号"}]},
    ]
    for _ in range(10):
        q = pick_random_question(questions, [])
        assert q is not None
        assert q["text"] == short_text
        assert len(q["text"]) <= MAX_STEM_LENGTH


# ----- get_segments -----


def test_get_segments():
    text = "句子内部并列词语之间用顿号，例如：苹果、香蕉、橙子。"
    blanks = [{"pos": 13}, {"pos": 16}, {"pos": 19}, {"pos": 22}, {"pos": 25}]
    segs = get_segments(text, blanks)
    assert len(segs) == 6
    assert segs[0] == "句子内部并列词语之间用顿号"
    assert segs[1] == "例如"
    assert segs[2] == "苹果"
    assert segs[3] == "香蕉"
    assert segs[4] == "橙子"
    assert segs[5] == ""


def test_get_segments_no_blanks():
    assert get_segments("hello", []) == ["hello"]


# ----- build_display_text -----


def test_build_display_text_replaces_blanks_with_underscores():
    text = "春天来了，花园里的花都开了。"
    blanks = [{"pos": 4, "char": "，"}, {"pos": 13, "char": "。"}]
    display = build_display_text(text, blanks)
    assert display.count("___") == 2
    assert "，" not in display and "。" not in display
    assert display.replace("___", "，", 1).replace("___", "。", 1) == text


def test_build_display_text_empty_blanks_returns_original():
    assert build_display_text("hello", []) == "hello"


def test_build_display_text_ordering_by_pos():
    text = "a，b。c"
    blanks = [{"pos": 3, "char": "。"}, {"pos": 1, "char": "，"}]
    display = build_display_text(text, blanks)
    idx1 = display.index("___")
    idx2 = display.index("___", idx1 + 1)
    assert idx1 < idx2  # 先出现的空是 pos 小的


# ----- split_single_box_answer -----


def test_split_single_box_answer_dunhao():
    assert split_single_box_answer("，、。、；") == ["，", "。", "；"]


def test_split_single_box_answer_comma():
    assert split_single_box_answer("，,。,；") == ["，", "。", "；"]


def test_split_single_box_answer_slash():
    assert split_single_box_answer("，/。/；") == ["，", "。", "；"]


def test_split_single_box_answer_single_answer_no_sep():
    assert split_single_box_answer("。") == ["。"]


def test_split_single_box_answer_empty():
    assert split_single_box_answer("") == []
    assert split_single_box_answer("   ") == []


# ----- compare_answers -----


def test_compare_answers_all_correct():
    user = ["，", "。"]
    blanks = [{"pos": 4, "char": "，"}, {"pos": 13, "char": "。"}]
    count, total, details = compare_answers(user, blanks)
    assert count == 2 and total == 2
    assert all(d["ok"] for d in details)


def test_compare_answers_partial():
    user = ["，", "x"]
    blanks = [{"pos": 4, "char": "，"}, {"pos": 13, "char": "。"}]
    count, total, details = compare_answers(user, blanks)
    assert count == 1 and total == 2
    assert details[0]["ok"] and not details[1]["ok"]
    assert details[1]["user"] == "x" and details[1]["correct"] == "。"


def test_compare_answers_fewer_user_answers():
    user = ["，"]
    blanks = [{"pos": 4, "char": "，"}, {"pos": 13, "char": "。"}]
    count, total, details = compare_answers(user, blanks)
    assert total == 2 and count == 1
    assert details[1]["user"] == "" and details[1]["ok"] is False


# ----- filter_questions_by_type -----


def test_filter_questions_by_type_empty_selection_returns_all():
    questions = load_builtin_articles()
    filtered = filter_questions_by_type(questions, [])
    assert len(filtered) == len(questions)


def test_filter_questions_by_type_filters():
    questions = load_builtin_articles()
    filtered = filter_questions_by_type(questions, ["句号"])
    assert len(filtered) <= len(questions)
    for q in filtered:
        types = {b.get("punctuation_type") for b in q["blanks"]}
        assert "句号" in types


# ----- pick_random_question -----


def test_pick_random_question_returns_one_or_none():
    questions = load_builtin_articles()
    random.seed(123)
    q = pick_random_question(questions, [])
    assert q is not None
    assert "text" in q and "blanks" in q

    q2 = pick_random_question([], [])
    assert q2 is None


def test_pick_random_question_respects_type_filter():
    questions = load_builtin_articles()
    q = pick_random_question(questions, ["逗号", "句号"])
    assert q is not None
    types = {b.get("punctuation_type") for b in q["blanks"]}
    assert types & {"逗号", "句号"}
