# Real-Content Dogfood Report

state=wave2-shipped-candidate

Generated: 2026-06-11

## Boundary

The generated H5 lessons live under `lessons/`, which is ignored by git. This report records speed and quality only; it does not commit third-party article text, video transcript text, generated lesson HTML, or generated audio.

## Targets

| Lane | Source | Target | Local H5 | Result |
|---|---|---|---|---|
| OpenAI article | OpenAI official article | <https://openai.com/index/harness-engineering/> | `lessons/dogfood-openai-harness/index.html` | Built and opened |
| Claude article | Anthropic official engineering article | <https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents> | `lessons/dogfood-anthropic-harnesses/index.html` | Built and opened |
| YouTube video | YouTube target; transcript via YouTLDR | <https://www.youtube.com/watch?v=am_oeAoUhew> | `lessons/dogfood-youtube-harness/index.html` | Built and opened |

## Speed And Quality

| Lane | Words | Segments | Build Time | Browser Check | Quality Notes |
|---|---:|---:|---:|---|---|
| OpenAI article | 1960 | 12 | 0.264s | `file://` built; audio status `missing=[]`, `word_missing=[]` | Edge mp3 present: 12 segment files + 6 card-audio files; low lexicon coverage remains expected for unpolished dogfood |
| Claude article | 1826 | 11 | 0.124s | `file://` built; audio status `missing=[]`, `word_missing=[]` | Edge mp3 present: 11 segment files + 6 card-audio files; low lexicon coverage remains expected for unpolished dogfood |
| YouTube video | 2000 | 12 | 0.112s | `file://` built; audio status `missing=[]`, `word_missing=[]` | Edge mp3 present: 12 segment files + 6 card-audio files; transcript source is third-party |

## Build Closeout Samples

OpenAI:

```text
学习页: file://<repo>/lessons/dogfood-openai-harness/index.html
本课: 1960 词 · 难度 high · 约 3 天 · 主练: 盲听 + 原文精读 + agent 追问
建议第一步: 打开页面, 点 开始盲听
词典覆盖 2% (11/689)，划词未命中自动走问 agent
⚠ 词典覆盖低于 80%，缺 678 词，建议补 lexicon 后再交付
```

Claude:

```text
学习页: file://<repo>/lessons/dogfood-anthropic-harnesses/index.html
本课: 1826 词 · 难度 high · 约 3 天 · 主练: 盲听 + 原文精读 + agent 追问
建议第一步: 打开页面, 点 开始盲听
词典覆盖 2% (8/504)，划词未命中自动走问 agent
⚠ 词典覆盖低于 80%，缺 496 词，建议补 lexicon 后再交付
```

YouTube:

```text
学习页: file://<repo>/lessons/dogfood-youtube-harness/index.html
本课: 2000 词 · 难度 high · 约 3 天 · 主练: 盲听 + 原文精读 + agent 追问
建议第一步: 打开页面, 点 开始盲听
词典覆盖 3% (12/461)，划词未命中自动走问 agent
⚠ 词典覆盖低于 80%，缺 449 词，建议补 lexicon 后再交付
```

## Residuals

- These are dogfood lessons, not polished public examples. The low lexicon coverage warning proves I-6 fires for arbitrary source text.
- Edge audio generation now passes for all three dogfood lessons: segment audio and required card audio are present, and `__AUDIO_STATUS__` reports no missing files.
- YouTube direct subtitle retrieval via `yt-dlp` timed out in this environment. The video H5 used a third-party transcript page for local-only dogfood and must not be described as an official transcript.
- No generated dogfood lesson is committed. A publishable lesson needs rights review, full lexicon work, and audio generation.
