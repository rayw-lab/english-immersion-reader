from contextlib import contextmanager
import base64
import json
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOTS = ROOT / "artifacts" / "screenshots"
# derive the expected segment count from the lesson source so content growth
# never leaves these assertions silently pinned to an old demo
SEG_COUNT = len(json.loads((ROOT / "examples" / "demo" / "segments.json").read_text())["segments"])
# Keep duration metadata tests independent of ignored lessons/demo/audio artifacts.
SILENT_MP3_B64 = (
    "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjYyLjEyLjEwMAAAAAAAAAAAAAAA/+M4wAAAAAAAAAAAAEluZm8AAAAP"
    "AAAABQAAAkAAgICAgICAgICAgICAgICAgICAgKCgoKCgoKCgoKCgoKCgoKCgoKCgwMDAwMDAwMDAwMDAwMDAwMDA"
    "wMDg4ODg4ODg4ODg4ODg4ODg4ODg4P//////////////////////////AAAAAExhdmM2Mi4yOAAAAAAAAAAAAAAA"
    "ACQCwAAAAAAAAAJAvffvQQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/+MY"
    "xAAAAANIAAAAAExBTUUzLjEwMFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVMQU1FMy4xMDBVVVVVVVVV"
    "VVVV/+MYxDsAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
    "VVVVVVVVVVVV/+MYxHYAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
    "VVVVVVVVVVVVVVVVVVVV/+MYxLEAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
    "VVVVVVVVVVVVVVVVVVVVVVVV/+MYxMQAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
    "VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
)


def ensure_demo_audio(segment_id: str = "seg-01") -> None:
    audio_path = ROOT / "lessons" / "demo" / "audio" / f"{segment_id}.mp3"
    if audio_path.exists() and audio_path.stat().st_size > 0:
        return
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(base64.b64decode(SILENT_MP3_B64))


def sync_demo_audio_fixture() -> None:
    source_audio = ROOT / "docs" / "demo" / "audio"
    target_audio = ROOT / "lessons" / "demo" / "audio"
    target_audio.mkdir(parents=True, exist_ok=True)
    if source_audio.exists():
        shutil.copytree(source_audio, target_audio, dirs_exist_ok=True)
    else:
        ensure_demo_audio("seg-01")


def write_demo_word_timing_fixture() -> None:
    sync_demo_audio_fixture()
    data = json.loads((ROOT / "examples" / "demo" / "segments.json").read_text(encoding="utf-8"))
    words = []
    t = 0.0
    for raw in re.findall(r"[A-Za-z0-9']+", data["segments"][0]["en"]):
        duration = max(0.18, min(0.55, len(raw) * 0.045))
        words.append({"text": raw, "t0": round(t, 3), "t1": round(t + duration, 3)})
        t += duration + 0.08
    (ROOT / "lessons" / "demo" / "audio" / "seg-01.words.json").write_text(
        json.dumps(words),
        encoding="utf-8",
    )


def build_demo(with_word_timings: bool = False):
    if with_word_timings:
        write_demo_word_timing_fixture()
    else:
        sync_demo_audio_fixture()
    subprocess.run(
        [sys.executable, "src/build_page.py", "examples/demo/segments.json", "--out", "lessons/demo"],
        cwd=ROOT,
        check=True,
    )


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("localhost", 0))
        return int(sock.getsockname()[1])


@contextmanager
def demo_server():
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--directory", "lessons/demo"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(1)
        yield f"http://localhost:{port}/index.html"
    finally:
        server.terminate()
        server.wait(timeout=5)


def assert_no_horizontal_overflow(page):
    overflow = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 1, f"horizontal overflow: {overflow}px"


def screenshot(page, name: str):
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOTS / name), full_page=False)


def test_demo_page_at_640px_http():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 640, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            assert page.locator(".study-card").count() == 1
            assert page.locator(".seg").count() == SEG_COUNT
            assert_no_horizontal_overflow(page)
            screenshot(page, "task-8-http-default.png")

            page.get_by_text("开始盲听").click()
            page.wait_for_selector(".blind-grid")
            assert page.locator(".blind-chip").count() == SEG_COUNT
            assert page.locator(".blind-chip.current").count() == 1
            assert_no_horizontal_overflow(page)
            screenshot(page, "task-8-http-blind.png")

            page.get_by_text("揭文本").click()
            page.locator("#basketChip").evaluate("el => el.classList.remove('hidden')")
            assert_no_horizontal_overflow(page)
            browser.close()


