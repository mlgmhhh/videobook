"""Scan a video clip with a vision model and build a source-linked formula ebook.

The clip is processed independently of any previous book or formula labels.
Example:
  python src/formula_ebook.py --clip clip.mp4 --clip-start 1200 \
      --transcript transcript.json --output formula_auto --model deepseek-flash
"""

import argparse
import base64
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib import error, parse, request

from PIL import Image, ImageDraw
import imageio_ffmpeg

from post_process import md_to_html


def stamp(second):
    second = int(second)
    return f"{second // 3600:02d}:{second // 60 % 60:02d}:{second % 60:02d}"


def seconds(value):
    parts = [int(part) for part in value.split(":")]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def sample_frames(paths, clip_start, interval):
    if interval < 1:
        raise ValueError("sample interval must be at least one second")
    return [
        {"second": clip_start + offset, "time": stamp(clip_start + offset), "path": str(paths[offset])}
        for offset in range(0, len(paths), interval)
    ]


def collapse_candidates(candidates, max_gap, max_span):
    """Keep the last board in each short burst of progressive handwriting."""
    chosen = {}
    burst = []
    for time in sorted(candidates):
        if burst and (seconds(time) - seconds(burst[-1]) > max_gap or
                      seconds(time) - seconds(burst[0]) > max_span):
            chosen[burst[-1]] = candidates[burst[-1]]
            burst = []
        burst.append(time)
    if burst:
        chosen[burst[-1]] = candidates[burst[-1]]
    return chosen


def transcript_near(segments, first, last, limit=1800):
    lines = [
        f"{segment['start']} {segment['text']}"
        for segment in segments
        if seconds(segment["start"]) <= last and seconds(segment["end"]) >= first
    ]
    return "\n".join(lines)[:limit]


def make_sheet(samples, path):
    width, height = 960, 540
    sheet = Image.new("RGB", (width * 3, (height + 30) * 2), "white")
    draw = ImageDraw.Draw(sheet)
    for index, item in enumerate(samples):
        x, y = index % 3 * width, index // 3 * (height + 30)
        with Image.open(item["path"]) as image:
            sheet.paste(image.convert("RGB").resize((width, height)), (x, y + 30))
        draw.text((x + 8, y + 7), item["time"], fill="black")
    sheet.save(path, quality=88)


def extract_frames(clip, directory):
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.glob("*.jpg")):
        return sorted(directory.glob("*.jpg"))
    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-i", str(clip),
               "-vf", "fps=1,scale=960:-1", "-q:v", "3", str(directory / "%05d.jpg")]
    subprocess.run(command, check=True)
    return sorted(directory.glob("*.jpg"))


def full_frame(clip, relative_second, path):
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
                    "-ss", str(relative_second), "-i", str(clip), "-frames:v", "1", "-y", str(path)],
                   check=True)


def parse_json_answer(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    return json.loads(text)


class VisionClient:
    def __init__(self, base_url, model, key):
        if not (base_url and model and key):
            raise ValueError("vision base URL, model and API key are required")
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.key = key

    def ask(self, prompt, image=None, max_tokens=1600):
        content = [{"type": "text", "text": prompt}]
        if image is not None:
            content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,"
                            + base64.b64encode(Path(image).read_bytes()).decode("ascii")}})
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": 0,
            "thinking": {"type": "disabled"},
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": content}],
        }
        req = request.Request(self.url, data=json.dumps(payload).encode("utf-8"),
                              headers={"Authorization": f"Bearer {self.key}",
                                       "Content-Type": "application/json"})
        for attempt in range(3):
            try:
                with request.urlopen(req, timeout=120) as response:
                    body = json.load(response)
                answer = body["choices"][0]["message"]["content"] or ""
                if not answer.strip():
                    raise RuntimeError(f"vision model returned no text (finish: {body['choices'][0].get('finish_reason')})")
                return parse_json_answer(answer)
            except error.HTTPError as exc:
                if exc.code not in (429, 500, 502, 503) or attempt == 2:
                    raise RuntimeError(f"vision API returned HTTP {exc.code}") from exc
                time.sleep(2 ** attempt)
        raise RuntimeError("vision API did not respond")


def scan_prompt(samples, transcript):
    times = ", ".join(item["time"] for item in samples)
    return (
        "你在检查数学课程视频的六格时间序列截图。只根据可见板书找新出现或发生变化的数学式、定义、图像例子；"
        "邻近字幕只用于校准术语，不得凭字幕编造看不到的公式。重复板书只选最清晰的一格。"
        "返回严格 JSON：{\"candidates\":[{\"time\":\"HH:MM:SS\",\"reason\":\"短说明\"}]}。"
        "time 必须取下列标签之一；没有新内容返回空数组。请优先保证不漏掉短暂出现的关键例子。\n"
        f"画面时间：{times}\n邻近字幕：\n{transcript}"
    )


