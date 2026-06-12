"""全控件交互测试：每个可点控件至少一次点击 + 状态断言 + 零 pageerror。"""
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

from verify_browser import build_demo, demo_server  # 复用既有 helper


@contextmanager
def ui_page(url, p, launch_args=None, **ctx_kwargs):
    browser = p.chromium.launch(args=launch_args or [])
    context = browser.new_context(viewport={"width": 720, "height": 900}, **ctx_kwargs)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url)
    page.wait_for_selector(".seg")
    try:
        yield page, errors
    finally:
        assert errors == [], errors
        browser.close()


def test_topbar_zh_toggle_persists():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p) as (page, _):
            page.locator("#zhBtn").click()
            assert page.evaluate("document.body.classList.contains('hide-zh')")
            assert page.evaluate("localStorage.getItem('ir_zh')") is not None
            page.reload()
            page.wait_for_selector(".seg")
            assert page.evaluate("document.body.classList.contains('hide-zh')")
            page.locator("#zhBtn").click()
            assert not page.evaluate("document.body.classList.contains('hide-zh')")


def test_topbar_font_size_buttons_persist():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p) as (page, _):
            before = page.evaluate(
                "parseFloat(getComputedStyle(document.querySelector('.en')).fontSize)"
            )
            page.locator("#fsUp").click()
            after = page.evaluate(
                "parseFloat(getComputedStyle(document.querySelector('.en')).fontSize)"
            )
            assert after > before
            assert page.evaluate("localStorage.getItem('ir_fs')") is not None
            page.locator("#fsDown").click()
            restored = page.evaluate(
                "parseFloat(getComputedStyle(document.querySelector('.en')).fontSize)"
            )
            assert abs(restored - before) < 0.5


def test_player_rate_buttons_persist():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p) as (page, _):
            assert page.locator(".rate").count() == 4
            page.locator('.rate[data-rate="0.8"]').click()
            assert page.evaluate("window.ImmersionReader.state.rate") == 0.8
            assert page.evaluate("localStorage.getItem('ir_rate')") == "0.8"
            page.locator('.rate[data-rate="1.5"]').click()
            assert page.evaluate("window.ImmersionReader.state.rate") == 1.5
            assert page.evaluate("localStorage.getItem('ir_rate')") == "1.5"


def test_player_prev_next_updates_now_playing():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p) as (page, _):
            page.locator('[data-play="0"]').click()
            page.wait_for_function("document.getElementById('pNow1').textContent.includes('01')")
            page.locator("#nextBtn").click()
            page.wait_for_function("document.getElementById('pNow1').textContent.includes('02')")
            page.locator("#prevBtn").click()
            page.wait_for_function("document.getElementById('pNow1').textContent.includes('01')")


def test_player_ab_loop_cycle_is_safe():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p) as (page, _):
            page.locator('[data-play="0"]').click()
            for _ in range(3):  # 设 A → 设 B → 取消，全程不崩
                page.locator("#abBtn").click()
            assert page.evaluate("window.ImmersionReader.state.cur") == 0


def test_segment_read_button_speaks_without_error():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p) as (page, _):
            page.locator('[data-read="0"]').click()
            page.wait_for_timeout(300)  # speechSynthesis 启动窗口，pageerror 守卫兜底


def test_hard_and_chunk_popovers_with_copy_feedback():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p, permissions=["clipboard-read", "clipboard-write"]) as (page, _):
            page.locator("mark.hl").first.click()
            page.wait_for_selector(".term-popover .pop-def")
            page.locator(".term-popover .pop-ask").click()
            page.wait_for_function(
                "document.querySelector('.term-popover .pop-ask').textContent.includes('已复制')"
            )
            page.mouse.click(10, 10)
            chunk = page.locator(".chunk").first
            chunk.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            chunk.click()
            page.wait_for_selector(".term-popover")
            page.mouse.click(10, 10)


def test_popover_speak_and_segment_link_buttons_are_safe():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p) as (page, _):
            page.evaluate(
                """() => {
                  window.__spoken = [];
                  window.Audio = function(src = "") {
                    return {
                      src,
                      onerror: null,
                      play() { return Promise.reject(new Error("missing")); }
                    };
                  };
                  speechSynthesis.cancel = () => {};
                  speechSynthesis.getVoices = () => [];
                  speechSynthesis.speak = u => { window.__spoken.push(u.text); };
                }"""
            )
            page.locator("mark.hl").first.click()
            page.wait_for_selector(".term-popover .pop-speak")
            page.locator(".term-popover .pop-speak").click()
            page.wait_for_function("window.__spoken.length === 1")
            page.locator(".term-popover [data-jump-seg]").first.click()
            page.wait_for_selector(".term-popover", state="detached")