def test_seg_icons_always_visible():
    # 2026-06-11 ray.w拍板: 五个段卡图标全部常显 (对齐 V1/V2), 无 hover 隐藏 / discovery 机制
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(url)
            page.wait_for_selector(".seg")
            assert page.locator(".seg.discover").count() == 0
            icons = page.locator('.seg[data-i="0"] .icbtn')
            assert icons.count() == 5
            opacities = icons.evaluate_all("els => els.map(el => getComputedStyle(el).opacity)")
            assert opacities == ["1"] * 5, opacities
            # hover 离开后依然常显
            page.locator('.seg[data-i="0"]').hover()
            page.locator(".hero").hover()
            page.wait_for_timeout(250)
            opacities = icons.evaluate_all("els => els.map(el => getComputedStyle(el).opacity)")
            assert opacities == ["1"] * 5, opacities
            screenshot(page, "task-10-icons-always-visible.png")
            browser.close()


def test_demo_page_file_url_renders_without_bridge():
    build_demo()
    url = (ROOT / "lessons" / "demo" / "index.html").resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 640, "height": 900})
        page.goto(url)
        page.wait_for_selector(".seg")
        assert page.locator(".study-card").count() == 1
        assert page.locator(".seg").count() == SEG_COUNT
        forbidden_host = ".".join(["127", "0", "0", "1"])
        assert forbidden_host not in page.content()
        assert_no_horizontal_overflow(page)
        screenshot(page, "task-8-file-default.png")
        browser.close()


def test_reset_clears_lesson_keys_but_keeps_preferences():
    build_demo()
    lesson_keys = ["ir_counts", "ir_out", "ir_transfer", "ir_week", "ir_last", "ir_basket", "ir_seen_terms", "ir_plays"]
    pref_keys = ["ir_rate", "ir_zh", "ir_fs"]
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 640, "height": 900})
            page.goto(url)
            page.evaluate(
                """([lessonKeys, prefKeys]) => {
                  lessonKeys.forEach(key => localStorage.setItem(key, JSON.stringify({x: 1})));
                  prefKeys.forEach(key => localStorage.setItem(key, "pref"));
                }""",
                [lesson_keys, pref_keys],
            )
            page.get_by_text("重置").click()
            page.wait_for_load_state("domcontentloaded")
            result = page.evaluate(
                """([lessonKeys, prefKeys]) => ({
                  lesson: lessonKeys.map(key => [key, localStorage.getItem(key)]),
                  prefs: prefKeys.map(key => [key, localStorage.getItem(key)])
                })""",
                [lesson_keys, pref_keys],
            )
            assert all(value is None for _, value in result["lesson"])
            assert all(value == "pref" for _, value in result["prefs"])
            browser.close()


def test_recording_is_memory_only_with_fake_microphone():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
            context = browser.new_context(viewport={"width": 640, "height": 900}, permissions=["microphone"])
            page = context.new_page()
            page.goto(url)
            page.wait_for_selector(".seg")
            page.locator('[data-record="0"]').click()
            page.wait_for_timeout(500)
            page.locator('[data-stop-record="0"]').click()
            page.wait_for_selector('[data-play-mine="0"]')
            assert page.locator('[data-play-mine="0"]').count() == 1
            screenshot(page, "task-8-recording.png")
            page.reload()
            page.wait_for_selector(".seg")
            assert page.locator('[data-play-mine="0"]').count() == 0
            browser.close()


def test_basket_chip_and_heat_strip_behaviors():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 640, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            page.locator('[data-confuse="0"]').click()
            page.wait_for_selector("#basketChip:not(.hidden)")
            assert page.locator('[data-confuse="0"]').inner_text() == "🤔"
            assert "1" in page.locator("#basketChip").inner_text()
            for _ in range(3):
                page.locator('[data-play="0"]').click()
            page.wait_for_selector(".heat-strip .heat-cell")
            assert page.locator(".heat-strip .heat-cell").count() == SEG_COUNT
            assert_no_horizontal_overflow(page)
            page.locator("#heatBlock").scroll_into_view_if_needed()
            screenshot(page, "task-8-basket-heat.png")
            browser.close()


