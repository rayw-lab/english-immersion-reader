"""每个正文实词必须能解出释义：lexicon 直查 / lemma 跳转 / hard / chunks 四选一。"""
import json
import re
from pathlib import Path

from lesson_quality import british_ipa_entries, lexicon_coverage

ROOT = Path(__file__).resolve().parents[1]

def load_demo():
    return json.loads((ROOT / "examples" / "demo" / "segments.json").read_text(encoding="utf-8"))


def resolves_with_ipa(word, lex):
    entry = lex.get(word)
    if not entry:
        return False
    if entry.get("def") and entry.get("ipa"):
        return True
    lemma = entry.get("lemma")
    target = lex.get(lemma or "", {})
    return bool(target.get("def") and target.get("ipa"))


def test_every_content_word_resolves():
    data = load_demo()
    missing = lexicon_coverage(data)["missing"]
    assert not missing, f"lexicon missing {len(missing)} words: {missing[:25]}"


def test_single_word_hard_terms_resolve_with_ipa():
    data = load_demo()
    lex = data.get("lexicon", {})
    hard_terms = sorted({
        h["w"].lower()
        for seg in data["segments"]
        for h in seg["hard"]
        if re.fullmatch(r"[a-z][a-z'-]*", h["w"].lower())
    })
    missing = [
        term for term in hard_terms
        if not (lex.get(term, {}).get("def") and lex.get(term, {}).get("ipa"))
    ]
    assert not missing, f"single-word hard terms missing lexicon ipa: {missing}"


def test_demo_ipa_uses_american_style():
    data = load_demo()
    flagged = british_ipa_entries(data)
    assert not flagged, f"British IPA markers found: {flagged[:20]}"
