# Immersion Reader V3 Polish Superaudit

审计日期: 2026-06-11  
角色: Independent Architecture Council / superaudit subagent  
仓库: `<repo>`  
范围: `git log 2237d3c..HEAD`  
初始 HEAD: `edc77e1 chore: refresh state screenshots after v3 polish`  
审计修复后 HEAD: `a8b37f9 fix(superaudit): correct present lexicon ipa`  
工作树状态: clean before report; report written before Task 14 Step 4 commit

## Executive Verdict

verdict: `fixed-clear`

本轮实现可以进入ray.w人审。没有发现 P0。发现 1 个 P1: demo lexicon 中 `present` 在原文语境是动词, 但 IPA 写成名词/形容词重音。已修复并提交 `a8b37f9 fix(superaudit): correct present lexicon ipa`, 同步重建 `docs/demo/index.html`, 修后 `pytest -q` 为 `36 passed`。

发布门结论: 代码与静态交付物达到 T-PASS / R-PASS; 审美门仍按计划交给ray.w做 V-PASS 走查, 不在本报告里替代人工审美拍板。

Top evidence:

- 权威优先级: `AGENTS.md:7-12` 明确目标是桌面用户、1280 + 720 验收、五个段级图标常显; 这压过 spec §11 旧的 hover/640 文字。
- 实装范围: `git log 2237d3c..HEAD` 覆盖 Task 1-14 以及本次 `fix(superaudit)` 修复; 改动集中于模板三件套、schema、demo lexicon、browser/UI 测试、docs/demo 和截图。
- 全量验证: `pytest -q` -> `36 passed`; browser/UI 收集 34 个测试, 无 `skip` / `xfail`。
- file:// 回归: Playwright 直开 `file://<repo>/lessons/demo/index.html`, 断言 `.seg` = 22、`.study-card` = 1。
- 边界扫描: 未命中 `Qwen3` / `whisper` / `study_bridge` / `127.0.0.1` / `EventSource` / `SSE` / `fetch(` / 在线词典 / 跨课存储。

## P0-P2 Register

| ID | Sev | Status | Finding | Evidence | Action |
|---|---:|---|---|---|---|
| P1-001 | P1 | fixed | `present` lexicon IPA 用了名词/形容词重音; 原文是动词 `present three candidate answers` | 原文语境在 `examples/demo/segments.json` §7; Merriam-Webster verb pronunciation is `pri-ˈzent`; local fixed line `examples/demo/segments.json:1717-1720` | Changed `/ˈprɛzənt/` -> `/prɪˈzent/`; rebuilt `docs/demo/index.html`; committed `a8b37f9`; full tests green |
| P2-001 | P2 | registered | spec §11 旧验收仍写 hover 可发现 / 640px, 与 2026-06-11 拍板的常显图标 / 1280+720 有历史差异 | `public-core-design.md:947-955`; override in `AGENTS.md:7-12` and plan priority `v3-polish.md:101-102` | Per PRIORITY RULE: do not reverse-fix; leave for doc cascade cleanup |
| P2-002 | P2 | registered | 截图证据制品有时序弱点: `state-*-13-selection-passage.png` 在 `pop-in .18s` 动画刚开始时截图, 浮层过淡; `state-*-02-fullpage.png` 因进入态/IO 导致全页下半大面积空白; `state-*-05-recording-bar.png` 画面未清楚展示 recording bar | Visual review of 30 required screenshots; Playwright measured immediate popover opacity `0.083`, after 250ms opacity `1` and no player overlap | Product runtime not blocked; leave for screenshot script hardening |
| P2-003 | P2 | registered | `src/template/app.js` 继承了 NUL/SOH 占位符字节, normal `rg` treats file as binary; audit must use `rg -a` | `src/template/app.js:241-264`; baseline `2237d3c` already had 1 NUL + 1 SOH | Not introduced in this range; leave as tooling hygiene cleanup |

## Dimension 1: Spec 合规

