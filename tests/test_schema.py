import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "src" / "segments.schema.json").read_text(encoding="utf-8"))


def load_demo():
    return json.loads((ROOT / "examples" / "demo" / "segments.json").read_text(encoding="utf-8"))


def test_demo_segments_validate_against_schema():
    jsonschema.validate(load_demo(), SCHEMA)


def test_zh_is_required_for_each_segment():
    data = load_demo()
    del data["segments"][0]["zh"]
    try:
        jsonschema.validate(data, SCHEMA)
    except jsonschema.ValidationError as exc:
        assert "zh" in str(exc)
    else:
        raise AssertionError("schema accepted a segment without zh")


def test_patterns_are_defined_and_validated():
    data = load_demo()
    data["patterns"][0]["t"] = ""
    try:
        jsonschema.validate(data, SCHEMA)
    except jsonschema.ValidationError as exc:
        assert "'' should be non-empty" in str(exc) or "is too short" in str(exc)
    else:
        raise AssertionError("schema accepted an empty pattern")


def test_transfer_task_genre_is_limited_to_workplace_pool():
    data = load_demo()
    data["transfer_tasks"][0]["genre"] = "essay"
    try:
        jsonschema.validate(data, SCHEMA)
    except jsonschema.ValidationError as exc:
        assert "essay" in str(exc)
    else:
        raise AssertionError("schema accepted an unsupported transfer task genre")


def test_transfer_task_requires_exactly_three_hint_chunks():
    data = load_demo()
    data["transfer_tasks"][0]["hint_chunks"] = ["clear constraint"]
    try:
        jsonschema.validate(data, SCHEMA)
    except jsonschema.ValidationError as exc:
        assert "too short" in str(exc) or "is too short" in str(exc)
    else:
        raise AssertionError("schema accepted fewer than three hint chunks")


def test_lexicon_is_optional_but_validated():
    data = load_demo()
    assert "lexicon" in data, "demo must ship a lexicon"
    jsonschema.validate(data, SCHEMA)
    legacy = load_demo()
    del legacy["lexicon"]
    jsonschema.validate(legacy, SCHEMA)  # 老课无 lexicon 仍合法


def test_lexicon_entry_needs_def_or_lemma():
    data = load_demo()
    data["lexicon"]["__bogus__"] = {"ipa": "/x/"}
    try:
        jsonschema.validate(data, SCHEMA)
    except jsonschema.ValidationError:
        pass
    else:
        raise AssertionError("schema accepted a lexicon entry without def or lemma")


def test_lexicon_ipa_format():
    data = load_demo()
    data["lexicon"]["__badipa__"] = {"def": "x", "ipa": "no-slashes"}
    try:
        jsonschema.validate(data, SCHEMA)
    except jsonschema.ValidationError:
        pass
    else:
        raise AssertionError("schema accepted ipa without /slashes/")


def test_meta_title_zh_is_optional_string():
    data = load_demo()
    assert data["meta"]["title_zh"]
    jsonschema.validate(data, SCHEMA)
    legacy = load_demo()
    del legacy["meta"]["title_zh"]
    jsonschema.validate(legacy, SCHEMA)  # 老课无中文标题仍合法
