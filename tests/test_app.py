# -*- coding: utf-8 -*-
"""
标点学堂 - app 层单元测试：format_stats、on_start 清空结果与统计、on_submit 更新已答数。
"""
import pytest

from app import format_stats, on_start, on_submit, MAX_BLANKS, BUILTIN_QUESTIONS


def test_format_stats():
    assert "总题数：10" in format_stats(10, 0)
    assert "剩余：10" in format_stats(10, 0)
    assert "已答：0" in format_stats(10, 0)
    assert "总题数：5" in format_stats(5, 2)
    assert "剩余：3" in format_stats(5, 2)
    assert "已答：2" in format_stats(5, 2)
    assert format_stats(0, 0) == "**总题数：0** &nbsp; **剩余：0** &nbsp; **已答：0**"


def test_on_start_returns_cleared_result_and_stats():
    out = on_start([], 0)
    assert len(out) == 16
    assert out[-2] == ""
    assert "总题数" in out[-1]


def test_on_start_clears_boxes_with_empty_value():
    pool = BUILTIN_QUESTIONS[:1]
    out = on_start(pool, 0)
    assert len(out) == 16
    for i in range(1, 1 + MAX_BLANKS):
        u = out[i]
        val = u.get("value") if isinstance(u, dict) else getattr(u, "value", None)
        assert val == ""


def test_on_submit_increments_answered_and_returns_stats():
    current = {
        "text": "春天来了，花开了。",
        "blanks": [{"pos": 4, "char": "，"}, {"pos": 10, "char": "。"}],
    }
    inputs = ["，", "。"] + [""] * (MAX_BLANKS - 2)
    inputs += [[], current, 0]  # uploaded_questions, current_question, answered_count
    result_html, new_answered, stats_str = on_submit(*inputs)
    assert new_answered == 1
    assert "已答：1" in stats_str
    assert "结果" in result_html