def detail_prompt(item, transcript):
    return (
        "请独立核对这一张数学课堂画面，并用邻近字幕校准口述。只转写清晰可见的数学式，不补写推导中缺失的步骤。"
        "返回严格 JSON，字段为 topic(简短主题), visible(板书事实), latex(可确认的 LaTeX 字符串数组), "
        "explanation(不超过一句、仅陈述画面或口述支持的结论), status(clear 或 uncertain)。"
        "若符号或结论看不清，status=uncertain，latex 留空，在 visible 写明疑点。"
        f"\n画面时间：{item['time']}。邻近字幕：\n{transcript}"
    )


def video_link(url, second):
    parts = parse.urlsplit(url)
    query = parse.parse_qs(parts.query)
    query["t"] = [str(second)]
    return parse.urlunsplit(parts._replace(query=parse.urlencode(query, doseq=True)))


def display_formulas(formulas):
    selected = []
    for formula in formulas:
        if (re.search(r"(?:\\(?:leq?|geq?|Rightarrow|Leftrightarrow)|[=<>])\s*$", formula)
                or not re.search(r"=|[<>]|\\(?:le|ge|subset|in|Rightarrow|Leftrightarrow)", formula)
                or (re.search(r"[\u4e00-\u9fff]", formula) and "\\text" not in formula)):
            continue
        if formula not in selected:
            selected.append(formula)
    return selected


def curation_prompt(items):
    compact = [{"time": item["time"], "topic": item["topic"], "visible": item["visible"],
                "latex": item["latex"], "status": item["status"]} for item in items]
    return (
        "从以下视频画面逐张识别记录中，选出适合电子书的关键画面。只用记录，不添加外部知识或新公式。"
        "把同一板书逐笔写成的重复帧合并，优先选内容完整的画面；保留每个不同的定义、推理和例子，"
        "尤其检查定义域、区间端点和片段末尾的新例子。"
        "返回严格 JSON：{\"sections\":[{\"heading\":\"简短小节标题\",\"times\":[\"HH:MM:SS\"]}],"
        "\"uncertain_times\":[\"HH:MM:SS\"]}。"
        "sections 只选 status=clear 的 8–14 个不同时间；uncertain_times 只选重要且无法确认的画面，最多 3 个。"
        "所有时间必须逐字取自记录，不要选择跨入下一话题但没有公式的画面。\n"
        + json.dumps(compact, ensure_ascii=False)
    )


def apply_review(items, review):
    reviewed = [{**item, "latex": list(item["latex"])} for item in items]
    by_time = {item["time"]: item for item in reviewed}
    allowed = {"topic", "visible", "explanation", "latex", "status"}
    for time, changes in review.get("overrides", {}).items():
        if time not in by_time or set(changes) - allowed:
            raise ValueError(f"invalid review override: {time}")
        by_time[time].update(changes)
    return reviewed


def safe_prose(value):
    parts = re.split(r"(\$[^$\n]+\$)", str(value))
    return "".join(part if part.startswith("$") and part.endswith("$") else escape(part)
                   for part in parts)


def formula_tex(items, outline):
    source = {item["time"]: item for item in items if item["status"] == "clear"}
    lines = []
    for section in outline.get("sections", []):
        for time in section.get("times", []):
            if time in source:
                for formula in display_formulas(source[time]["latex"]):
                    lines.extend([f"% {time}", r"\[", formula, r"\]", ""])
    return "\n".join(lines)


