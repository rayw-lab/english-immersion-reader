import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "src" / "template" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "src" / "template" / "style.css").read_text(encoding="utf-8")
HTML = (ROOT / "src" / "template" / "index.html").read_text(encoding="utf-8")
DOCS_APP = (ROOT / "docs" / "demo" / "app.js").read_text(encoding="utf-8")
DOCS_CSS = (ROOT / "docs" / "demo" / "style.css").read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
README_ZH = (ROOT / "README.zh.md").read_text(encoding="utf-8")
CAPTURE = (ROOT / "artifacts" / "capture_states.py").read_text(encoding="utf-8")
SKILL = (ROOT / "skills" / "immersion-reader" / "SKILL.md").read_text(encoding="utf-8")
SPEC_PATH = ROOT.parents[1] / "docs" / "superpowers" / "specs" / "2026-06-10-immersion-reader-public-core-design.md"


def test_required_storage_keys_are_named():
    for key in [
        "ir_counts",
        "ir_out",
        "ir_transfer",
        "ir_week",
        "ir_last",
        "ir_basket",
        "ir_seen_terms",
        "ir_plays",
        "ir_rate",
        "ir_zh",
        "ir_fs",
    ]:
        assert key in APP


def test_template_has_favicon_and_color_scheme():
    assert 'rel="icon"' in HTML
    assert "data:image/svg+xml" in HTML
    assert 'name="color-scheme"' in HTML


def test_css_brands_text_selection():
    assert "::selection" in CSS


def test_word_timing_contract_is_wired_template_to_runtime():
    assert "window.__WORD_TIMINGS__" in HTML
    assert "{{WORD_TIMINGS_JSON}}" in HTML
    assert "const wordTimings = window.__WORD_TIMINGS__ || {}" in APP
    assert "CSS.highlights" in APP
    assert "::highlight(karaoke)" in CSS


def test_public_template_has_no_agent_bridge():
    forbidden = [
        "study" + "_bridge",
        ".".join(["127", "0", "0", "1"]),
        "Event" + "Source",
        "SS" + "E",
        "claude" + " -p",
        "codex" + " exec",
    ]
    for token in forbidden:
        assert token not in APP


def test_visual_contract_classes_exist():
    for selector in [".study-card", ".seg", ".seg-head", ".icbtn", ".train-slot", ".blind-grid", ".basket-chip", ".heat-strip"]:
        assert selector in CSS


def test_s1_to_s9_functions_exist():
    for token in [
        "function enterBlind",
        "function exitBlind",
        "function playSeg",
        "function askSegPrompt",
        "function askWordPrompt",
        "function basketPrompt",
        "function transferPrompt",
        "function retellPrompt",
        "function resetLesson",
        "function renderBlindGrid",
    ]:
        assert token in APP


def test_auto_play_does_not_update_last_or_plays_directly():
    assert "function playSeg(i, auto = false)" in APP
    assert "if (!auto)" in APP
    assert "writeLast(i)" in APP


