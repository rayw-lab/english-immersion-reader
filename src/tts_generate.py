#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Sequence

from lesson_quality import required_word_audio_terms, word_audio_slug

DEFAULT_VOICE = "en-US-AndrewNeural"
DEFAULT_RATE = "-20%"
DEFAULT_KOKORO_VOICE = "af_heart"
# mirrors segments.schema.json id pattern; standalone runs skip jsonschema, so re-enforce here
SEGMENT_ID_PATTERN = re.compile(r"^seg-[0-9]{2,}$")
PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy")
WORD_AUDIO_MODES = ("hard", "full", "off")


@dataclass(frozen=True)
class SegmentJob:
    segment_id: str
    text: str
    output: Path
    skip: bool
    # optional Edge WordBoundary sidecar for segment jobs
    words_output: Path | None = None


def load_lesson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def segment_text(segment: dict) -> str:
    return str(segment.get("tts") or segment.get("en") or "").strip()


def nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def plan_segments(segments: Sequence[dict], out_dir: Path, force: bool = False) -> list[SegmentJob]:
    jobs = []
    for index, segment in enumerate(segments, 1):
        segment_id = segment.get("id")
        if not isinstance(segment_id, str) or not SEGMENT_ID_PATTERN.fullmatch(segment_id):
            raise ValueError(f"segments[{index - 1}].id must match seg-NN, got: {segment_id!r}")
        output = out_dir / f"{segment_id}.mp3"
        words_output = out_dir / f"{segment_id}.words.json"
        jobs.append(
            SegmentJob(
                segment_id=segment_id,
                text=segment_text(segment),
                output=output,
                skip=(not force and nonempty_file(output)),
                words_output=words_output,
            )
        )
    return jobs


def lexicon_terms(data: dict) -> list[str]:
    lex = data.get("lexicon") or {}
    if not isinstance(lex, dict):
        return []
    return [str(term).strip() for term in lex if str(term).strip()]