def test_study_card_resume_and_suggest_branches():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 640, "height": 900})
            page.goto(url)
            page.evaluate(
                """() => {
                  localStorage.setItem('ir_last', JSON.stringify({id: 'seg-03', ts: Date.now()}));
                }"""
            )
            page.reload()
            page.wait_for_selector(".study-card")
            assert "继续 §3" in page.locator(".study-card").inner_text()

            page.evaluate(
                """() => {
                  const old = Date.now() - 3 * 24 * 60 * 60 * 1000;
                  localStorage.setItem('ir_last', JSON.stringify({id: 'seg-03', ts: old}));
                }"""
            )
            page.reload()
            page.wait_for_selector(".study-card")
            assert "隔了 3 天" in page.locator(".study-card").inner_text()

            page.evaluate(
                """() => {
                  localStorage.removeItem('ir_last');
                  localStorage.setItem('ir_basket', JSON.stringify([{type:'seg', id:'seg-01'}, {type:'seg', id:'seg-02'}, {type:'word', w:'reliable'}]));
                }"""
            )
            page.reload()
            page.wait_for_selector(".study-card")
            assert "攒了 3 条" in page.locator(".study-card").inner_text()

            page.evaluate(
                """() => {
                  localStorage.removeItem('ir_basket');
                  localStorage.setItem('ir_plays', JSON.stringify({'0': 3}));
                }"""
            )
            page.reload()
            page.wait_for_selector(".study-card")
            assert "回访 §1" in page.locator(".study-card").inner_text()
            screenshot(page, "task-10-study-card-suggest.png")
            browser.close()


def test_seen_terms_gold_border_after_click():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 640, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            page.locator('[data-term="reliable"]').first.click()
            seen = page.evaluate("() => JSON.parse(localStorage.getItem('ir_seen_terms')).reliable")
            assert isinstance(seen, int)
            assert "seen" in page.locator('[data-term="reliable"]').first.get_attribute("class")
            page.locator('[data-chunk="clear constraint"]').click()
            assert "seen" in page.locator('[data-chunk="clear constraint"]').get_attribute("class")
            screenshot(page, "task-10-seen-terms.png")
            browser.close()


def test_selection_popover_phrase_passage_and_cap():
    """划词复制 (S4 冗余通道): ≤5 词且 ≤40 字符走查词 prompt, 更长走整段精读
    prompt, 超过 120 词只提示不弹层。"""
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                permissions=["clipboard-read", "clipboard-write"],
            )
            page = context.new_page()
            page.goto(url)
            page.wait_for_selector(".seg")

            # --- phrase: first 3 words of §1 → word prompt ---
            selected = page.evaluate(
                """() => {
                  const en = document.querySelector('.seg[data-i="0"] .en');
                  const walker = document.createTreeWalker(en, NodeFilter.SHOW_TEXT);
                  let node = walker.nextNode();
                  const words = t => t.trim().split(/\\s+/).filter(Boolean).length;
                  while (node && words(node.textContent) < 3) node = walker.nextNode();
                  const m = node.textContent.match(/\\S+(?:\\s+\\S+){2}/);
                  const range = document.createRange();
                  range.setStart(node, m.index);
                  range.setEnd(node, m.index + m[0].length);
                  const sel = getSelection();
                  sel.removeAllRanges();
                  sel.addRange(range);
                  en.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                  return String(sel).trim();
                }"""
            )
            page.wait_for_selector(".term-popover", timeout=3000)
            ask = page.locator(".term-popover .pop-ask")
            assert "问你的 agent" in ask.inner_text()
            ask.click()
            clip = page.evaluate("() => navigator.clipboard.readText()")
            assert clip.startswith("请用中文解释这个英文表达"), clip
            assert selected in clip, (selected, clip)

            # --- passage: whole §1 en → 精读 prompt + 「已选 N 词 · M 字符」 ---
            page.evaluate(
                """() => {
                  const en = document.querySelector('.seg[data-i="0"] .en');
                  const range = document.createRange();
                  range.selectNodeContents(en);
                  const sel = getSelection();
                  sel.removeAllRanges();
                  sel.addRange(range);
                  en.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                }"""
            )
            page.wait_for_selector(".term-popover .pop-count", timeout=3000)
            head = page.locator(".term-popover .pop-count").inner_text()
            assert "已选" in head and "词" in head and "字符" in head, head
            ask = page.locator(".term-popover .pop-ask")
            assert "复制整段" in ask.inner_text()
            ask.click()
            clip = page.evaluate("() => navigator.clipboard.readText()")
            assert clip.startswith("请帮我精读这段英文"), clip
            screenshot(page, "task-selection-passage.png")

            # --- cap: >120 词只提示, 不弹浮层 ---
            page.evaluate(
                """() => {
                  document.querySelectorAll('.term-popover').forEach(el => el.remove());
                  const en = document.querySelector('.seg[data-i="1"] .en');
                  en.textContent = Array.from({length: 130}, (_, k) => 'word' + k).join(' ');
                  const range = document.createRange();
                  range.selectNodeContents(en);
                  const sel = getSelection();
                  sel.removeAllRanges();
                  sel.addRange(range);
                  en.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                }"""
            )
            page.wait_for_timeout(300)
            assert page.locator(".term-popover").count() == 0
            assert "最多支持 120 词" in page.locator("#toast").inner_text()
            browser.close()


