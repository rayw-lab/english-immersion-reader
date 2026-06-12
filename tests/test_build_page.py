import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "src" / "build_page.py"
DEMO = ROOT / "examples" / "demo" / "segments.json"


def test_build_page_creates_index_and_assets(tmp_path):
    out = tmp_path / "lesson"
    result = subprocess.run(
        [sys.executable, str(BUILD), str(DEMO), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "window.__LESSON_DATA__" in html
    assert "Why Reliable AI Features Need Small Interfaces" in html
    assert (out / "style.css").exists()
    assert (out / "app.js").exists()
    assert "学习页:" in result.stdout
    assert "建议第一步:" in result.stdout
    assert "词典覆盖" in result.stdout
    assert "词音频缺失" in result.stdout


def test_build_page_warns_on_british_ipa_markers(tmp_path):
    data = json.loads(DEMO.read_text(encoding="utf-8"))
    data["lexicon"]["british_probe"] = {"def": "测试词", "ipa": "/bəʊt/"}
    data["lexicon"]["lot_probe"] = {"def": "测试词", "ipa": "/lɒt/"}
    data["lexicon"]["long_probe"] = {"def": "测试词", "ipa": "/kɜːr/"}
    lesson = tmp_path / "british-ipa.json"
    lesson.write_text(json.dumps(data), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(BUILD), str(lesson), "--out", str(tmp_path / "lesson")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "IPA 风格警告" in result.stdout
    assert "british_probe" in result.stdout
    assert "lot_probe" in result.stdout
    assert "long_probe" in result.stdout


def test_build_page_rejects_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    data = json.loads(DEMO.read_text(encoding="utf-8"))
    del data["segments"][0]["zh"]
    bad.write_text(json.dumps(data), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(BUILD), str(bad), "--out", str(tmp_path / "lesson")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "schema validation failed" in result.stderr


def test_build_page_rejects_transfer_hint_not_in_chunks(tmp_path):
    bad = tmp_path / "bad-hint.json"
    data = json.loads(DEMO.read_text(encoding="utf-8"))
    data["transfer_tasks"][0]["hint_chunks"] = ["clear constraint", "recover from failure", "missing chunk"]
    bad.write_text(json.dumps(data), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(BUILD), str(bad), "--out", str(tmp_path / "lesson")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "hint_chunks must reference chunks" in result.stderr


def test_build_page_treats_empty_mp3_as_missing(tmp_path):
    from build_page import audio_status

    out = tmp_path / "lesson"
    audio = out / "audio"
    audio.mkdir(parents=True)
    (audio / "seg-01.mp3").write_bytes(b"")

    status = audio_status(out, [{"id": "seg-01"}])

    assert status["missing"] == ["seg-01"]


def test_build_page_reports_word_audio_missing(tmp_path):
    from build_page import audio_status

    out = tmp_path / "lesson"
    audio = out / "audio"
    (audio / "w").mkdir(parents=True)
    (audio / "seg-01.mp3").write_bytes(b"mp3")
    (audio / "w" / "reliable.mp3").write_bytes(b"")

    status = audio_status(out, [{"id": "seg-01"}], word_terms=["reliable", "clear constraint"])

    assert status["missing"] == []
    assert status["word_missing"] == ["reliable", "clear constraint"]


def test_build_page_embeds_aligned_word_timing_sidecar(tmp_path):
    from build_page import word_timings

    out = tmp_path / "lesson"
    audio = out / "audio"
    audio.mkdir(parents=True)
    (audio / "seg-01.words.json").write_text(
        json.dumps([
            {"text": "A", "t0": 0.0, "t1": 0.2},
            {"text": "reliable", "t0": 0.2, "t1": 0.7},
        ]),
        encoding="utf-8",
    )

    timings = word_timings(out, [{"id": "seg-01", "en": "A reliable feature."}])

    assert timings == {"seg-01": [[0.0, 0.2, 0, 1], [0.2, 0.7, 2, 10]]}


def test_build_page_low_lexicon_coverage_warns_without_failing(tmp_path):
    data = json.loads(DEMO.read_text(encoding="utf-8"))
    data["lexicon"] = {}
    lesson = tmp_path / "low-coverage.json"
    lesson.write_text(json.dumps(data), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(BUILD), str(lesson), "--out", str(tmp_path / "lesson")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "词典覆盖" in result.stdout
    assert "低于 80%" in result.stdout


def test_build_page_rejects_fabricated_study_card_numbers(tmp_path):
    """study_card claims must match the actual content: a hand-written
    word_count that is 4x reality (430 vs ~100) must fail the build."""
    data = json.loads(DEMO.read_text(encoding="utf-8"))

    bad_words = tmp_path / "bad-words.json"
    fake = dict(data)
    fake["meta"] = json.loads(json.dumps(data["meta"]))
    fake["meta"]["study_card"]["word_count"] = data["meta"]["study_card"]["word_count"] * 4
    bad_words.write_text(json.dumps(fake), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(BUILD), str(bad_words), "--out", str(tmp_path / "lesson-a")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "word_count" in result.stderr

    bad_segs = tmp_path / "bad-segs.json"
    fake = json.loads(json.dumps(data))
    fake["meta"]["study_card"]["segment_count"] = len(data["segments"]) + 7
    bad_segs.write_text(json.dumps(fake), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(BUILD), str(bad_segs), "--out", str(tmp_path / "lesson-b")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "segment_count" in result.stderr


def test_build_injects_word_timings_placeholder(tmp_path):
    out = tmp_path / "lesson"
    result = subprocess.run(
        [sys.executable, str(BUILD), str(DEMO), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "window.__WORD_TIMINGS__" in html
    assert "{{WORD_TIMINGS_JSON}}" not in html