def unique_terms(terms: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        key = word_audio_slug(term)
        if key in seen:
            continue
        seen.add(key)
        out.append(term)
    return out


def plan_word_audio(data: dict, out_dir: Path, mode: str = "hard", force: bool = False) -> list[SegmentJob]:
    if mode == "off":
        return []
    if mode not in WORD_AUDIO_MODES:
        raise ValueError(f"word-audio must be one of: {', '.join(WORD_AUDIO_MODES)}")

    terms = required_word_audio_terms(data)
    if mode == "full":
        terms += lexicon_terms(data)

    jobs: list[SegmentJob] = []
    for term in unique_terms(terms):
        output = out_dir / "w" / f"{word_audio_slug(term)}.mp3"
        jobs.append(
            SegmentJob(
                segment_id=f"w/{word_audio_slug(term)}",
                text=term,
                output=output,
                skip=(not force and nonempty_file(output)),
            )
        )
    return jobs


def engine_config(data: dict, engine_arg: str | None) -> str:
    config = data.get("voice") or {}
    engine = str(engine_arg or config.get("engine") or "edge").lower()
    if engine not in {"edge", "kokoro"}:
        raise ValueError(
            "voice.engine must be 'edge' or 'kokoro'. "
            "Edge is the public default; Kokoro is an optional offline fallback."
        )
    return engine


def voice_config(data: dict, engine: str, voice_arg: str | None, rate_arg: str | None) -> tuple[str, str]:
    config = data.get("voice") or {}
    if engine == "kokoro":
        voice = voice_arg or config.get("kokoro_voice") or DEFAULT_KOKORO_VOICE
        rate = rate_arg or str(config.get("speed") or "1.0")
        return str(voice), str(rate)
    voice = voice_arg or config.get("voice") or DEFAULT_VOICE
    rate = rate_arg or config.get("rate") or DEFAULT_RATE
    return str(voice), str(rate)


def clear_proxy_env() -> None:
    for key in PROXY_KEYS:
        os.environ.pop(key, None)


def missing_edge_tts_message() -> str:
    return (
        "edge-tts package is not installed.\n"
        "Install it with: python -m pip install edge-tts\n"
        "Inside this repo, you can also run: python -m pip install -e '.[dev]'"
    )


def missing_kokoro_message() -> str:
    return (
        "Kokoro optional offline backend is not installed.\n"
        "Install it with: python -m pip install -e '.[local]'\n"
        "Kokoro may also require the system package espeak-ng.\n"
        "Then rerun with: python src/tts_generate.py <segments.json> --out <lesson>/audio --engine kokoro"
    )


def print_plan(jobs: Sequence[SegmentJob], engine: str, voice: str, rate: str, dry_run: bool) -> None:
    dry = " dry_run=true" if dry_run else ""
    print(f"engine={engine} voice={voice} rate={rate}{dry}")
    for job in jobs:
        if job.skip:
            print(f"skip existing {job.output}")
        elif dry_run:
            print(f"would write {job.output}")
        else:
            print(f"will write {job.output}")


async def synthesize_edge(jobs: Sequence[SegmentJob], voice: str, rate: str) -> int:
    try:
        import edge_tts
    except ImportError:
        print(missing_edge_tts_message(), file=sys.stderr)
        return 2

    clear_proxy_env()
    written = 0
    skipped = 0
    failed = 0

    for job in jobs:
        if job.skip:
            skipped += 1
            print(f"skip existing {job.output}")
            continue
        if not job.text:
            failed += 1
            print(f"failed {job.segment_id}: empty tts/en text", file=sys.stderr)
            continue

        job.output.parent.mkdir(parents=True, exist_ok=True)
        try:
            if job.words_output is None:
                communicate = edge_tts.Communicate(job.text, voice, rate=rate)
                await communicate.save(str(job.output))
            else:
                # edge-tts >= 7.2 defaults to SentenceBoundary; word-level sync needs WordBoundary
                try:
                    communicate = edge_tts.Communicate(job.text, voice, rate=rate, boundary="WordBoundary")
                except TypeError:
                    communicate = edge_tts.Communicate(job.text, voice, rate=rate)
                await stream_with_word_boundaries(communicate, job)
        except Exception as exc:
            failed += 1
            print(f"failed {job.segment_id}: {exc}", file=sys.stderr)
            continue

        if not nonempty_file(job.output):
            failed += 1
            print(f"failed {job.segment_id}: output mp3 is missing or empty", file=sys.stderr)
            continue

        written += 1
        print(f"wrote {job.output}")

    print(f"generated={written} skipped={skipped} failed={failed} total={len(jobs)}")
    return 1 if failed else 0


async def stream_with_word_boundaries(communicate, job: SegmentJob) -> None:
    """Write the mp3 while capturing WordBoundary events (offset/duration are 100ns ticks)."""
    words: list[dict] = []
    with job.output.open("wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 10_000_000
                words.append({
                    "text": str(chunk.get("text", "")),
                    "t0": round(start, 3),
                    "t1": round(start + chunk["duration"] / 10_000_000, 3),
                })
    # bind the sidecar to this exact mp3: a size fingerprint lets the build
    # detect (and drop) timings that came from a different synthesis run
    payload = {"mp3_bytes": job.output.stat().st_size, "words": words}
    job.words_output.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


async def synthesize_kokoro(jobs: Sequence[SegmentJob], voice: str, rate: str) -> int:
    try:
        from kokoro import KPipeline
        import soundfile as sf
    except ImportError:
        print(missing_kokoro_message(), file=sys.stderr)
        return 2

    written = 0
    skipped = 0
    failed = 0
    try:
        pipeline = KPipeline(lang_code="a")
    except Exception as exc:
        print(f"failed to initialize Kokoro: {exc}", file=sys.stderr)
        print("Fallback: python src/tts_generate.py <segments.json> --out <lesson>/audio --engine edge", file=sys.stderr)
        return 2

    speed = parse_kokoro_speed(rate)
    for job in jobs:
        if job.skip:
            skipped += 1
            print(f"skip existing {job.output}")
            continue
        if not job.text:
            failed += 1
            print(f"failed {job.segment_id}: empty tts/en text", file=sys.stderr)
            continue

        try:
            audio = kokoro_audio(pipeline, job.text, voice, speed)
            job.output.parent.mkdir(parents=True, exist_ok=True)
            write_audio_mp3(sf, audio, job.output)
        except Exception as exc:
            failed += 1
            print(f"failed {job.segment_id}: {exc}", file=sys.stderr)
            print("Fallback: python src/tts_generate.py <segments.json> --out <lesson>/audio --engine edge", file=sys.stderr)
            continue

        if not nonempty_file(job.output):
            failed += 1
            print(f"failed {job.segment_id}: output mp3 is missing or empty", file=sys.stderr)
            continue

        written += 1
        print(f"wrote {job.output}")

    print(f"generated={written} skipped={skipped} failed={failed} total={len(jobs)}")
    return 1 if failed else 0


def parse_kokoro_speed(rate: str) -> float:
    raw = str(rate).strip()
    if raw.endswith("%"):
        return max(0.1, 1 + (float(raw[:-1]) / 100))
    return max(0.1, float(raw))


def kokoro_audio(pipeline, text: str, voice: str, speed: float):
    parts = []
    for _, _, audio in pipeline(text, voice=voice, speed=speed):
        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()
        elif hasattr(audio, "cpu") and hasattr(audio, "numpy"):
            audio = audio.cpu().numpy()
        parts.append(audio)
    if not parts:
        raise RuntimeError("Kokoro produced no audio")
    if len(parts) == 1:
        return parts[0]
    import numpy as np
    return np.concatenate(parts)


def write_audio_mp3(sf, audio, output: Path) -> None:
    try:
        sf.write(str(output), audio, 24000, format="MP3")
        return
    except Exception:
        pass

    with NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)
    try:
        sf.write(str(wav_path), audio, 24000)
        result = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav_path), str(output)],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "soundfile could not write mp3 directly and ffmpeg conversion failed. "
                "Install ffmpeg or use: python src/tts_generate.py <segments.json> --out <lesson>/audio --engine edge"
            )
    finally:
        wav_path.unlink(missing_ok=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Edge TTS mp3 files from segments.json.")
    parser.add_argument("segments_json", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="Audio output directory.")
    parser.add_argument("--engine", choices=["edge", "kokoro"], default=None, help="TTS engine. Default: voice.engine or edge.")
    parser.add_argument("--voice", default=None, help=f"Edge voice name. Default: {DEFAULT_VOICE}")
    parser.add_argument("--rate", default=None, help=f"Edge speaking rate. Default: {DEFAULT_RATE.replace('%', '%%')}")
    parser.add_argument(
        "--word-audio",
        choices=WORD_AUDIO_MODES,
        default="full",
        help="Generate word/chunk card audio under audio/w/. Default: full (hard terms + chunks + lexicon, so selection-card playback never falls back to browser TTS).",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing non-empty mp3 files.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned mp3 outputs without network or writes.")
    return parser.parse_args(argv)


async def run(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        data = load_lesson(args.segments_json)
        segments = data.get("segments")
        if not isinstance(segments, list):
            raise ValueError("segments.json must contain a segments array")
        engine = engine_config(data, args.engine)
        voice, rate = voice_config(data, engine, args.voice, args.rate)
        jobs = plan_segments(segments, args.out, force=args.force)
        jobs += plan_word_audio(data, args.out, mode=args.word_audio, force=args.force)
    except Exception as exc:
        print(f"tts plan failed: {exc}", file=sys.stderr)
        return 2

    print_plan(jobs, engine, voice, rate, dry_run=args.dry_run)
    if args.dry_run:
        return 0
    if engine == "kokoro":
        return await synthesize_kokoro(jobs, voice, rate)
    return await synthesize_edge(jobs, voice, rate)


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(run(argv))


if __name__ == "__main__":
    raise SystemExit(main())
