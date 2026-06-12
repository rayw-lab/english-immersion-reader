from word_sync import align_words, en_tokens, normalize_token


def w(text, t0, t1):
    return {"text": text, "t0": t0, "t1": t1}


def test_perfect_alignment_maps_every_word():
    en = "A reliable AI feature."
    words = [w("A", 0.0, 0.2), w("reliable", 0.2, 0.7), w("AI", 0.7, 1.0), w("feature", 1.0, 1.5)]
    aligned = align_words(words, en)
    assert len(aligned) == 4
    assert aligned[0]["c0"] == 0 and en[aligned[1]["c0"]:aligned[1]["c1"]] == "reliable"
    assert en[aligned[3]["c0"]:aligned[3]["c1"]] == "feature."


def test_expanded_abbreviation_collapses_onto_display_token():
    en = "An AI layer watches."
    # tts said "An A I layer watches" — AI expanded into two speech words
    words = [w("An", 0.0, 0.2), w("A", 0.2, 0.4), w("I", 0.4, 0.6), w("layer", 0.6, 1.0), w("watches", 1.0, 1.4)]
    aligned = align_words(words, en)
    spans = [en[a["c0"]:a["c1"]] for a in aligned]
    assert "AI" in spans
    ai = aligned[spans.index("AI")]
    assert ai["t0"] == 0.2 and ai["t1"] == 0.6


def test_number_expansion_spreads_time():
    en = "Bezos founded Amazon in 1994 quietly."
    words = [
        w("Bezos", 0.0, 0.5), w("founded", 0.5, 1.0), w("Amazon", 1.0, 1.5), w("in", 1.5, 1.7),
        w("nineteen", 1.7, 2.1), w("ninety", 2.1, 2.5), w("four", 2.5, 2.9), w("quietly", 2.9, 3.4),
    ]
    aligned = align_words(words, en)
    spans = {en[a["c0"]:a["c1"]]: a for a in aligned}
    assert "1994" in spans
    assert spans["1994"]["t0"] == 1.7 and spans["1994"]["t1"] == 2.9
    assert spans["quietly."]["t0"] == 2.9


def test_hopeless_alignment_returns_empty():
    en = "Completely different sentence here."
    words = [w("nothing", 0.0, 0.4), w("matches", 0.4, 0.8), w("at", 0.8, 1.0), w("all", 1.0, 1.2)]
    assert align_words(words, en) == []


def test_punctuation_only_tokens_are_skipped():
    en = "Day one — always."
    words = [w("Day", 0.0, 0.3), w("one", 0.3, 0.6), w("always", 0.6, 1.0)]
    aligned = align_words(words, en)
    spans = [en[a["c0"]:a["c1"]] for a in aligned]
    assert "—" not in spans
    assert "always." in spans


def test_normalize_and_tokenize_helpers():
    assert normalize_token("It’s") == "it's"
    assert normalize_token("—") == ""
    tokens = en_tokens("Hello world")
    assert tokens[1]["c0"] == 6 and tokens[1]["c1"] == 11