def test_ab_button_states_and_no_audio_hint():
    """A-B 复读按钮: 默认 A·B 文案; 无 mp3 播放时点击只给提示不进入循环。"""
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            ab = page.locator("#abBtn")
            assert ab.count() == 1
            assert ab.inner_text() == "A·B"
            ab.click()
            assert "先播放一段 mp3" in page.locator("#toast").inner_text()
            assert "on" not in (ab.get_attribute("class") or "")
            browser.close()


def test_segment_read_button_prefers_slow_mp3_before_webspeech():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            page.evaluate(
                """() => {
                  window.__slowAudio = [];
                  window.__spoken = [];
                  window.Audio = function(src = "") {
                    return {
                      src,
                      playbackRate: 1,
                      onended: null,
                      onerror: null,
                      ontimeupdate: null,
                      play() {
                        window.__slowAudio.push({src, rate: this.playbackRate});
                        return Promise.resolve();
                      },
                      pause() {},
                      removeAttribute() {},
                      load() {}
                    };
                  };
                  speechSynthesis.cancel = () => {};
                  speechSynthesis.speak = u => { window.__spoken.push({text: u.text, rate: u.rate, lang: u.lang}); };
                }"""
            )
            page.locator('[data-read="0"]').click()
            page.wait_for_function("window.__slowAudio.length === 1")
            result = page.evaluate("() => ({slowAudio: window.__slowAudio, spoken: window.__spoken})")
            assert result["slowAudio"][0]["src"].endswith("audio/seg-01.mp3"), result
            assert result["slowAudio"][0]["rate"] == 0.8, result
            assert result["spoken"] == [], result
            browser.close()


def test_segment_read_button_fallback_speaks_once_when_audio_errors_twice():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            page.evaluate(
                """() => {
                  window.__spoken = [];
                  window.Audio = function(src = "") {
                    return {
                      src,
                      playbackRate: 1,
                      onended: null,
                      onerror: null,
                      ontimeupdate: null,
                      play() {
                        setTimeout(() => this.onerror && this.onerror(new Event("error")), 0);
                        return Promise.reject(new Error("missing"));
                      },
                      pause() {},
                      removeAttribute() {},
                      load() {}
                    };
                  };
                  speechSynthesis.cancel = () => {};
                  speechSynthesis.getVoices = () => [];
                  speechSynthesis.speak = u => { window.__spoken.push({text: u.text, rate: u.rate, lang: u.lang}); };
                }"""
            )
            page.locator('[data-read="0"]').click()
            page.wait_for_function("window.__spoken.length >= 1")
            page.wait_for_timeout(100)
            result = page.evaluate("() => window.__spoken")
            assert len(result) == 1, result
            assert result[0]["lang"] == "en-US"
            browser.close()