verdict: `clear-with-P2-doc-drift`

- Q1 首屏: S1 学习卡不是 dashboard, 无图表/环形进度/百分比; screenshots `state-desktop-01-default.png` and `state-halfscreen-01-default.png` show first segment visible below S1. Spec basis: `public-core-design.md:619-630`.
- Q2 段卡主轴: default state keeps English as high-contrast reading axis; training states live in `.train-slot` and are exit-able. Code: `src/template/app.js:216-235`, `src/template/app.js:926-978`.
- Q3 icons: five segment icons are always visible by priority rule. Code: `src/template/app.js:224-230`; test: `tests/verify_browser.py:108-128`.
- Q4 blind: content hidden, hero + blind grid + bottom player retained; durations only in `title`, no text leak. Code: `src/template/app.js:1034-1075`; screenshots `state-*-11-blind.png`.
- Q5 bottom review: basket / heat / week are page-tail blocks, not mid-reading banners. Test coverage: `tests/verify_browser.py:200-218`, `tests/verify_ui_controls.py:136-154`, `tests/verify_ui_controls.py:206-233`.
- Q6 Chinese: zh is lower weight and can hide; blind hides text. Code paths: `#zhBtn` binding `src/template/app.js:1332-1335`; tests `tests/verify_ui_controls.py:25-36`.
- Q7 quiet feedback: diff colors use static red/green; no score/verdict. Code: `src/template/app.js:981-1008`; CSS variables `--diff-add`/`--diff-del` in `src/template/style.css:28-30`.
- Q8 halfscreen: screenshots are 720px halfscreen; browser tests also keep a legacy 640 lower-bound smoke. Per priority, 720 is acceptance, 640 remains only a regression floor.
- Architecture boundary: no backend/database/account/cloud/CLI bridge/SSE/cross-course storage. Spec basis `public-core-design.md:919-943`; scan found no forbidden runtime tokens.

## Dimension 2: 计划一致

verdict: `clear`

Task evidence:

- Task 0 ROADMAP: parent doc has P1 `V-PASS 未过`, P2.5 `进行中`; no "V-PASS 已过" claim.
- Task 1 capture: `artifacts/capture_states.py` now generates desktop + halfscreen 14-state set; required screenshot count = 30 including two task-11 card shots.
- Task 2 dictation keyboard: Enter checks, Shift+Enter remains newline, Esc exits. Code `src/template/app.js:926-952`; test `tests/verify_browser.py:444-462`.
- Task 3 blind duration: code `src/template/app.js:1013-1075`; test `tests/verify_browser.py::test_blind_chip_title_gains_duration_without_text_leak`.
- Task 4 favicon / color-scheme / selection: schema and template tests cover `rel="icon"`, color-scheme meta, and `::selection`.
- Task 5/6/7 prompts, console, completion line: code `lessonHeader`, `window.ImmersionReader`, and `updateRecProgress`; tests in `verify_browser.py`.
- Task 8/9 lexicon: schema lines `src/segments.schema.json:126-140`, AGENTS rules `AGENTS.md:31-36`, coverage test `tests/test_lexicon_coverage.py:48-55`.
- Task 10/11 selection card behavior/visual: lookup chain `src/template/app.js:596-637`, card builder `src/template/app.js:654-685`, selection split `src/template/app.js:717-740`, tests `tests/verify_browser.py:569-602`.
- Task 12 control net: `tests/verify_ui_controls.py` covers topbar, player, A-B, read, hard/chunk popovers, popover speak/jump, basket, output copy, dictation buttons, recording controls, heat cell, week day, blind reveal; pageerror guard in `tests/verify_ui_controls.py:9-22`.
- Task 13 docs/demo: README demo entry at `README.md:23-27` / `README.zh.md:23-27`; `docs/demo/` includes built HTML, app/style, and 22 mp3 files.
- Task 14: full validation and screenshot refresh done before this audit; this audit added one P1 fix commit and reran validation.

