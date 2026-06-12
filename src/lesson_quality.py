import re

NON_AMERICAN_IPA_MARKERS = ("əʊ", "ɒ", "ː")
LEXICON_COVERAGE_WARN_THRESHOLD = 0.8
STOPWORDS = set(
    """a an the and or but if then than that this these those it its is are was were be been being am
    do does did done doing have has had having will would can could should may might must shall not no
    nor so to of in on at by for with from as about into over after before between out against during
    without within above below under again once because while until too very just more most much many
    some any each both few other another such only own same up down off he she they we you i his her
    their our your my me him them us who whom which what when where why how there here also all
    s t don ll re ve d m o y""".split()
)


def british_ipa_entries(data: dict) -> list[tuple[str, str]]:
    """Return lexicon entries whose IPA uses markers outside the American style gate."""
    flagged: list[tuple[str, str]] = []
    lexicon = data.get("lexicon") or {}
    if not isinstance(lexicon, dict):
        return flagged
    for term, entry in lexicon.items():
        if not isinstance(entry, dict):
            continue
        ipa = str(entry.get("ipa") or "")
        if ipa and any(marker in ipa for marker in NON_AMERICAN_IPA_MARKERS):
            flagged.append((str(term), ipa))
    return flagged


def content_words(data: dict) -> set[str]:
    words: set[str] = set()
    for segment in data.get("segments") or []:
        for token in re.findall(r"[a-z][a-z'-]*", str(segment.get("en") or "").lower()):
            if token not in STOPWORDS and len(token) > 2:
                words.add(token)
    return words


def phrase_terms(data: dict) -> list[str]:
    phrases: list[str] = []
    for segment in data.get("segments") or []:
        phrases.extend(str(item.get("w") or "").lower() for item in segment.get("hard") or [])
    phrases.extend(str(chunk.get("t") or "").lower() for chunk in data.get("chunks") or [])
    return [phrase for phrase in phrases if phrase]


def covered_by_phrase(word: str, data: dict) -> bool:
    return any(word in phrase.split() for phrase in phrase_terms(data))


def lexicon_resolves(word: str, lexicon: dict) -> bool:
    entry = lexicon.get(word)
    if not isinstance(entry, dict):
        return False
    if entry.get("def"):
        return True
    lemma = entry.get("lemma")
    target = lexicon.get(lemma or "")
    return bool(isinstance(target, dict) and target.get("def"))


def lexicon_coverage(data: dict) -> dict:
    lexicon = data.get("lexicon") or {}
    if not isinstance(lexicon, dict):
        lexicon = {}
    words = sorted(content_words(data))
    missing = [
        word for word in words
        if not lexicon_resolves(word, lexicon) and not covered_by_phrase(word, data)
    ]
    total = len(words)
    covered = total - len(missing)
    ratio = covered / total if total else 1.0
    return {
        "covered": covered,
        "total": total,
        "ratio": ratio,
        "missing": missing,
    }


def word_audio_slug(term: str) -> str:
    slug = str(term or "").strip().lower()
    slug = slug.replace("'", "").replace("’", "")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "term"


def required_word_audio_terms(data: dict) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for term in phrase_terms(data):
        slug = word_audio_slug(term)
        if slug in seen:
            continue
        seen.add(slug)
        out.append(term)
    return out