def test_segment_switch_has_single_audio_stream():
    """Regression: switching segments must not leave the old segment speaking via
    the speechSynthesis fallback while the new mp3 plays (double-voice bug)."""
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            page.evaluate(
                """() => {
                  window.__speakCalls = 0;
                  const origSpeak = speechSynthesis.speak.bind(speechSynthesis);
                  speechSynthesis.speak = u => { window.__speakCalls++; return origSpeak(u); };
                  window.__audios = [];
                  const OrigAudio = window.Audio;
                  window.Audio = function (src) {
                    const a = new OrigAudio(src);
                    window.__audios.push(a);
                    return a;
                  };
                }"""
            )
            plays = page.locator(".icbtn.primary-play")
            plays.nth(0).click()
            page.wait_for_timeout(800)
            plays.nth(1).click()
            page.wait_for_timeout(1200)
            state = page.evaluate(
                """() => ({
                  speakCalls: window.__speakCalls,
                  speaking: speechSynthesis.speaking || speechSynthesis.pending,
                  unpaused: window.__audios.filter(a => !a.paused).length,
                })"""
            )
            assert state["speakCalls"] == 0, f"speech fallback fired on switch: {state}"
            assert not state["speaking"], f"speechSynthesis still speaking: {state}"
            assert state["unpaused"] == 1, f"expected exactly one live audio: {state}"
            # pause toggle must also end fully silent
            page.click("#playBtn")
            page.wait_for_timeout(600)
            after = page.evaluate(
                """() => ({
                  speakCalls: window.__speakCalls,
                  speaking: speechSynthesis.speaking || speechSynthesis.pending,
                  unpaused: window.__audios.filter(a => !a.paused).length,
                })"""
            )
            assert after["speakCalls"] == 0 and not after["speaking"] and after["unpaused"] == 0, f"not silent after pause: {after}"
            browser.close()


def test_dictation_keyboard_enter_checks_escape_exits():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            page.locator('[data-dict="0"]').click()
            box = page.locator(".dict-input")
            box.fill("a quick")
            box.press("Shift+Enter")
            box.type("test line")
            assert box.input_value() == "a quick\ntest line"
            box.press("Enter")
            page.wait_for_selector(".dict-diff")
            page.locator(".dict-input").press("Escape")
            page.wait_for_selector(".dict-input", state="detached")
            assert page.locator('.seg[data-i="0"] .en').inner_text().strip() != ""
            browser.close()


def test_blind_chip_title_gains_duration_without_text_leak():
    ensure_demo_audio()
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            page.get_by_text("开始盲听").click()
            page.wait_for_selector(".blind-chip")
            page.wait_for_function(
                "document.querySelector('.blind-chip').title.includes('·')", timeout=15000
            )
            title = page.locator(".blind-chip").first.get_attribute("title")
            assert re.fullmatch(r"§1 · \d+:\d{2}", title), title
            assert "reliable" not in title.lower()  # 防文本泄露
            browser.close()


def test_copy_prompts_carry_lesson_title_context():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            title = page.evaluate("window.ImmersionReader.data.meta.title")
            page.locator('[data-confuse="0"]').click()
            prompts = page.evaluate(
                """() => {
                  const IR = window.ImmersionReader;
                  return [IR.askSegPrompt(0), IR.basketPrompt(), IR.transferPrompt()];
                }"""
            )
            for text in prompts:
                assert title in text, text[:120]
            browser.close()


def test_console_greets_developers():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            messages = []
            page.on("console", lambda m: messages.append(m.text))
            page.goto(url)
            page.wait_for_selector(".seg")
            assert any("window.ImmersionReader" in m for m in messages), messages
            browser.close()


def test_full_practice_completion_line():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            page.evaluate(
                """() => {
                  const IR = window.ImmersionReader;
                  IR.data.segments.forEach((_, i) => { IR.state.counts[i] = 3; });
                  IR.writeJSON(IR.KEYS.counts, IR.state.counts);
                }"""
            )
            page.reload()
            page.wait_for_selector("#recProgress:not(.hidden)")
            text = page.locator("#recProgress").inner_text()
            assert "可以写复述了" in text, text
            browser.close()


def _select_word(page, word, seg=0):
    """在 §1 正文单 text node 内选词并触发 mouseup（词必须避开 hard 词渲染节点）。"""
    found = page.evaluate(
        """([word, seg]) => {
          const en = document.querySelector(`.seg[data-i="${seg}"] .en`);
          const walker = document.createTreeWalker(en, NodeFilter.SHOW_TEXT);
          let node;
          while ((node = walker.nextNode())) {
            const idx = node.textContent.indexOf(word);
            if (idx >= 0) {
              const r = document.createRange();
              r.setStart(node, idx);
              r.setEnd(node, idx + word.length);
              const sel = getSelection();
              sel.removeAllRanges();
              sel.addRange(r);
              en.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
              return true;
            }
          }
          return false;
        }""",
        [word, seg],
    )
    assert found, word