## Dimension 3: 视觉 5 Gate

verdict: `clear-with-P2-artifact-gaps`

Reviewed artifacts:

- 28 state screenshots: `state-desktop-01..14`, `state-halfscreen-01..14`.
- 2 lexicon card screenshots: `task-11-lexicon-card-desktop.png`, `task-11-lexicon-card-halfscreen.png`.

Gate assessment:

- 层级: default and halfscreen views prioritize H1 -> S1 card -> reading text -> low-weight zh. Lexicon card hierarchy follows word / badge / speak / IPA / def / meta / ghost ask.
- 对齐: cards stay on common left/right rails; halfscreen wraps S1 bullets without truncation; blind grid flex-wrap is stable.
- 遮挡: runtime popover does not overlap fixed player after animation; measured halfscreen passage popover bottom `803px`, player top `835px`.
- 可读: English text remains the highest contrast; zh is secondary; controls are icon-sized but visible. Small hints use existing low-contrast tokens, not blocking.
- 重量: copy buttons and blue primary buttons are high weight only at actions; lexicon definition is visually stronger than meta.

P2 artifact caveat:

- `state-*-13-selection-passage.png` was captured immediately after `.term-popover` appears; animation opacity was measured at about `0.083`. After 250ms it is fully opaque. Product behavior is fine; screenshot evidence is weak.
- `state-*-02-fullpage.png` full-page screenshots show lower-page blank space because entrance animation/IntersectionObserver does not reveal offscreen segments during capture.
- `state-*-05-recording-bar.png` does not clearly show the recording bar, while `state-*-06-recording-controls.png` does show post-record controls.

## Dimension 4: fake-green 排查

verdict: `clear`

Commands and outcomes:

- Baseline full run: `. .venv/bin/activate && pytest -q` -> `36 passed`.
- Browser/UI collect: `pytest tests/verify_browser.py tests/verify_ui_controls.py --collect-only -q` -> 34 browser/UI tests collected.
- Skip scan: `rg -n "skip|xfail|pytest\\.mark\\.skip|pytest\\.mark\\.xfail" tests/verify_browser.py tests/verify_ui_controls.py` -> no output.

Five assertion-mutation red checks:

| Test | Temporary mutation | Result |
|---|---|---|
| `test_seg_icons_always_visible` | expected icon count `6` instead of `5` | failed |
| `test_selection_lookup_hits_lexicon_and_marks_seen` | expected `distrust` instead of `trust` in lemma meta | failed |
| `test_player_rate_buttons_persist` | expected `ir_rate == "1.2"` after clicking `0.8` | failed |
| `test_week_day_cell_toggles_progress_state` | expected `[1]` instead of `[0]` | failed |
| `test_every_content_word_resolves` | inverted missing assertion | failed |

After reverting temporary mutations, the same five tests returned `5 passed`; full run returned `36 passed`.

## Dimension 5: 边界

verdict: `clear`

Production boundary scan:

```text
rg -a -n "Qwen3|whisper|study_bridge|127\.0\.0\.1|EventSource|\bSSE\b|在线词典|dictionary API|fetch\(|XMLHttpRequest|indexedDB|ir_profile|cross[- ]lesson|跨课" README.md README.zh.md AGENTS.md skills src examples docs tests artifacts/capture_states.py
```

Result: no output.

Benign related findings:

- README quickstart uses `python3 -m http.server` and `http://localhost:8770/index.html`, which is a static file server path, not a product backend.
- Tests and capture script use local `http.server` for browser automation only.
- `localStorage` keys are lesson-local (`ir_counts`, `ir_out`, `ir_transfer`, `ir_week`, `ir_last`, `ir_basket`, `ir_seen_terms`, `ir_plays`) plus preferences (`ir_rate`, `ir_zh`, `ir_fs`); reset removes lesson keys and preserves preferences per spec.

## Dimension 6: lexicon 质量

verdict: `fixed-clear`

Quantitative checks:

