# Immersion Reader Wave-2 Superaudit

state=wave2-shipped-candidate

Generated: 2026-06-11

## Executive Verdict

verdict=T-PASS-candidate

No P0/P1 found in the current local candidate after the final test loop. This does not replace human visual review or rights review.

## Audit Scope

- Static compiler and template runtime
- Edge TTS segment/card audio pipeline
- Public demo under `docs/demo`
- Local dogfood pages under ignored `lessons/`
- Release documentation under `docs/release/`

## Baseline Matrix

| Item | Evidence |
|---|---|
| Start baseline | Wave-2 plan recorded `start_head=180140f`; current branch is `main`; final candidate was committed after the local audit loop. |
| Source spec | `docs/superpowers/specs/2026-06-11-immersion-reader-wave2-improvements.md` I-1 through I-13. |
| TDD plan | `docs/superpowers/plans/2026-06-11-immersion-reader-wave2-tdd-execution-plan.md`. |
| Work repo | `<repo>`. |
| Publish boundary | `docs/release/wave2-publish-candidate.md` keeps publish commands under human review. |

## Findings

| ID | Severity | Status | Finding | Resolution |
|---|---:|---|---|---|
| W2-001 | P1 | fixed-candidate | `docs/demo` had no hard/chunk card audio, so public demo would rely on browser speech for 70 card terms. | Generated 70 card mp3 files under `docs/demo/audio/w/` and rebuilt `docs/demo`; closeout now has no audio warning. |
| W2-002 | P1 | fixed-candidate | `tts_generate.py --help` could crash because argparse treated `-20%` as a formatting placeholder. | Escaped `%` in help text and added a regression test. |
| W2-003 | P2 | fixed-candidate | New word timing sidecar behavior conflicted with old skip test and could force long mp3 re-synthesis. | Kept sidecars optional: existing non-empty mp3 files still skip; new generation writes sidecars when available. |
| W2-004 | P2 | fixed-candidate | Template had word timing runtime changes but `docs/demo` was stale. | Rebuilt `docs/demo` and added a template contract test for `__WORD_TIMINGS__` wiring. |
| W2-005 | P2 | accepted-residual | `@browser` MCP was locked by another automation profile. | Ran equivalent Playwright Chromium smoke: 22 segments, 1 study card, no audio gaps, no overflow, no page errors. |

## Verification

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
docs/demo build:
词典覆盖 100% (467/467)
no segment audio warning
no card audio warning
逐词同步数据: 22/22 段已生成
```

```text
dogfood build:
YouTube: only low lexicon coverage warning
OpenAI: only low lexicon coverage warning
Anthropic: only low lexicon coverage warning
```

```text
dogfood TTS skip:
YouTube failed=0
OpenAI failed=0
Anthropic failed=0
```

## Subagent Gates

| Gate | Result | Evidence |
|---|---|---|
| Archimedes I-1-I-13 audit | `AUDIT-FAIL` then fixed | Initial I-13 clean-copy browser gap exposed stale timing fixture behavior; fixed before final gate. |
| Arendt I-13 recheck | `AUDIT-PASS` | Re-ran unit and browser suites after timing fixture repair. |
| Noether stranger gate | `STRANGER-GATE clear` | Clean worktree at `a02a21e`, clean-copy quickstart, `63 passed`, `44 passed`, no public publish. |
| Russell final scope audit | `AUDIT-PASS I-1-I-13` | Current HEAD `e5a129b`, clean worktree, I-1 through I-13 evidence matrix clear, no P0/P1. |

## Boundary Checks

- No public publish command was run.
- `gh repo view rayw-lab/immersion-reader` returned repository-not-found on 2026-06-11, so the planned name remains available at this checkpoint.
- No third-party dogfood source text/audio is intentionally shipped in tracked release assets. The dogfood outputs stay local under ignored `lessons/`; an extra SoundHound study draft was removed from the tracked tree during cleanup.
- `lessons/` remains local-only and ignored.
- `docs/demo` uses the repository-owned demo lesson and tracked demo audio.

## Runtime Truth

- `docs/demo/index.html` reports `__AUDIO_STATUS__ = {"missing": [], "count": 22, "word_missing": [], "word_count": 70}`.
- Public demo audio inventory is 22 segment mp3 files and 70 card mp3 files.
- Dogfood local pages build without audio warnings; each keeps only the intended low-lexicon-coverage warning.
- Optional word timing data is wired through `window.__WORD_TIMINGS__`; the public demo now ships 22/22 segment timing sidecars and renders non-empty word timing data.

## Visual 5 Gate

- Existing browser verification refreshed 1280/720 screenshot artifacts under `artifacts/screenshots/`.
- `pytest tests/verify_browser.py tests/verify_ui_controls.py -q` passed with 44 browser/UI tests.
- No horizontal overflow was found in the Chromium smoke for `docs/demo`.

## Dynamic Build Gates

- Build closeout reports lexicon coverage.
- Build closeout reports segment audio gaps.
- Build closeout reports hard/chunk card audio gaps.
- Build closeout reports IPA style warnings without hard-failing arbitrary lessons.

## Docs Drift

- Current visual authority is recorded in the public-core design spec note.
- README and README.zh keep the public boundary: static compiler, no account/backend/database/cloud/local-agent bridge.
- Release candidate docs keep public publish commands under human review.

## Release Readiness

- `LICENSE` is MIT.
- `README.md` and `README.zh.md` have bilingual links, demo GIF, quickstart, skill install, privacy, and license sections.
- `docs/assets/demo.gif` and `docs/assets/social-preview.png` are present.
- `docs/release/awesome-agent-skills-entry.md` prepares the low-barrier listing entry.
- Human gate remains required before public repo creation, push, Pages activation, tag, or external PR.

## Closeout

SUPERAUDIT-CANDIDATE verdict=T-PASS-candidate