def render_book(items, title, video_url, start, end, interval, outline=None, reviewed=False):
    lines = [f"# {title}", "", f"[原视频 {stamp(start)}–{stamp(end)}]({video_link(video_url, start)})", "",
             ("本篇先由视觉模型独立检查画面和邻近字幕，再对入书内容人工复核。" if reviewed else
              "本篇是视觉模型独立生成的草稿，尚未人工逐式复核。")
             + f"每 {interval} 秒取一张候选画面；短暂画面仍可能漏检。", ""]
    source = {item["time"]: item for item in items}
    if outline:
        groups = []
        used = set()
        for section in outline.get("sections", []):
            selected = [source[t] for t in section.get("times", [])
                        if t in source and source[t]["status"] == "clear" and t not in used]
            used.update(item["time"] for item in selected)
            if selected:
                groups.append((section.get("heading", "课堂板书"), selected))
        if not groups:
            raise ValueError("curation selected no valid source frames")
        uncertain = [source[t] for t in outline.get("uncertain_times", [])
                     if t in source and source[t]["status"] != "clear"]
    else:
        groups = [(None, [item for item in items if item["status"] == "clear"])]
        uncertain = [item for item in items if item["status"] != "clear"]
    for heading, group in groups:
        if heading:
            lines.extend([f"## {escape(str(heading))}", ""])
        for item in group:
            level = "###" if heading else "##"
            lines.extend([f"{level} {item['time']} · {escape(item['topic'])}", "",
                          safe_prose(item["explanation"]), ""])
            for formula in display_formulas(item["latex"]) if outline else item["latex"]:
                lines.extend(["$$", formula, "$$", ""])
            lines.extend([f"![{item['time']} 课堂板书]({item['image']})", "",
                          f"[回到原视频]({video_link(video_url, seconds(item['time']))})", ""])
    if uncertain:
        lines.extend(["## 待核对", "", "以下画面有数学内容，但识别结果不足以写成确定公式。", ""])
        for item in uncertain:
            lines.extend([f"### {item['time']} · {escape(item['topic'])}", "", escape(item["visible"]), "",
                          f"![待核对画面]({item['image']})", "",
                          f"[回到原视频]({video_link(video_url, seconds(item['time']))})", ""])
    return "\n".join(lines)


def run(args):
    output = Path(args.output)
    scan_dir = output / "scan"
    evidence_dir = output / "evidence"
    scan_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    transcript = json.loads(Path(args.transcript).read_text(encoding="utf-8"))
    frames = sorted(Path(args.frames_dir).glob("*.jpg")) if args.frames_dir else extract_frames(Path(args.clip), output / "frames")
    if not frames:
        raise ValueError("no one-second video frames found")
    samples = sample_frames(frames, args.clip_start, args.sample_seconds)
    batches = [samples[index:index + 6] for index in range(0, len(samples), 6)]
    for index, batch in enumerate(batches):
        path = scan_dir / f"window_{index:03d}.jpg"
        if not path.exists():
            make_sheet(batch, path)
    manifest = {"clip": str(Path(args.clip).resolve()), "source_start": args.clip_start,
                "source_end": args.clip_start + len(frames), "one_second_frames": len(frames),
                "sample_seconds": args.sample_seconds, "sampled_frames": len(samples), "windows": len(batches),
                "model": args.model, "video_url": transcript["video_url"]}
    (output / "coverage.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.dry_run:
        print(json.dumps(manifest, ensure_ascii=False))
        return
    key = os.getenv("VIDEOBOOK_VISION_API_KEY")
    client = VisionClient(args.api_base, args.model, key)
    candidate_by_time = {}
    for index, batch in enumerate(batches):
        cache = scan_dir / f"window_{index:03d}.json"
        if cache.exists():
            result = json.loads(cache.read_text(encoding="utf-8"))
        else:
            result = client.ask(scan_prompt(batch, transcript_near(transcript["segments"],
                                                         batch[0]["second"], batch[-1]["second"] + 5)),
                                scan_dir / f"window_{index:03d}.jpg")
            cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        allowed = {item["time"] for item in batch}
        for candidate in result.get("candidates", []):
            if candidate.get("time") in allowed:
                candidate_by_time[candidate["time"]] = candidate
        print(f"scan {index + 1}/{len(batches)}: {len(candidate_by_time)} candidates", flush=True)
    raw_candidates = candidate_by_time
    candidate_by_time = collapse_candidates(raw_candidates, args.merge_gap, args.merge_span)
    manifest["raw_candidates"] = len(raw_candidates)
    manifest["detail_candidates"] = len(candidate_by_time)
    (output / "coverage.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "candidates.json").write_text(json.dumps({"raw": raw_candidates, "selected": candidate_by_time},
                                             ensure_ascii=False, indent=2), encoding="utf-8")
    items = []
    for item in samples:
        if item["time"] not in candidate_by_time:
            continue
        short = item["time"].replace(":", "_")
        image = evidence_dir / f"frame_{short}.jpg"
        if not image.exists():
            full_frame(args.clip, item["second"] - args.clip_start, image)
        cache = evidence_dir / f"frame_{short}.json"
        if cache.exists():
            detail = json.loads(cache.read_text(encoding="utf-8"))
        else:
            detail = client.ask(detail_prompt(item, transcript_near(transcript["segments"],
                                                               item["second"] - 15, item["second"] + 15)), image)
            cache.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
        latex = detail.get("latex", [])
        status = detail.get("status", "uncertain")
        if not isinstance(latex, list) or not all(isinstance(value, str) for value in latex):
            latex, status = [], "uncertain"
        items.append({"time": item["time"], "topic": str(detail.get("topic", "数学板书")),
                      "visible": str(detail.get("visible", "画面待核对")),
                      "explanation": str(detail.get("explanation", "")), "latex": latex,
                      "status": "clear" if status == "clear" else "uncertain",
                      "image": f"evidence/{image.name}"})
        print(f"detail {len(items)}/{len(candidate_by_time)}: {item['time']}", flush=True)
    observations = json.dumps(items, ensure_ascii=False, indent=2)
    (output / "observations.json").write_text(observations, encoding="utf-8")
    title = transcript.get("title", "视频课程") + " · 公式识别试读"
    raw_book = render_book(items, title, transcript["video_url"], args.clip_start,
                           args.clip_start + len(frames), args.sample_seconds)
    (output / "book.all_candidates.md").write_text(raw_book, encoding="utf-8")
    (output / "book.all_candidates.html").write_text(md_to_html(raw_book, title), encoding="utf-8")
    outline_path = output / "outline.json"
    source_hash = hashlib.sha256(observations.encode("utf-8")).hexdigest()
    outline = json.loads(outline_path.read_text(encoding="utf-8")) if outline_path.exists() else {}
    if outline.get("source_sha256") != source_hash:
        outline = client.ask(curation_prompt(items), max_tokens=2500)
        outline["source_sha256"] = source_hash
        outline_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
    book = render_book(items, title, transcript["video_url"], args.clip_start,
                       args.clip_start + len(frames), args.sample_seconds, outline)
    (output / "book.md").write_text(book, encoding="utf-8")
    (output / "book.html").write_text(md_to_html(book, title), encoding="utf-8")
    (output / "formulas.tex").write_text(formula_tex(items, outline), encoding="utf-8")
    if args.review_file:
        review = json.loads(Path(args.review_file).read_text(encoding="utf-8"))
        reviewed_items = apply_review(items, review)
        reviewed_title = title + "（人工复核）"
        reviewed_book = render_book(reviewed_items, reviewed_title, transcript["video_url"],
                                    args.clip_start, args.clip_start + len(frames), args.sample_seconds,
                                    review, reviewed=True)
        (output / "book.reviewed.md").write_text(reviewed_book, encoding="utf-8")
        (output / "book.reviewed.html").write_text(md_to_html(reviewed_book, reviewed_title), encoding="utf-8")
        (output / "formulas.reviewed.tex").write_text(formula_tex(reviewed_items, review), encoding="utf-8")
        print(f"reviewed ebook: {output / 'book.reviewed.html'}")
    print(f"ebook: {output / 'book.html'}")


