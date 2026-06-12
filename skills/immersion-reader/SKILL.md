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

Use `src/build_page.py` to build the static page and `src/tts_generate.py` to generate Edge mp3 audio.

Use this skill when the user asks for any of these:

- turn an English article URL into an immersion reading lesson
- turn a YouTube video or transcript into an English listening lesson
- build an H5/static HTML lesson with original English text
- create local audio, word cards, chunk cards, dictation, shadowing, or agent-copy prompts from source English

Default output stays local under `lessons/`; generated lessons and transcripts are not committed unless the user owns the rights and explicitly asks.