def test_basket_chip_remove_and_copy_summary():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p, permissions=["clipboard-read", "clipboard-write"]) as (page, _):
            page.locator('[data-confuse="0"]').click()
            page.locator('[data-confuse="1"]').click()
            page.wait_for_selector("#basketChip:not(.hidden)")
            assert "2" in page.locator("#basketChip").inner_text()
            page.locator("#basketChip").click()  # 跳页尾问题筐
            page.wait_for_selector('[data-remove-basket="0"]')
            page.locator('[data-remove-basket="0"]').click()
            page.wait_for_function(
                "document.getElementById('basketChip').textContent.includes('1')"
            )
            page.locator("#copyBasket").click()
            page.wait_for_function(
                "document.getElementById('copyBasket').textContent.includes('已复制')"
            )


def test_output_copy_buttons_use_written_text():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p, permissions=["clipboard-read", "clipboard-write"]) as (page, _):
            page.locator("#retellInput").fill("This article explains how constraints guide shipping.")
            page.locator("#copyRetell").click()
            page.wait_for_function(
                "document.getElementById('copyRetell').textContent.includes('已复制')"
            )
            page.locator("#transferInput").fill("We should make the constraint explicit before review.")
            page.locator("#copyTransfer").click()
            page.wait_for_function(
                "document.getElementById('copyTransfer').textContent.includes('已复制')"
            )


def test_dictation_action_buttons_check_reveal_and_retry():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p) as (page, _):
            page.locator('[data-dict="0"]').click()
            page.locator(".dict-input").fill("a quick test")
            page.locator('[data-check-dict="0"]').click()
            page.wait_for_selector(".dict-diff")
            page.locator('.pill-btn[data-dict="0"]').click()
            page.wait_for_selector(".dict-input")
            page.locator('[data-reveal-dict="0"]').click()
            page.wait_for_selector(".dict-input", state="detached")


def test_recording_playback_controls_are_safe_with_fake_microphone():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(
            url,
            p,
            launch_args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
            permissions=["microphone"],
        ) as (page, _):
            page.locator('[data-record="0"]').click()
            page.wait_for_selector('[data-stop-record="0"]')
            page.locator('[data-stop-record="0"]').click()
            page.wait_for_selector('[data-play-mine="0"]')
            assert page.evaluate("Boolean(window.ImmersionReader.state.recordings[0])")
            page.locator('[data-play-mine="0"]').click()
            page.wait_for_timeout(300)
            page.locator('[data-play-ab="0"]').click()
            page.wait_for_timeout(300)


def test_heat_cell_click_jumps_to_segment():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p) as (page, _):
            for _ in range(3):
                page.locator('[data-play="5"]').click()
            page.wait_for_selector(".heat-strip .heat-cell")
            page.locator(".heat-strip .heat-cell").nth(5).click()
            # 断言跳转目标段进入视口（CC 二审 RISK-7：scrollY 在 Playwright 自动滚动下无区分度）
            page.wait_for_function(
                """() => {
                  const r = document.querySelector('.seg[data-i="5"]').getBoundingClientRect();
                  return r.top > -50 && r.top < window.innerHeight * 0.8;
                }"""
            )


def test_week_day_cell_toggles_progress_state():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p) as (page, _):
            day = page.locator('.day[data-day="0"]')
            day.click()
            assert "on" in (day.get_attribute("class") or "")
            assert page.evaluate("JSON.parse(localStorage.getItem('ir_week'))") == [0]
            day.click()
            assert "on" not in (day.get_attribute("class") or "")
            assert page.evaluate("JSON.parse(localStorage.getItem('ir_week'))") == []


def test_blind_chip_and_done_reveal_buttons_restore_reading():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p) as (page, _):
            page.get_by_text("开始盲听").click()
            page.wait_for_selector(".blind-chip")
            page.locator("[data-blind-play]").last.click()
            page.wait_for_function(
                "window.ImmersionReader.state.cur === window.ImmersionReader.data.segments.length - 1"
            )
            page.evaluate(
                """() => {
                  const IR = window.ImmersionReader;
                  IR.data.segments.slice(0, -1).forEach((_, i) => IR.state.blindPlayed.add(i));
                  IR.state.audio.onended();
                }"""
            )
            page.wait_for_selector("#blindDoneReveal")
            page.locator("#blindDoneReveal").click()
            assert not page.evaluate("document.body.classList.contains('blind')")


def test_blind_reveal_button_restores_reading():
    build_demo()
    with demo_server() as url, sync_playwright() as p:
        with ui_page(url, p) as (page, _):
            page.get_by_text("开始盲听").click()
            page.wait_for_selector(".blind-chip")
            assert page.evaluate("document.body.classList.contains('blind')")
            page.locator("#revealBtn").click()
            assert not page.evaluate("document.body.classList.contains('blind')")
            assert page.locator(".seg").first.is_visible()
