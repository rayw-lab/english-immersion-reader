#!/usr/bin/env python3
"""Capture full-state screenshots for visual review (四联验 #2 / V-PASS 人审素材).

Covers the 14-state screenshot authority at desktop (1280) and halfscreen
(720) widths. Output: artifacts/screenshots/state-*.png
"""
import subprocess
import sys
import socket
import time
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "screenshots"


def build_demo() -> None:
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


def shot(page, name: str, full: bool = False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if full:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(300)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
    print(f"  saved {name}.png")


def select_in_seg0(page, text):
    """在 §1 正文单 text node 内建选区并触发 mouseup（文本必须避开 hard 词）。"""
    page.evaluate(
        """(text) => {
          const en = document.querySelector('.seg[data-i="0"] .en');
          const walker = document.createTreeWalker(en, NodeFilter.SHOW_TEXT);
          let node;
          while ((node = walker.nextNode())) {
            const idx = node.textContent.indexOf(text);
            if (idx >= 0) {
              const r = document.createRange();
              r.setStart(node, idx);
              r.setEnd(node, idx + text.length);
              const sel = getSelection();
              sel.removeAllRanges();
              sel.addRange(r);
              en.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
              return true;
            }
          }
          return false;
        }""",
        text,
    )


def capture(width: int, tag: str, url: str, p) -> None:
    browser = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
    context = browser.new_context(viewport={"width": width, "height": 960}, permissions=["microphone"])
    page = context.new_page()
    page.goto(url)
    page.wait_for_selector(".seg")
    page.wait_for_timeout(900)

    # 1. default (hero + study card + first segs)
    shot(page, f"state-{tag}-01-default")
    shot(page, f"state-{tag}-02-fullpage", full=True)

    # 2. term popover
    page.locator('[data-term="reliable"]').first.click()
    page.wait_for_timeout(250)
    shot(page, f"state-{tag}-03-popover")
    page.keyboard.press("Escape")
    page.mouse.wheel(0, 60)
    page.wait_for_timeout(200)

    # 3. seen term (gold ring) + basket
    page.locator('[data-confuse="0"]').click()
    page.wait_for_timeout(300)
    page.locator('[data-play="0"]').click()
    page.wait_for_timeout(400)
    shot(page, f"state-{tag}-04-seen-basket-playing")

    # 4. recording flow
    page.locator('[data-record="1"]').click()
    page.wait_for_selector(".recording-bar")
    page.wait_for_timeout(600)
    shot(page, f"state-{tag}-05-recording-bar")
    page.locator('[data-stop-record="1"]').click()
    page.wait_for_selector('[data-play-mine="1"]')
    page.locator('.seg[data-i="1"]').scroll_into_view_if_needed()
    page.wait_for_timeout(250)
    shot(page, f"state-{tag}-06-recording-controls")

    # 5. dictation
    page.locator('[data-dict="2"]').click()
    page.wait_for_timeout(300)
    page.locator(".dict-input").fill("the main thing is reliable systems and clear constraint")
    page.locator('[data-check-dict="2"]').click()
    page.wait_for_timeout(300)
    page.locator('.seg[data-i="2"]').scroll_into_view_if_needed()
    page.wait_for_timeout(250)
    shot(page, f"state-{tag}-07-dictation-diff")

    # 6. basket list open
    chip = page.locator("#basketChip")
    if chip.count() and "hidden" not in (chip.get_attribute("class") or ""):
        chip.click()
        page.wait_for_timeout(300)
        page.locator("#basketBlock").scroll_into_view_if_needed()
        page.wait_for_timeout(250)
        shot(page, f"state-{tag}-08-basket-list")

    # 7. heat strip
    page.locator("#heatBlock").scroll_into_view_if_needed()
    page.wait_for_timeout(250)
    shot(page, f"state-{tag}-09-heat-week")

    # 8. week punch
    page.locator(".day").first.click()
    page.wait_for_timeout(250)
    shot(page, f"state-{tag}-10-week-punched")

    # 9. blind mode
    page.get_by_text("开始盲听").click()
    page.wait_for_selector(".blind-grid")
    page.wait_for_timeout(400)
    shot(page, f"state-{tag}-11-blind")
    page.get_by_text("揭文本").click()
    page.wait_for_timeout(400)

    # 10. zh hidden mode
    page.locator("#zhBtn").click()
    page.wait_for_timeout(250)
    page.locator('.seg[data-i="0"]').scroll_into_view_if_needed()
    page.wait_for_timeout(250)
    shot(page, f"state-{tag}-12-zh-hidden")
    page.locator("#zhBtn").click()  # 恢复中文显示（替换原有恢复点击，勿叠加）
    select_in_seg0(page, "they ship the widest possible surface, watch it break in unexpected hands")
    page.wait_for_selector(".term-popover")
    page.wait_for_timeout(250)
    shot(page, f"state-{tag}-13-selection-passage")
    page.mouse.click(10, 10)  # 点空白关闭浮层
    select_in_seg0(page, "shows what is possible")
    page.wait_for_selector(".term-popover")
    page.wait_for_timeout(250)
    shot(page, f"state-{tag}-14-selection-phrase")
    page.mouse.click(10, 10)

    browser.close()


def main() -> int:
    build_demo()
    with demo_server() as url:
        with sync_playwright() as p:
            print("== desktop 1280 ==")
            capture(1280, "desktop", url, p)
            print("== halfscreen 720 ==")
            capture(720, "halfscreen", url, p)
    print(f"\nall screenshots → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
