#!/usr/bin/env python3
import argparse
import html as html_escape
import json
import shutil
import sys
from pathlib import Path

import jsonschema

from lesson_quality import (
    LEXICON_COVERAGE_WARN_THRESHOLD,
    SEGMENT_WORDS_LIMIT,
    british_ipa_entries,
    lexicon_coverage,
    overlong_segments,
    required_word_audio_terms,
    word_audio_slug,
)
from word_sync import align_words

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "segments.schema.json"
TEMPLATE_DIR = HERE / "template"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_lesson(data: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    jsonschema.validate(data, schema)
    validate_transfer_tasks(data)
    validate_study_card(data)


def validate_study_card(data: dict) -> None:
    # the study card is a promise to the learner; fabricated numbers fail the build
    card = data["meta"]["study_card"]
    segments = data["segments"]
    actual_words = sum(len(seg["en"].split()) for seg in segments)
    claimed = card["word_count"]
    tolerance = max(10, round(actual_words * 0.1))
    if abs(claimed - actual_words) > tolerance:
        raise ValueError(
            f"study_card.word_count is {claimed} but the segments contain {actual_words} words"
        )
    if card["segment_count"] != len(segments):
        raise ValueError(
            f"study_card.segment_count is {card['segment_count']} but there are {len(segments)} segments"
        )


def validate_transfer_tasks(data: dict) -> None:
    chunk_terms = {chunk["t"] for chunk in data.get("chunks", [])}
    for idx, task in enumerate(data.get("transfer_tasks", [])):
        missing = [term for term in task.get("hint_chunks", []) if term not in chunk_terms]
        if missing:
            raise ValueError(
                f"transfer_tasks[{idx}].hint_chunks must reference chunks[].t; missing: {', '.join(missing)}"
            )


def audio_status(out_dir: Path, segments: list[dict], word_terms: list[str] | None = None) -> dict:
    audio_dir = out_dir / "audio"
    missing = []
    for seg in segments:
        expected = audio_dir / f"{seg['id']}.mp3"
        if not expected.exists() or expected.stat().st_size == 0:
            missing.append(seg["id"])
    word_missing = []
    for term in word_terms or []:
        expected = audio_dir / "w" / f"{word_audio_slug(term)}.mp3"
        if not expected.exists() or expected.stat().st_size == 0:
            word_missing.append(term)
    return {"missing": missing, "count": len(segments), "word_missing": word_missing, "word_count": len(word_terms or [])}


def word_timings(out_dir: Path, segments: list[dict]) -> dict:
    """Align each segment's WordBoundary sidecar (if present) to its display text."""
    timings: dict[str, list[list[float]]] = {}
    for seg in segments:
        sidecar = out_dir / "audio" / f"{seg['id']}.words.json"
        if not sidecar.exists() or sidecar.stat().st_size == 0:
            continue
        try:
            words = json.loads(sidecar.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        aligned = align_words(words, seg["en"])
        if aligned:
            timings[seg["id"]] = [
                [round(item["t0"], 3), round(item["t1"], 3), item["c0"], item["c1"]]
                for item in aligned
            ]
    return timings


def render_index(data: dict, out_dir: Path) -> None:
    template = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
    # escape every "<" as \u003c inside JSON strings: blocks script-tag breakout and comment-open parsing tricks
    lesson_json = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    status_json = json.dumps(audio_status(out_dir, data["segments"], required_word_audio_terms(data)), ensure_ascii=False)
    timings_json = json.dumps(word_timings(out_dir, data["segments"]), ensure_ascii=False)
    html = (
        template
        .replace("{{TITLE}}", html_escape.escape(data["meta"]["title"]))
        .replace("{{LESSON_JSON}}", lesson_json)
        .replace("{{AUDIO_STATUS_JSON}}", status_json)
        .replace("{{WORD_TIMINGS_JSON}}", timings_json)
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    shutil.copy2(TEMPLATE_DIR / "style.css", out_dir / "style.css")
    shutil.copy2(TEMPLATE_DIR / "app.js", out_dir / "app.js")


def closeout(data: dict, out_dir: Path) -> str:
    card = data["meta"]["study_card"]
    status = audio_status(out_dir, data["segments"], required_word_audio_terms(data))
    coverage = lexicon_coverage(data)
    page = (out_dir / "index.html").resolve().as_uri()
    lines = [
        f"学习页: {page}",
        f"本课: {card['word_count']} 词 · 难度 {card['difficulty']} · 约 {card['estimated_days']} 天 · 主练: {card['main_practice']}",
        "建议第一步: 打开页面, 点 开始盲听",
        f"词典覆盖 {coverage['ratio']:.0%} ({coverage['covered']}/{coverage['total']})，划词未命中自动走问 agent",
    ]
    if coverage["ratio"] < LEXICON_COVERAGE_WARN_THRESHOLD:
        lines.append(f"⚠ 词典覆盖低于 80%，缺 {len(coverage['missing'])} 词，建议补 lexicon 后再交付")
    timings = word_timings(out_dir, data["segments"])
    if timings:
        lines.append(f"逐词同步数据: {len(timings)}/{len(data['segments'])} 段已生成")
    if status["missing"]:
        lines.append(
            f"⚠ {len(status['missing'])} 段音频缺失, 页面自动用浏览器朗读兜底; 重跑: python src/tts_generate.py <segments.json> --out <lesson>/audio"
        )
    if status["word_missing"]:
        lines.append(
            f"⚠ 词音频缺失 {len(status['word_missing'])}/{status['word_count']} 个, 卡片将用浏览器朗读兜底; 重跑: python src/tts_generate.py <segments.json> --out <lesson>/audio"
        )
    overlong = overlong_segments(data)
    if overlong:
        sample = " ".join(f"§{sid.split('-')[1].lstrip('0') or '0'}({words}词)" for sid, words in overlong[:6])
        lines.append(
            f"⚠ {len(overlong)} 段超 {SEGMENT_WORDS_LIMIT} 词: {sample}; 长段拉垮中英双栏观感, 建议拆段后重编译"
        )
    british_ipa = british_ipa_entries(data)
    if british_ipa:
        sample = ", ".join(f"{term} {ipa}" for term, ipa in british_ipa[:8])
        lines.append(f"⚠ IPA 风格警告: 检出英式特征 {len(british_ipa)} 处（{sample}）; 建议统一美式 IPA")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a static Immersion Reader lesson page.")
    parser.add_argument("segments_json", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        data = load_json(args.segments_json)
        validate_lesson(data)
    except Exception as exc:
        print(f"schema validation failed: {exc}", file=sys.stderr)
        return 2

    render_index(data, args.out)
    print(closeout(data, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