```text
content_words 467
lexicon entries 447
lemma refs 119
missing 0
dangling 0
bad_ipa 0
rough_extras 0
```

Random sample seed: `20260611`

Sampled entries:

`weakness, output, shows, signal, find, language, nature, unexpected, organizational, take, widest, present, exactly, coin, project, question, data, accumulate, almost, attention, lets, train, actual, suggest, every, means, learning, treat, new, fix`

Manual judgment:

- Chinese defs in the sample match local article sense; examples: `organizational` -> `组织层面的`, `take` -> `花费;需要`, `means` -> lemma `mean`.
- Lemma chain is closed; no dangling lemma refs.
- P1 fixed: `present` in §7 is verb. Merriam-Webster lists verb pronunciation as `pri-ˈzent` while noun/adjective use `ˈpre-zᵊnt`; local entry now reads `examples/demo/segments.json:1717-1720` as `/prɪˈzent/`. Source: [Merriam-Webster present](https://www.merriam-webster.com/dictionary/present).

Residual note:

- IPA style is broadly American and not perfectly narrow IPA (`/trit/` vs `/triːt/`, `/nu/` vs `/nuː/` style choices exist). This is not blocking under current schema because it only requires slash-wrapped IPA and no pronunciation scoring.

## Dimension 7: 回归

verdict: `clear`

Commands:

```bash
. .venv/bin/activate && pytest -q
```

Output: `36 passed`.

file:// smoke:

```text
file://<repo>/lessons/demo/index.html
{'seg_count': 22, 'study_card': 1, 'title': 'Why Reliable AI Features Need Small Interfaces'}
```

Browser/UI test inventory:

- `tests/verify_browser.py`: 18 tests.
- `tests/verify_ui_controls.py`: 16 tests.
- Total browser/UI collected: 34.
- No `skip` / `xfail`.

## Dimension 8: 文档级联

verdict: `clear-with-P2-spec-drift`

README:

- English README states static compiler, no account/backend/database/cloud/local-agent CLI bridge/in-page server at `README.md:5-21`.
- Chinese README mirrors public boundary at `README.zh.md:5-21`.
- Both expose docs/demo first-run path at `README.md:23-27` and `README.zh.md:23-27`.

AGENTS:

- Target audience and viewport rule are current at `AGENTS.md:7-12`.
- Lexicon generation rules are current at `AGENTS.md:31-36`.

SKILL:

- Skill remains a pointer, not duplicate process text, at `skills/immersion-reader/SKILL.md:6-10`.

Spec drift:

- `public-core-design.md:947-955` still contains old hover/640 acceptance wording. Per explicit PRIORITY RULE, this is P2 doc drift only and must not trigger reverse fixes.

## Scorecard

| Dimension | Score | Notes |
|---|---:|---|
| Spec 合规 | 92 | Current AGENTS/priority resolves old spec wording; P2 doc drift remains |
| 计划一致 | 94 | Tasks map to code/tests/docs; Task 0 is parent ROADMAP and outside repo commits |
| 视觉 5 Gate | 86 | Product visuals clear; screenshot evidence has P2 timing/fullpage gaps |
| fake-green | 96 | 5/5 mutation checks red; no browser skip/xfail |
| 边界 | 97 | Forbidden runtime tokens absent; static server mentions are benign |
| lexicon 质量 | 90 | P1 fixed; remaining IPA style is schema-level acceptable |
| 回归 | 97 | `36 passed`; file:// smoke clear |
| 文档级联 | 92 | README/AGENTS/SKILL aligned; old spec §11 drift remains |

Overall: 93/100

## Closeout

Fixed commit:

```text
a8b37f9 fix(superaudit): correct present lexicon ipa
```

Fresh verification:

```text
pytest -q -> 36 passed
browser/UI collect -> 34 tests, no skip/xfail
file:// smoke -> 22 segments + 1 study card rendered
git status --short --branch -> ## main
```

SUPERAUDIT-DONE verdict=fixed-clear