def test_template_javascript_has_valid_syntax():
    result = subprocess.run(
        ["node", "--check", str(ROOT / "src" / "template" / "app.js")],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_blind_mode_replaces_zh_button_with_reveal_button():
    assert '$("#revealBtn").classList.remove("hidden")' in APP
    assert '$("#zhBtn").classList.add("hidden")' in APP
    assert '$("#revealBtn").classList.add("hidden")' in APP
    assert '$("#zhBtn").classList.remove("hidden")' in APP


def test_b1_to_b4_hooks_exist():
    for token in [
        "MediaRecorder",
        "URL.revokeObjectURL",
        "function startRecording",
        "function renderRecordingControls",
        "function enterDictation",
        "function diffWords",
        "ir_seen_terms",
        "ir_plays",
    ]:
        assert token in APP


def test_seg_head_icon_cap_is_documented_in_code():
    assert "seg-head icon cap: 5" in APP


def test_b4_heat_average_uses_all_segments():
    assert "data.segments.map((_, i) => Number(state.plays[i]) || 0)" in APP
    assert "vals.reduce((a, b) => a + b, 0) / vals.length" in APP


def test_dictation_icon_matches_spec_and_train_slot_avoids_player():
    assert 'data-dict="${i}">✍</button>' in APP
    assert ".train-slot:not(:empty)" in CSS
    assert "padding-bottom: 72px" in CSS


def test_icon_buttons_do_not_replace_icon_text_for_copy_feedback():
    assert 'button.classList.contains("icbtn")' in APP
    assert 'button.classList.add("copied")' in APP
    assert ".icbtn.copied" in CSS


def test_popover_visual_contract():
    for selector in [".pop-speak", ".pop-ipa", ".pop-eg", ".pop-meta", ".pop-seglink", ".ghost-ask"]:
        assert selector in CSS, selector
    # 定位逻辑改为左对齐选区，不再水平居中盖字（positionPopover:602 现含 rect.width / 2）
    assert "rect.width / 2" not in APP


def test_docs_demo_popover_template_is_in_sync():
    assert DOCS_APP == APP
    assert DOCS_CSS == CSS
    assert "pop-eg" in DOCS_APP
    assert ".pop-eg" in DOCS_CSS
    assert " — 例：" not in DOCS_APP


def test_agents_dynamic_content_robustness_rules():
    for token in [
        "proper nouns",
        "company/product names",
        "more than 1000 content words",
        "top 80%",
        "single-word hard",
        "video or podcast transcripts",
        "spk",
        "kind",
    ]:
        assert token in AGENTS


def test_selection_card_policy_is_documented_and_enforced():
    agents_lower = AGENTS.lower()
    for token in [
        "single-word",
        "2-5 word",
        "agent card",
        "passage selections",
        "clicked chunks",
    ]:
        assert token in agents_lower
    assert "Selection Card Policy" in README
    assert "2-5 word phrases stay agent cards" in README
    assert "划词卡策略" in README_ZH
    assert "2-5 词词组保持 agent 卡" in README_ZH
    assert "info.words === 1 ? lookupTerm" in APP
    assert "info.words <= 3 ? lookupTerm" not in APP


def test_capture_states_timing_contract():
    assert 'capture(720, "halfscreen"' in CAPTURE
    assert 'page.wait_for_timeout(250)' in CAPTURE
    assert "document.body.scrollHeight" in CAPTURE
    assert "scrollTo(0, 0)" in CAPTURE
    assert 'page.wait_for_selector(".recording-bar")' in CAPTURE
    state_13 = CAPTURE.index('shot(page, f"state-{tag}-13-selection-passage")')
    state_14 = CAPTURE.index('shot(page, f"state-{tag}-14-selection-phrase")')
    assert CAPTURE.rfind('page.wait_for_timeout(250)', 0, state_13) > CAPTURE.rfind('page.wait_for_selector(".term-popover")', 0, state_13)
    assert CAPTURE.rfind('page.wait_for_timeout(250)', 0, state_14) > CAPTURE.rfind('page.wait_for_selector(".term-popover")', 0, state_14)


def test_template_javascript_has_no_control_bytes():
    for rel in ["src/template/app.js", "docs/demo/app.js"]:
        data = (ROOT / rel).read_bytes()
        assert b"\x00" not in data
        assert b"\x01" not in data


def test_release_candidate_assets_and_docs_exist():
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")
    assert (ROOT / "docs" / "assets" / "demo.gif").stat().st_size > 10_000
    assert (ROOT / "docs" / "assets" / "social-preview.png").stat().st_size > 10_000
    for token in [
        "[English](README.md) | [简体中文](README.zh.md)",
        "docs/assets/demo.gif",
        "GitHub Pages",
        "Skill Install",
        "lessons/",
        "MIT",
    ]:
        assert token in README
    for token in [
        "[English](README.md) | [简体中文](README.zh.md)",
        "docs/assets/demo.gif",
        "Skill 安装",
        "lessons/",
        "MIT",
    ]:
        assert token in README_ZH
    release = (ROOT / "docs" / "release" / "wave2-publish-candidate.md").read_text(encoding="utf-8")
    assert "state=wave2-shipped-candidate" in release
    assert "Do not run these commands before human review" in release
    assert "gh repo create rayw-lab/immersion-reader --public" in release
    assert "HN Show HN and V2EX are human-review channels" in release
    awesome = (ROOT / "docs" / "release" / "awesome-agent-skills-entry.md").read_text(encoding="utf-8")
    assert "VoltAgent/awesome-agent-skills" in awesome
    assert "https://github.com/rayw-lab/immersion-reader/tree/main/skills/immersion-reader" in awesome
    dogfood = (ROOT / "docs" / "release" / "dogfood-real-content-report.md").read_text(encoding="utf-8")
    assert "lessons/dogfood-openai-harness/index.html" in dogfood
    assert "lessons/dogfood-anthropic-harnesses/index.html" in dogfood
    assert "lessons/dogfood-youtube-harness/index.html" in dogfood
    assert "third-party transcript" in dogfood
    assert "must not be described as an official transcript" in dogfood


def test_skill_frontmatter_and_trigger_terms_are_release_ready():
    lines = SKILL.splitlines()
    assert lines[0] == "---"
    end = lines.index("---", 1)
    frontmatter = lines[1:end]
    meta = dict(line.split(": ", 1) for line in frontmatter)
    assert len(meta["name"]) <= 64
    assert len(meta["description"]) <= 200
    for token in [
        "article URL",
        "YouTube",
        "transcript",
        "H5/static HTML",
        "original English text",
        "lessons/",
    ]:
        assert token in SKILL


def test_spec_acceptance_notes_current_visual_authority():
    if not SPEC_PATH.exists():
        return
    spec = SPEC_PATH.read_text(encoding="utf-8")
    assert "2026-06-11 当前验收注记" in spec
    assert "五个图标全部常显" in spec
    assert "1280px + 720px" in spec
