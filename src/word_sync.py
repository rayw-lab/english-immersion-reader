"""Word-level audio sync: align Edge TTS WordBoundary events to display text.

WordBoundary events come from the synthesized `tts` text (numbers and
abbreviations expanded for speech); the page displays `en`. This module aligns
the two token streams and returns character ranges into `en` with start/end
times in seconds.

Discipline: a word that cannot be aligned confidently is dropped — a gap in
the karaoke highlight beats a wrong highlight. A segment whose overall match
ratio is too low returns no timings at all.
"""
import re

WORD_RE = re.compile(r"\S+")
MIN_MATCH_RATIO = 0.5
SYNC_LOOKAHEAD = 6


def normalize_token(token: str) -> str:
    text = str(token or "").lower().replace("’", "'")
    return re.sub(r"[^a-z0-9']+", "", text)


def en_tokens(text: str) -> list[dict]:
    tokens = []
    for match in WORD_RE.finditer(text or ""):
        tokens.append({
            "norm": normalize_token(match.group(0)),
            "c0": match.start(),
            "c1": match.end(),
        })
    return tokens


def tts_tokens(words: list[dict]) -> list[dict]:
    tokens = []
    for word in words or []:
        norm = normalize_token(str(word.get("text", "")))
        if not norm:
            continue
        tokens.append({
            "norm": norm,
            "t0": float(word.get("t0", 0.0)),
            "t1": float(word.get("t1", 0.0)),
        })
    return tokens


def _find_sync(en, tts, i, j):
    """Smallest (di, dj) within the lookahead window where tokens match again."""
    best = None
    for di in range(SYNC_LOOKAHEAD + 1):
        if i + di >= len(en):
            break
        for dj in range(SYNC_LOOKAHEAD + 1):
            if j + dj >= len(tts):
                break
            if en[i + di]["norm"] and en[i + di]["norm"] == tts[j + dj]["norm"]:
                if best is None or di + dj < best[0] + best[1]:
                    best = (di, dj)
                break
    return best


def _spread(en_slice, tts_slice, out):
    """Map m unmatched display tokens onto n unmatched speech words by even split."""
    if not en_slice or not tts_slice:
        return
    t0 = tts_slice[0]["t0"]
    t1 = tts_slice[-1]["t1"]
    if t1 <= t0:
        return
    step = (t1 - t0) / len(en_slice)
    for k, token in enumerate(en_slice):
        out.append({
            "t0": t0 + k * step,
            "t1": t0 + (k + 1) * step,
            "c0": token["c0"],
            "c1": token["c1"],
        })


def align_words(words: list[dict], en_text: str) -> list[dict]:
    """Align WordBoundary events to `en_text`.

    words: [{"text": str, "t0": seconds, "t1": seconds}, ...] in speech order.
    Returns [{"t0", "t1", "c0", "c1"}, ...] sorted by t0; empty when the
    alignment is not trustworthy.
    """
    en = en_tokens(en_text)
    tts = tts_tokens(words)
    meaningful = [token for token in en if token["norm"]]
    if not meaningful or not tts:
        return []

    out: list[dict] = []
    exact = 0
    i = 0
    j = 0
    while i < len(en) and j < len(tts):
        if not en[i]["norm"]:
            i += 1
            continue
        if en[i]["norm"] == tts[j]["norm"]:
            out.append({"t0": tts[j]["t0"], "t1": tts[j]["t1"], "c0": en[i]["c0"], "c1": en[i]["c1"]})
            exact += 1
            i += 1
            j += 1
            continue
        sync = _find_sync(en, tts, i, j)
        if sync is None:
            i += 1
            j += 1
            continue
        di, dj = sync
        if di == 0:
            # extra speech words (expansions already consumed); skip them
            j += dj
            continue
        _spread([t for t in en[i:i + di] if t["norm"]], tts[j:j + dj], out)
        i += di
        j += dj

    if exact / len(meaningful) < MIN_MATCH_RATIO:
        return []
    out.sort(key=lambda item: item["t0"])
    return out
