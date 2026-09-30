import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import formula_ebook as fe
import post_process as pp


def test_sample_frames_use_clip_offset_and_interval(tmp_path):
    frames = [tmp_path / f"{i:04d}.jpg" for i in range(1, 12)]
    for path in frames:
        path.write_bytes(b"x")
    samples = fe.sample_frames(frames, clip_start=1200, interval=5)
    assert [item["second"] for item in samples] == [1200, 1205, 1210]
    assert [item["time"] for item in samples] == ["00:20:00", "00:20:05", "00:20:10"]


def test_collapse_candidates_keeps_last_complete_board_in_each_burst():
    candidates = {time: {"time": time} for time in
                  ("00:20:20", "00:20:25", "00:20:35", "00:20:40", "00:20:45", "00:21:10")}
    selected = fe.collapse_candidates(candidates, max_gap=15, max_span=20)
    assert list(selected) == ["00:20:40", "00:20:45", "00:21:10"]


def test_book_separates_uncertain_formula_and_keeps_evidence():
    items = [
        {"time": "00:20:25", "topic": "函数", "visible": "板书写 f(x)=1/x", "latex": [r"f(x)=\frac1x"], "explanation": "讨论函数。", "status": "clear", "image": "evidence/frame_20_25.jpg"},
        {"time": "00:25:10", "topic": "有界性", "visible": "板书不清楚", "latex": [r"M=\max(M_1,M_2)"], "explanation": "统一上界待核对。", "status": "uncertain", "image": "evidence/frame_25_10.jpg"},
    ]
    md = fe.render_book(items, "课堂公式试读", "https://example.com/video?p=3", 1200, 2100, 5)
    assert "$$\nf(x)=\\frac1x\n$$" in md
    assert "待核对" in md and "M=\\max(M_1,M_2)" not in md
    assert "evidence/frame_20_25.jpg" in md
    assert "?p=3&t=1225" in md


def test_curated_book_keeps_only_selected_source_formulas():
    items = [
        {"time": "00:20:25", "topic": "函数", "visible": "板书", "latex": [r"f(x)=\frac1x", r"|f(x)|\le", "在区间有下界"], "explanation": "讨论函数。", "status": "clear", "image": "evidence/a.jpg"},
        {"time": "00:20:30", "topic": "重复", "visible": "板书", "latex": [r"f(x)=\frac1x"], "explanation": "重复。", "status": "clear", "image": "evidence/b.jpg"},
    ]
    outline = {"sections": [{"heading": "例子", "times": ["00:20:25"]}], "uncertain_times": []}
    md = fe.render_book(items, "数学", "https://example.com/video", 1200, 1235, 5, outline)
    assert "f(x)=\\frac1x" in md
    assert "|f(x)|\\le" not in md and "在区间有下界" not in md
    assert "重复" not in md


def test_review_overrides_a_known_frame_without_changing_raw_observations():
    items = [{"time": "00:34:45", "latex": ["D=[-1,2]"], "status": "clear"}]
    reviewed = fe.apply_review(items, {"overrides": {"00:34:45": {"latex": ["D=[-1,2)"]}}})
    assert reviewed[0]["latex"] == ["D=[-1,2)"]
    assert items[0]["latex"] == ["D=[-1,2]"]


def test_html_supports_math_and_large_evidence_images():
    html = pp.md_to_html("# 数学\n\n$$\n\\left. x \\right\\} > 0\n$$\n\n![图](evidence/a.jpg)", "数学")
    assert "mathjax" in html.lower()
    assert "max-width: 100%" in html
    assert r"\right\}" in html


def test_explanation_escapes_html_without_double_escaping_math():
    assert fe.safe_prose("取 $x_1<x_2$；<script>bad</script>") == (
        "取 $x_1<x_2$；&lt;script&gt;bad&lt;/script&gt;")


def test_image_alt_is_valid_when_observation_contains_brackets():
    item = {"time": "00:34:45", "topic": "函数", "visible": "D=[-1,2)",
            "latex": ["D=[-1,2)"], "explanation": "定义域", "status": "clear",
            "image": "evidence/frame_00_34_45.jpg"}
    book = fe.render_book([item], "数学", "https://example.com", 1200, 2100, 5)
    html = pp.md_to_html(book, "数学")
    assert 'src="evidence/frame_00_34_45.jpg"' in html


def test_formula_tex_only_exports_reviewed_clear_selection():
    items = [{"time": "00:23:15", "latex": [r"|f(x)|\le M"], "status": "clear"},
             {"time": "00:25:10", "latex": [r"M=\max(M_1,M_2)"], "status": "uncertain"}]
    outline = {"sections": [{"times": ["00:23:15", "00:25:10"]}]}
    result = fe.formula_tex(items, outline)
    assert r"|f(x)|\le M" in result
    assert r"M=\max(M_1,M_2)" not in result