def test_selection_lookup_hits_lexicon_and_marks_seen():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            _select_word(page, "trusted")  # lexicon: trusted -> lemma trust（已核对非 hard 词）
            page.wait_for_selector(".term-popover .pop-def")
            card = page.locator(".term-popover")
            assert card.locator(".pop-def").inner_text().strip() != ""
            assert card.locator(".pop-speak").count() == 1
            assert "trust" in card.locator(".pop-meta").inner_text()  # 词形还原行
            seen = page.evaluate("JSON.parse(localStorage.getItem('ir_seen_terms') || '{}')")
            assert "trusted" in seen  # 金边联动
            page.keyboard.press("Escape")
            page.wait_for_selector(".term-popover", state="detached")
            browser.close()


def test_hard_word_popover_merges_lexicon_ipa_without_losing_hard_def():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            page.locator('[data-term="interface"]').first.click()
            page.wait_for_selector(".term-popover .pop-def")
            card = page.locator(".term-popover")
            assert "人与系统交互" in card.locator(".pop-def").inner_text()
            assert card.locator(".pop-ipa").inner_text().strip() == "/ˈɪntərfeɪs/"
            browser.close()


def test_chunk_popover_splits_definition_and_example_layers():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            page.evaluate('document.querySelector(\'[data-chunk="clear constraint"]\').click()')
            page.wait_for_selector(".term-popover .pop-def")
            card = page.locator(".term-popover")
            assert card.locator(".pop-def").inner_text().strip() == "清晰约束"
            assert "This design note starts with a clear constraint." in card.locator(".pop-eg").inner_text()
            assert "例：" not in card.locator(".pop-def").inner_text()
            browser.close()


def test_popover_speak_prefers_word_audio_before_webspeech():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            page.evaluate(
                """() => {
                  window.__wordAudio = [];
                  window.__spoken = [];
                  window.Audio = function(src = "") {
                    return {
                      src,
                      onerror: null,
                      play() {
                        window.__wordAudio.push(src);
                        return Promise.resolve();
                      }
                    };
                  };
                  speechSynthesis.cancel = () => {};
                  speechSynthesis.speak = u => { window.__spoken.push({text: u.text, rate: u.rate, lang: u.lang}); };
                }"""
            )
            page.locator('[data-term="reliable"]').first.click()
            page.wait_for_selector(".term-popover .pop-speak")
            page.locator(".term-popover .pop-speak").click()
            page.wait_for_function("window.__wordAudio.length === 1")
            result = page.evaluate("() => ({wordAudio: window.__wordAudio, spoken: window.__spoken})")
            assert result["wordAudio"][0].endswith("audio/w/reliable.mp3"), result
            assert result["spoken"] == [], result
            browser.close()


def test_popover_speak_falls_back_to_tuned_webspeech_when_word_audio_missing():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            page.evaluate(
                """() => {
                  window.__wordAudio = [];
                  window.__spoken = [];
                  window.Audio = function(src = "") {
                    return {
                      src,
                      onerror: null,
                      play() {
                        window.__wordAudio.push(src);
                        return Promise.reject(new Error("missing"));
                      }
                    };
                  };
                  speechSynthesis.cancel = () => {};
                  speechSynthesis.getVoices = () => [];
                  speechSynthesis.speak = u => { window.__spoken.push({text: u.text, rate: u.rate, lang: u.lang}); };
                }"""
            )
            page.locator('[data-term="reliable"]').first.click()
            page.wait_for_selector(".term-popover .pop-speak")
            page.locator(".term-popover .pop-speak").click()
            page.wait_for_function("window.__spoken.length === 1")
            result = page.evaluate("() => ({wordAudio: window.__wordAudio, spoken: window.__spoken})")
            assert result["wordAudio"][0].endswith("audio/w/reliable.mp3"), result
            assert result["spoken"][0]["text"] == "reliable"
            assert result["spoken"][0]["lang"] == "en-US"
            assert abs(result["spoken"][0]["rate"] - 0.95) < 0.01
            browser.close()


