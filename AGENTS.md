# Immersion Reader Agent Instructions

You create `segments.json` files for static English deep-reading pages.

## Target Users (hard rule, 2026-06-11)

- The audience is laptop/desktop users who run a local agent (Claude Code, Codex, etc.) and open the generated pages in a desktop web browser.
- This is a GitHub-published skill for that audience only. There is NO mobile audience.
- Never design, reason, test, or ask questions in terms of phones, touch devices, `hover:none` media queries, or mobile viewports. All such thinking is out of scope.
- Desktop **half-screen split view IS a first-class scenario**: heavy agent users often tile two windows on one screen (agent terminal on the left, reading page on the right). Narrow-window layouts (~640-760px wide) must not overflow or truncate. Responsive breakpoints exist for desktop half-screen, not for phones.
- Acceptance viewports: full screen 1280px + half screen 720px. No phone viewports.
- UI affordances must be always visible (e.g. all five segment icons 常显). Do not hide controls behind hover/touch heuristics.

## Output Language

Rules are written in English. Learner-facing explanations, `zh`, `cn`, and closeout text are Chinese in v1.

## Required Data Rules

- Keep `segments.json` as the only lesson data authority.
- Segment length: aim for 60-100 English words per segment; split anything
  over 110 words at a natural semantic boundary. Long segments unbalance the
  side-by-side en/zh columns.
- `zh` is a condensed gist, not a sentence-by-sentence translation. Target
  zh character count ~= en word count x 2.0-2.5, consistent across segments.
- `meta.title_zh` is required: a natural Chinese translation of the title
  (rendered small under the English title).
- Segment granularity is paragraph/segment level, not sentence level.
- `zh` is required.
- `tts` must expand numbers and abbreviations for English speech.
- `chunks[].eg` must be a second-context example, not copied from the source segment.
- `chunks[].eg` must be a complete sentence, ideally no longer than 20 words.
- Try programmer work-context examples first. If unnatural, use the article domain.
- Work-context examples should reuse the transfer task genre pool (slack_message, pr_description, design_note, standup_update, code_review_comment) as their default settings.
- Generate one `transfer_tasks[]` item when the source naturally supports workplace output.
- Keep each Chinese line (`zh`, `cn`, study card text) within 20 characters per line of meaning; split long explanations.
- Use numbers for facts ("1280 词 · 22 段"), never stacked adjectives ("超长深度好文").
- Generate a `lexicon` object covering every content word in `segments[].en`
  (skip common function words). Inflected forms point to their lemma:
  `"starts": {"lemma": "start"}`; lemma entries carry a Chinese `def`
  (this lesson's sense only, <= 20 chars) and an American English `ipa`
  transcription wrapped in slashes, consistent across the lesson. Single-word
  `hard[]` entries must also exist in
  `lexicon` with `def` + `ipa` so hard cards can show pronunciation; multi-word
  hard phrases and `chunks[]` may rely on card audio instead of IPA. The page
  uses `lexicon` to answer text-selection lookups offline.
- For proper nouns and company/product names, keep the definition categorical
  and short (for example "company name; GPU vendor"). IPA may be omitted when
  a stable pronunciation is uncertain, but `def` must still make the reference
  useful offline.
- For long sources with more than 1000 content words, default to lexicon
  coverage for all content words; if the source is too large, cover the top 80%
  by frequency plus every single-word hard term. The build report must disclose
  the actual coverage and warn below 80%.
- Treat video or podcast transcripts the same as articles for `segments[]`,
  `hard[]`, `chunks[]`, `lexicon`, and audio. Use existing `spk` for speakers
  and `meta.kind` for source type; do not add new fields for transcript shape.

## Selection Card Policy

- User text selection is not the same surface as clicking a prepared `chunk`.
- A single-word selection may use `lexicon` offline and show a definition card.
- 2-5 word phrase selections stay agent cards by default. Do not build a
  per-word mini-definition list unless the product policy changes.
- Longer passage selections show the passage card and copy-out deep-reading
  prompt.
- Clicked chunks may still show their prepared `chunks[].cn` and `chunks[].eg`
  card, because those phrases were intentionally authored for the lesson.

## Tone

- No exclamation marks.
- No cheerleading phrases such as "加油", "恭喜", or "让我们".
- Study card value points are factual phrases, not motivational copy.

## Transfer Task Rule

Choose one natural workplace output genre from:

- slack_message
- pr_description
- design_note
- standup_update
- code_review_comment

Generate one task by default. The task must name three `chunks[].t` values through `hint_chunks`.

## Closeout

After running `src/build_page.py`, relay the script's Chinese closeout block verbatim. Do not invent a new summary.
