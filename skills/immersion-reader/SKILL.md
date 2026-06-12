---
name: immersion-reader
description: Build a local H5 English deep-reading lesson from an article URL, YouTube transcript, podcast transcript, or prepared segments.json.
---

# Immersion Reader

## Setup (run once before first use)

1. Locate the repo root: this skill folder lives at `<repo>/skills/immersion-reader/`
   — resolve the real path of this file and go up two directories. If you only have
   the skill folder (no repo), clone it first:
   `git clone https://github.com/rayw-lab/english-immersion-reader`
2. Install the two Python dependencies (Python >= 3.10):
   `python3 -m pip install jsonschema edge-tts`
   (or, inside the repo: `python3 -m pip install -e .`)
3. `edge-tts` needs network access at synthesis time; the script manages proxy
   env vars itself, so no proxy setup is required.

Follow `AGENTS.md` in this repository.

## Compile flow

1. Write `lessons/<slug>/segments.json` per `AGENTS.md` (segments + hard +
   chunks + patterns + transfer task + full `lexicon`).
2. `python src/tts_generate.py lessons/<slug>/segments.json --out lessons/<slug>/audio`
   — one command produces segment mp3s, per-word audio for every lexicon term
   (default `--word-audio full`, so card/selection playback never falls back to
   browser TTS), and `.words.json` sidecars that power the karaoke word
   highlight. Needs network.
3. `python src/build_page.py lessons/<slug>/segments.json --out lessons/<slug>`
   — validates the contract, injects data + word timings, prints the Chinese
   closeout block. Relay that block verbatim; do not invent a summary.
4. Upgrading an older lesson: rerun step 2 (word audio fills in incrementally);
   add `--force` to regenerate segment mp3s so they gain timing sidecars.

Use this skill when the user asks for any of these:

- turn an English article URL into an immersion reading lesson
- turn a YouTube video or transcript into an English listening lesson
- build an H5/static HTML lesson with original English text
- create local audio, word cards, chunk cards, dictation, shadowing, or agent-copy prompts from source English

Default output stays local under `lessons/`; generated lessons and transcripts are not committed unless the user owns the rights and explicitly asks.