def main():
    parser = argparse.ArgumentParser(description="Visually scan a clip and make a formula ebook")
    parser.add_argument("--clip", required=True, help="local video clip")
    parser.add_argument("--clip-start", type=int, default=0, help="clip start in source video, seconds")
    parser.add_argument("--transcript", required=True, help="source transcript.json")
    parser.add_argument("--output", required=True, help="independent output directory")
    parser.add_argument("--frames-dir", help="optional existing 1 fps frames directory")
    parser.add_argument("--sample-seconds", type=int, default=5)
    # ponytail: merging saves model calls but can hide a quick topic change; opt in when cost matters.
    parser.add_argument("--merge-gap", type=int, default=1, help="maximum seconds between writing steps")
    parser.add_argument("--merge-span", type=int, default=20, help="maximum seconds in one writing burst")
    parser.add_argument("--model", default=os.getenv("VIDEOBOOK_VISION_MODEL"))
    parser.add_argument("--api-base", default=os.getenv("VIDEOBOOK_VISION_BASE_URL"))
    parser.add_argument("--dry-run", action="store_true", help="prepare local contact sheets only")
    parser.add_argument("--review-file", help="optional JSON overlay for a separately reviewed ebook")
    args = parser.parse_args()
    if args.clip_start < 0 or min(args.sample_seconds, args.merge_gap, args.merge_span) < 1:
        parser.error("clip start must be nonnegative and intervals must be positive")
    if not args.dry_run and not args.model:
        parser.error("set --model or VIDEOBOOK_VISION_MODEL")
    run(args)


if __name__ == "__main__":
    main()