def test_selection_miss_falls_back_to_agent_card():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            _select_word(page, "shows what is possible")  # 4 词短语：审计 C-3 修订，单 text node 内、零 hard 词
            page.wait_for_selector(".term-popover .pop-ask")
            assert page.locator(".term-popover .pop-def").count() == 0
            assert "agent" in page.locator(".term-popover .pop-ask").inner_text()
            browser.close()


def test_selected_phrase_stays_agent_card_even_when_chunk_exists():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            _select_word(page, "surface area", seg=2)
            page.wait_for_selector(".term-popover .pop-ask")
            card = page.locator(".term-popover")
            assert card.locator(".pop-def").count() == 0
            assert "划词" in card.locator(".pop-type").inner_text()
            assert "agent" in card.locator(".pop-ask").inner_text()
            browser.close()


def test_hit_word_ghost_button_stays_single_line_at_720px():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            page.locator("mark.hl").first.click()
            page.wait_for_selector(".term-popover .pop-ask.ghost-ask")
            metrics = page.locator(".term-popover .pop-ask.ghost-ask").evaluate(
                """el => {
                  const cs = getComputedStyle(el);
                  const height = el.getBoundingClientRect().height;
                  const contentHeight = height - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
                  return {
                    text: el.textContent,
                    contentHeight,
                    lineHeight: parseFloat(cs.lineHeight),
                    width: el.getBoundingClientRect().width
                  };
                }"""
            )
            assert metrics["text"] == "仍不懂？复制 → 问你的 agent"
            assert metrics["contentHeight"] <= metrics["lineHeight"] * 1.15, metrics
            screenshot(page, "task-i10-720-ghost-button.png")
            browser.close()


def test_player_rate_15_fits_at_720px():
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            assert page.locator(".rate").evaluate_all("els => els.map(el => el.dataset.rate)") == ["0.8", "1", "1.2", "1.5"]
            page.locator('.rate[data-rate="1.5"]').click()
            assert page.evaluate("window.ImmersionReader.state.rate") == 1.5
            assert page.evaluate("localStorage.getItem('ir_rate')") == "1.5"
            assert_no_horizontal_overflow(page)
            screenshot(page, "task-i11-720-player-rates.png")
            browser.close()


def test_karaoke_highlight_follows_playback_and_click_seeks():
    build_demo(with_word_timings=True)
    with demo_server() as url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(url)
            page.wait_for_selector(".seg")
            count = page.evaluate(
                "window.__WORD_TIMINGS__ ? Object.keys(window.__WORD_TIMINGS__).length : 0"
            )
            assert count > 0, "demo must ship word timings sidecar data"
            page.locator('[data-play="0"]').click()
            page.wait_for_function(
                "CSS.highlights && CSS.highlights.has('karaoke')", timeout=15000
            )
            # 点词跳播: 选一个不在 mark.hl 里的靠后词, 点它, 音频应跳到该词时间
            target = page.evaluate(
                """() => {
              const IR = window.ImmersionReader;
              const tm = window.__WORD_TIMINGS__[IR.data.segments[0].id];
              const en = document.querySelector('.seg[data-i="0"] .en');
              const playerTop = document.querySelector('.player').getBoundingClientRect().top;
              for (let k = 0; k < tm.length; k++) {
                const e = tm[k];
                const walker = document.createTreeWalker(en, NodeFilter.SHOW_TEXT);
                let pos = 0;
                let node;
                    while ((node = walker.nextNode())) {
                      const len = node.textContent.length;
                      if (e[2] < pos + len) {
                        if (node.parentElement.closest("mark.hl, button")) break;
                        const r = new Range();
                        r.setStart(node, e[2] - pos);
                    r.setEnd(node, Math.min(e[3] - pos, len));
                    const rect = r.getBoundingClientRect();
                    if (rect.width > 0 && e[0] > 2 && rect.bottom < playerTop - 12) {
                      return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2, t0: e[0] };
                    }
                        break;
                      }
                      pos += len;
                    }
                  }
                  return null;
                }"""
            )
            assert target, "no clickable plain-text word found in seg-01"
            page.mouse.click(target["x"], target["y"])
            page.wait_for_function(
                "window.ImmersionReader.state.audio && "
                f"window.ImmersionReader.state.audio.currentTime >= {target['t0'] - 0.2}",
                timeout=5000,
            )
            browser.close()
