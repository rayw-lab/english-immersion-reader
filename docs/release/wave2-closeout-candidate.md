# Wave-2 Closeout

state=wave2-shipped-candidate

Generated: 2026-06-11

## Scope

This is a local release candidate only. Do not create a public repository, push a tag, enable Pages, or submit an external PR before human review.

## Current Repo State

- Repo: `<repo>`
- Branch: `main`
- Publish plan remains gated by `docs/release/wave2-publish-candidate.md`
- `lessons/` remains ignored and local-only

## Evidence

```text
pytest -q
63 passed
```

```text
pytest tests/verify_browser.py tests/verify_ui_controls.py -q
44 passed
```

```text
clean-copy quickstart:
python3.13 -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest -q
python -m pytest tests/verify_browser.py tests/verify_ui_controls.py -q
python src/build_page.py examples/demo/segments.json --out lessons/demo
python src/tts_generate.py examples/demo/segments.json --out lessons/demo/audio --dry-run
result = 63 passed + 44 passed + demo build ok
```

```text
docs/demo build closeout:
学习页: file://<repo>/docs/demo/index.html
本课: 1280 词 · 难度 中高 · 约 3 天 · 主练: 盲听 + 影子跟读 + 工程表达迁移
建议第一步: 打开页面, 点 开始盲听
词典覆盖 100% (467/467)，划词未命中自动走问 agent
逐词同步数据: 22/22 段已生成
```

```text
docs/demo audio:
segment mp3 = 22
card mp3 = 70
__AUDIO_STATUS__ = {"missing": [], "count": 22, "word_missing": [], "word_count": 70}
```

```text
dogfood TTS skip checks:
YouTube generated=0 skipped=18 failed=0 total=18
OpenAI generated=0 skipped=18 failed=0 total=18
Anthropic generated=0 skipped=17 failed=0 total=17
```

```text
Chromium smoke on docs/demo:
title = Why Reliable AI Features Need Small Interfaces
segments = 22
studyCard = 1
audioMissing = 0
wordMissing = 0
overflow = 0
pageerrors = []
```

```text
subagent gates:
Noether STRANGER-GATE clear
Russell AUDIT-PASS I-1-I-13
```

## Material Changes In This Candidate

- Public demo now includes hard/chunk card audio under `docs/demo/audio/w/`.
- `tts_generate.py` can write optional Edge `WordBoundary` sidecars for segment audio when new segment mp3 files are generated.
- `build_page.py` injects aligned `window.__WORD_TIMINGS__` data when sidecars exist.
- Template runtime consumes `window.__WORD_TIMINGS__` for optional word-following highlight and click-to-seek behavior.
- `docs/demo` was rebuilt from the current template and includes 22/22 segment timing sidecars.
- `docs/release/dogfood-real-content-report.md` now reflects current 12/11/12 dogfood pages and zero audio gaps.

## Residuals

- `@browser` MCP was occupied by another automation Chrome profile during manual open; equivalent Playwright Chromium smoke passed.
- Dogfood lessons intentionally keep low lexicon coverage warnings. They are local dogfood pages, not polished public examples.
- Screenshot artifacts were refreshed by browser verification and remain in the worktree for human review.
- `gh repo view rayw-lab/english-immersion-reader` returned repository-not-found on 2026-06-11; public creation/push remains gated by human review.

## Human Gate

verdict=T-PASS-candidate

Do not run the publish commands in `docs/release/wave2-publish-candidate.md` until human visual review and rights review are done.
