import subprocess
import sys
import types
from pathlib import Path

import tts_generate

ROOT = Path(__file__).resolve().parents[1]
TTS = ROOT / "src" / "tts_generate.py"
DEMO = ROOT / "examples" / "demo" / "segments.json"


def test_tts_dry_run_lists_edge_outputs_and_writes_nothing(tmp_path):
    out = tmp_path / "audio"
    result = subprocess.run(
        [sys.executable, str(TTS), str(DEMO), "--out", str(out), "--dry-run"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "engine=edge" in result.stdout
    assert "seg-01.mp3" in result.stdout
    assert "seg-04.mp3" in result.stdout
    assert "audio/w/reliable.mp3" in result.stdout
    assert "audio/w/clear-constraint.mp3" in result.stdout
    assert not out.exists()


def test_word_audio_slug_handles_spaces_and_apostrophes():
    assert tts_generate.word_audio_slug("Clear constraint") == "clear-constraint"
    assert tts_generate.word_audio_slug("don’t ship it") == "dont-ship-it"
    assert tts_generate.word_audio_slug("A/B loop") == "a-b-loop"


def test_word_audio_default_is_hard_and_chunks_not_full_lexicon(tmp_path):
    result = subprocess.run(
        [sys.executable, str(TTS), str(DEMO), "--out", str(tmp_path / "audio"), "--dry-run"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "audio/w/reliable.mp3" in result.stdout
    assert "audio/w/clear-constraint.mp3" in result.stdout
    assert "audio/w/usually.mp3" not in result.stdout

    result = subprocess.run(
        [
            sys.executable,
            str(TTS),
            str(DEMO),
            "--out",
            str(tmp_path / "audio"),
            "--dry-run",
            "--word-audio",
            "full",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "audio/w/usually.mp3" in result.stdout


def test_word_audio_can_be_disabled(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(TTS),
            str(DEMO),
            "--out",
            str(tmp_path / "audio"),
            "--dry-run",
            "--word-audio",
            "off",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "audio/w/" not in result.stdout


def test_voice_and_rate_cli_options_override_defaults(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(TTS),
            str(DEMO),
            "--out",
            str(tmp_path / "audio"),
            "--dry-run",
            "--voice",
            "en-GB-RyanNeural",
            "--rate",
            "+0%",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "voice=en-GB-RyanNeural" in result.stdout
    assert "rate=+0%" in result.stdout


def test_tts_help_prints_rate_percent_without_crashing():
    result = subprocess.run(
        [sys.executable, str(TTS), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Default: -20%" in result.stdout


def test_kokoro_dry_run_lists_optional_fallback_outputs(tmp_path):
    out = tmp_path / "audio"
    result = subprocess.run(
        [
            sys.executable,
            str(TTS),
            str(DEMO),
            "--out",
            str(out),
            "--engine",
            "kokoro",
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "engine=kokoro" in result.stdout
    assert "seg-01.mp3" in result.stdout
    assert not out.exists()


def test_kokoro_missing_package_message_is_actionable(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(TTS),
            str(DEMO),
            "--out",
            str(tmp_path / "audio"),
            "--engine",
            "kokoro",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode == 0:
        raise AssertionError("Kokoro real synthesis should not silently pass in tests")
    assert "python -m pip install -e '.[local]'" in result.stderr or "--engine edge" in result.stderr


def test_kokoro_adapter_writes_audio_when_optional_backend_is_available(tmp_path, monkeypatch):
    class FakePipeline:
        def __init__(self, lang_code):
            assert lang_code == "a"

        def __call__(self, text, voice, speed):
            assert text == "hello"
            assert voice == "af_heart"
            assert speed == 1.0
            yield None, None, [0.0, 0.1, 0.0]

    fake_kokoro = types.ModuleType("kokoro")
    fake_kokoro.KPipeline = FakePipeline
    fake_soundfile = types.ModuleType("soundfile")

    def fake_write(path, audio, samplerate, format=None):
        assert samplerate == 24000
        assert format == "MP3"
        Path(path).write_bytes(b"fake mp3")

    fake_soundfile.write = fake_write
    monkeypatch.setitem(sys.modules, "kokoro", fake_kokoro)
    monkeypatch.setitem(sys.modules, "soundfile", fake_soundfile)

    output = tmp_path / "seg-01.mp3"
    job = tts_generate.SegmentJob("seg-01", "hello", output, False)
    import asyncio
    rc = asyncio.run(tts_generate.synthesize_kokoro([job], "af_heart", "1.0"))

    assert rc == 0
    assert output.read_bytes() == b"fake mp3"


def test_edge_stream_writes_audio_and_word_boundary_sidecar(tmp_path):
    class FakeCommunicate:
        async def stream(self):
            yield {"type": "audio", "data": b"fake "}
            yield {"type": "WordBoundary", "text": "hello", "offset": 1_000_000, "duration": 2_000_000}
            yield {"type": "audio", "data": b"mp3"}

    output = tmp_path / "seg-01.mp3"
    sidecar = tmp_path / "seg-01.words.json"
    job = tts_generate.SegmentJob("seg-01", "hello", output, False, sidecar)

    import asyncio
    asyncio.run(tts_generate.stream_with_word_boundaries(FakeCommunicate(), job))

    assert output.read_bytes() == b"fake mp3"
    assert sidecar.read_text(encoding="utf-8") == '[{"text": "hello", "t0": 0.1, "t1": 0.3}]'


def test_plan_prefers_tts_text_and_skips_existing_nonempty_file(tmp_path):
    existing = tmp_path / "seg-01.mp3"
    existing.write_bytes(b"not empty")
    segments = [{"id": "seg-01", "tts": "spoken form", "en": "written form"}]

    [job] = tts_generate.plan_segments(segments, tmp_path, force=False)

    assert job.text == "spoken form"
    assert job.output == existing
    assert job.skip is True
    assert job.words_output == tmp_path / "seg-01.words.json"


def test_force_marks_existing_file_for_overwrite(tmp_path):
    existing = tmp_path / "seg-01.mp3"
    existing.write_bytes(b"not empty")

    [job] = tts_generate.plan_segments(
        [{"id": "seg-01", "tts": "", "en": "fallback text"}],
        tmp_path,
        force=True,
    )

    assert job.text == "fallback text"
    assert job.output == existing
    assert job.skip is False
