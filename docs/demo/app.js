(() => {
  const data = window.__LESSON_DATA__;
  const audioStatus = window.__AUDIO_STATUS__ || { missing: [], count: 0 };
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const KEYS = {
    counts: "ir_counts",
    out: "ir_out",
    transfer: "ir_transfer",
    week: "ir_week",
    last: "ir_last",
    basket: "ir_basket",
    seen: "ir_seen_terms",
    plays: "ir_plays",
    rate: "ir_rate",
    zh: "ir_zh",
    fs: "ir_fs",
    voice: "ir_voice"
  };

  const TYPE_CN = { term: "术语", word: "生词", idiom: "搭配", chunk: "词块" };

  const state = {
    cur: -1,
    audio: null,
    rate: parseFloat(localStorage.getItem(KEYS.rate) || "1"),
    counts: readJSON(KEYS.counts, {}),
    basket: readJSON(KEYS.basket, []),
    seen: readJSON(KEYS.seen, {}),
    plays: readJSON(KEYS.plays, {}),
    recordings: {},
    recording: null,
    dictI: null,
    blind: false,
    blindPlayed: new Set(),
    durations: {},
    toastTimer: null,
    // A-B 复读: phase 0=off, 1=A set, 2=looping
    ab: { phase: 0, a: 0, b: 0 }
  };

  function readJSON(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback));
    } catch {
      return fallback;
    }
  }

  function writeJSON(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function esc(text) {
    return String(text || "").replace(/[&<>"']/g, ch => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    }[ch]));
  }

  function root() {
    return $("#app");
  }

  function toast(message) {
    const el = $("#toast");
    if (!el) return;
    el.textContent = message;
    el.classList.add("show");
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => el.classList.remove("show"), 1800);
  }

  /* ---------- render ---------- */

  function render() {
    const meta = data.meta;
    const safeUrl = meta.url && /^https?:\/\//i.test(meta.url) ? meta.url : "";
    const sourceLine = [
      esc(meta.source),
      safeUrl ? `<a href="${esc(safeUrl)}" target="_blank" rel="noopener">原文 ↗</a>` : ""
    ].filter(Boolean).join(" · ");
    root().innerHTML = `
      <header class="topbar">
        <div class="topbar-inner">
          <div class="brand"><span class="brand-dot"></span>Immersion Reader<span class="brand-cn">· 英语精读</span></div>
          <div class="toolbar">
            <span id="recProgress" class="tool-progress hidden" title="每段跟读录音 3 次达标"></span>
            <button id="revealBtn" class="tool primary hidden">揭文本</button>
            <button id="zhBtn" class="tool" title="显示 / 隐藏中文大意">中文</button>
            <button id="fsDown" class="tool" title="缩小英文字号">A−</button>
            <button id="fsUp" class="tool" title="放大英文字号">A+</button>
            <button id="resetBtn" class="tool danger" title="清空本课学习记录（保留语速等偏好）">重置</button>
          </div>
        </div>
      </header>
      <section class="hero">
        <p class="kicker">${meta.kind === "video" ? "视频精读" : "文章精读"} · Immersion Reader</p>
        <h1>${esc(meta.title)}</h1>
        <p class="source">${sourceLine}</p>
        ${audioStatus.missing.length ? `<p class="audio-note">🔈 ${audioStatus.missing.length} 段音频缺失，将使用浏览器朗读兜底</p>` : ""}
      </section>
      ${renderStudyCard()}
      <section id="blindGrid" class="blind-grid hidden"></section>
      <section id="segments" class="segments">${data.segments.map(renderSegment).join("")}</section>
      <section class="learning-block" id="chunksBlock">${renderChunks()}</section>
      <section class="learning-block" id="patternsBlock">${renderPatterns()}</section>
      <section class="learning-block output-block" id="outputBlock">${renderOutput()}</section>
      <section class="learning-block basket-block hidden" id="basketBlock"></section>
      <section class="learning-block heat-block hidden" id="heatBlock"></section>
      <section class="learning-block week-block" id="weekBlock">${renderWeek()}</section>
      <footer class="player">
        <div class="player-inner">
          <button id="playBtn" class="p-main" title="播放 / 暂停" aria-label="播放或暂停">▶</button>
          <button id="prevBtn" class="p-step" title="上一段" aria-label="上一段">⏮</button>
          <button id="nextBtn" class="p-step" title="下一段" aria-label="下一段">⏭</button>
          <button id="abBtn" class="p-step p-ab" title="A-B 复读：播放中点一下设 A 点，再点设 B 点开始循环，第三下取消" aria-label="A-B 复读">A·B</button>
          <div id="nowPlaying" class="p-now">
            <span id="pNow1">未选择段落</span>
            <span id="pNow2">点段落里的 ▶，或直接按左侧播放键</span>
          </div>
          <div class="p-rate" role="group" aria-label="语速">
            <button class="rate" data-rate="0.8">0.8×</button>
            <button class="rate" data-rate="1">1.0×</button>
            <button class="rate" data-rate="1.2">1.2×</button>
            <button class="rate" data-rate="1.5">1.5×</button>
          </div>
          <button id="basketChip" class="basket-chip hidden" title="问题筐 · 点击查看">0</button>
        </div>
      </footer>
    `;
    applyInitialPrefs();
    bindBaseEvents();
    updateBasketChip();
    renderBasket();
    renderHeat();
    observeFadeIns();
    startHalo();
  }

  function renderStudyCard() {
    const card = data.meta.study_card;
    const suggestion = suggest();
    return `
      <section class="study-card">
        <div class="study-top">
          <span class="study-kicker">学习卡</span>
          <div class="study-line">
            <span class="pill">${card.word_count} 词</span>
            <span class="pill">约 ${card.estimated_days} 天</span>
            <span class="pill">难度 ${esc(card.difficulty)}</span>
            <span class="pill main">${esc(card.main_practice)}</span>
          </div>
        </div>
        <ul class="study-values">${card.value_points.map(v => `<li>${esc(v)}</li>`).join("")}</ul>
        <div class="study-foot">
          <div class="study-suggest">${esc(suggestion.main)}${suggestion.sub ? `<span>${esc(suggestion.sub)}</span>` : ""}</div>
          <div class="study-actions">${studyActions().join("")}</div>
        </div>
      </section>
    `;
  }

  function studyActions() {
    const last = readJSON(KEYS.last, null);
    const fresh = last && Date.now() - last.ts < 48 * 60 * 60 * 1000;
    if (fresh) {
      return [
        `<button class="primary" data-jump="${esc(last.id)}">继续 §${segmentNumber(last.id)}</button>`,
        `<button class="secondary" id="startBlind">盲听全文</button>`
      ];
    }
    return [`<button class="primary" id="startBlind">开始盲听</button>`];
  }

  function segmentNumber(id) {
    const idx = data.segments.findIndex(seg => seg.id === id);
    return idx >= 0 ? idx + 1 : 1;
  }

  function suggest() {
    const last = readJSON(KEYS.last, null);
    let main = "先盲听全文";
    if (!Object.keys(state.counts).length && !last) {
      main = "先盲听全文";
    } else if (last && Date.now() - last.ts < 48 * 60 * 60 * 1000) {
      main = `继续 §${segmentNumber(last.id)}`;
    } else if (last) {
      const days = Math.max(2, Math.floor((Date.now() - last.ts) / (24 * 60 * 60 * 1000)));
      main = `隔了 ${days} 天, 建议从 §1 盲听复习`;
    }
    let sub = "";
    if (state.basket.length >= 3) {
      sub = ` · 攒了 ${state.basket.length} 条, 学完复制复盘`;
    } else {
      const hot = hotSegment();
      if (hot) sub = ` · 回访 §${hot}`;
    }
    return { main, sub };
  }

  function hotSegment() {
    const vals = data.segments.map((_, i) => Number(state.plays[i]) || 0);
    if (!vals.some(Boolean)) return null;
    const max = Math.max(...vals);
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    if (max >= 3 && max >= 2 * avg) {
      const key = vals.findIndex(count => count === max);
      return Number(key) + 1;
    }
    return null;
  }

  function renderSegment(seg, i) {
    // seg-head icon cap: 5 — keep the action row scannable; everything else lives in popovers / train-slot
    return `
      <article class="seg" data-i="${i}" id="${esc(seg.id)}">
        <div class="seg-head">
          <span class="seg-id">§${i + 1}</span>
          ${seg.spk ? `<span class="seg-spk">${esc(seg.spk)}</span>` : ""}
          <span class="seg-flex"></span>
          <div class="seg-actions">
            <button class="icbtn primary-play" title="播放本段" aria-label="播放 §${i + 1}" data-play="${i}">▶</button>
            <button class="icbtn" title="0.8× 慢速播放本段" aria-label="慢速播放 §${i + 1}" data-read="${i}">🔊</button>
            <button class="icbtn" title="没看懂？复制给 agent 拆解" aria-label="拆解 §${i + 1}" data-confuse="${i}">🤔</button>
            <button class="icbtn" title="录自己跟读，原音对照" aria-label="录音 §${i + 1}" data-record="${i}">🎙</button>
            <button class="icbtn" title="听写这一段" aria-label="听写 §${i + 1}" data-dict="${i}">✍</button>
          </div>
        </div>
        <div class="seg-body">
          <p class="en">${renderHard(seg.en, seg.hard)}</p>
          <p class="zh">${esc(seg.zh)}</p>
          <div class="train-slot"></div>
        </div>
      </article>
    `;
  }

  function renderHard(text, hard) {
    // longest-first placeholder swap: avoids nested marks when one term contains another
    const items = [...(hard || [])].sort((a, b) => b.w.length - a.w.length);
    let out = text;
    const slots = [];
    items.forEach((item, idx) => {
      const pos = out.toLowerCase().indexOf(item.w.toLowerCase());
      if (pos < 0) return;
      const shown = out.slice(pos, pos + item.w.length);
      const token = `__IR_HARD_${idx}__`;
      out = out.slice(0, pos) + token + out.slice(pos + item.w.length);
      slots.push({ token, item, shown });
    });
    out = esc(out);
    slots.forEach(({ token, item, shown }) => {
      const seen = state.seen[item.w.toLowerCase()] ? " seen" : "";
      const type = item.type || "word";
      // replacer function: keeps "$&"-style sequences in defs from being expanded by String.replace
      out = out.replace(
        token,
        () => `<mark class="hl ${esc(type)}${seen}" data-term="${esc(item.w)}" data-def="${esc(item.def || "")}" data-type="${esc(type)}" tabindex="0" role="button">${esc(shown)}</mark>`
      );
    });
    return out;
  }

  function renderChunks() {
    return `
      <h2>词块 · 拿来就用</h2>
      <p class="block-sub">点词块 = 记一次见面 + 弹出释义可复制问 agent · 例句偏程序员工作场景</p>
      <div class="chunks">${data.chunks.map(chunk => {
        const seen = state.seen[chunk.t.toLowerCase()] ? " seen" : "";
        return `<button class="chunk${seen}" data-chunk="${esc(chunk.t)}"><b>${esc(chunk.t)}</b><span class="c-cn">${esc(chunk.cn)}</span><em class="c-eg">${esc(chunk.eg)}</em></button>`;
      }).join("")}</div>
    `;
  }

  function renderPatterns() {
    return `
      <h2>句型骨架</h2>
      <p class="block-sub">本课值得偷走的表达框架 — 替换变量就能用在自己的话里</p>
      <div class="patterns">${data.patterns.map(p => `<div class="pattern"><b>${esc(p.t)}</b><span>${esc(p.cn)}</span></div>`).join("")}</div>
    `;
  }

  function renderOutput() {
    const transfer = (data.transfer_tasks || [])[0];
    return `
      <h2>输出 · 学完写两笔</h2>
      <p class="block-sub">内容自动保存在本机 — 写完复制批改 prompt 去问你的 agent</p>
      <div class="output-card">
        <h3>① 复述本课</h3>
        <p class="task-hint">用自己的英文写 3-5 句总结，别回看原文。</p>
        <textarea id="retellInput" placeholder="Write a 3-5 sentence English summary."></textarea>
        <span class="save-flash" id="retellSaved"></span>
        <button class="primary-btn" id="copyRetell">📋 复制批改 prompt</button>
      </div>
      ${transfer ? `<div class="output-card">
        <h3>② 迁移任务 · ${esc(transfer.genre)}</h3>
        <p class="task-text">${esc(transfer.task)}</p>
        ${transfer.hint_chunks && transfer.hint_chunks.length ? `<p class="task-hint">提示词块：${transfer.hint_chunks.map(esc).join(" / ")}</p>` : ""}
        <textarea id="transferInput" placeholder="Write your workplace output in English."></textarea>
        <span class="save-flash" id="transferSaved"></span>
        <button class="primary-btn" id="copyTransfer">📋 复制批改 prompt</button>
      </div>` : ""}
    `;
  }

  function renderWeek() {
    const week = readJSON(KEYS.week, []);
    const names = ["一", "二", "三", "四", "五", "六", "日"];
    return `
      <h2>本周打卡</h2>
      <p class="block-sub">学完一天点亮一格 — 节奏比强度重要</p>
      <div class="week">${names.map((name, i) => `
        <button class="day${week.includes(i) ? " on" : ""}" data-day="${i}"><span class="dn">周${name}</span><span class="dl">已学</span></button>
      `).join("")}</div>
    `;
  }

  /* ---------- clipboard ---------- */

  function copyText(text, button) {
    const finish = () => {
      if (!button) return;
      if (button.classList.contains("icbtn")) {
        const oldLabel = button.getAttribute("aria-label") || "";
        button.classList.add("copied");
        button.setAttribute("aria-label", "已复制");
        setTimeout(() => {
          button.classList.remove("copied");
          if (oldLabel) button.setAttribute("aria-label", oldLabel);
          else button.removeAttribute("aria-label");
        }, 1200);
        return;
      }
      const old = button.textContent;
      button.textContent = "✓ 已复制";
      setTimeout(() => { button.textContent = old; }, 1200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(finish).catch(finish);
    }
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    try {
      document.execCommand("copy");
    } catch {
      // Browser clipboard access can be unavailable under file://; the basket state still records the question.
    }
    area.remove();
    finish();
    return Promise.resolve();
  }

  /* ---------- audio ---------- */

  function audioSrc(i) {
    const tts = data.segments[i].tts || "";
    if (/\.mp3($|\?)/.test(tts)) return tts.includes("/") ? tts : `audio/${tts}`;
    return `audio/${data.segments[i].id}.mp3`;
  }

  function wordAudioSlug(term) {
    return String(term || "")
      .trim()
      .toLowerCase()
      .replace(/['’]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/-{2,}/g, "-")
      .replace(/^-|-$/g, "") || "term";
  }

  function wordAudioSrc(term) {
    return `audio/w/${wordAudioSlug(term)}.mp3`;
  }

  function preferredSpeechVoice() {
    if (!("speechSynthesis" in window)) return null;
    const voices = speechSynthesis.getVoices ? speechSynthesis.getVoices() : [];
    const saved = localStorage.getItem(KEYS.voice);
    const savedHit = saved ? voices.find(voice => voice.name === saved) : null;
    if (savedHit) return savedHit;
    const enUs = voices.filter(voice => /^en-US\b/i.test(voice.lang || ""));
    const picked = enUs.find(voice => voice.localService === false) || enUs[0] || null;
    if (picked) localStorage.setItem(KEYS.voice, picked.name);
    return picked;
  }

  function speakText(text, rate = 0.95, onend = null) {
    if (!("speechSynthesis" in window)) {
      setPlayIcon(false);
      if (onend) onend();
      return;
    }
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "en-US";
    utter.rate = rate;
    const voice = preferredSpeechVoice();
    if (voice) utter.voice = voice;
    utter.onend = () => {
      setPlayIcon(false);
      if (onend) onend();
    };
    speechSynthesis.cancel();
    speechSynthesis.speak(utter);
  }

  function playWordAudio(term) {
    stopAudio();
    let didFallback = false;
    const fallback = () => {
      if (didFallback) return;
      didFallback = true;
      speakText(term, 0.95);
    };
    const audio = new Audio(wordAudioSrc(term));
    audio.onerror = fallback;
    audio.play().catch(fallback);
  }

  function writeLast(i) {
    writeJSON(KEYS.last, { id: data.segments[i].id, ts: Date.now() });
  }

  function setPlayIcon(playing) {
    const btn = $("#playBtn");
    if (btn) btn.textContent = playing ? "⏸" : "▶";
  }

  function setNow(i) {
    const seg = data.segments[i];
    const n1 = $("#pNow1");
    const n2 = $("#pNow2");
    if (n1) n1.textContent = `第 ${String(i + 1).padStart(2, "0")} 段 · 共 ${data.segments.length} 段${seg.spk ? ` · ${seg.spk}` : ""}`;
    if (n2) n2.textContent = state.blind ? "盲听中 · 文本已隐藏" : seg.en.slice(0, 46) + (seg.en.length > 46 ? "…" : "");
  }

  function stopAudio() {
    stopKaraoke();
    if (state.audio) {
      const old = state.audio;
      state.audio = null;
      // detach handlers BEFORE touching src: clearing src fires a media error
      // event, and a live onerror would speak the old segment over the new one
      old.onended = null;
      old.onerror = null;
      old.ontimeupdate = null;
      old.pause();
      old.removeAttribute("src");
      old.load();
    }
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    setPlayIcon(false);
  }

  function handleEnded(i) {
    setPlayIcon(false);
    if (state.blind) {
      state.blindPlayed.add(i);
      renderBlindGrid();
      if (i + 1 < data.segments.length) playSeg(i + 1, true);
      else renderBlindComplete();
    }
  }


  /* ---------- 逐词高亮（karaoke）: build 期 WordBoundary 对齐数据驱动 ---------- */

  const wordTimings = window.__WORD_TIMINGS__ || {};
  const karaoke = { raf: null, segI: null, ranges: null, times: null, idx: -1 };
  let seekTimer = null;

  function karaokeSupported() {
    return typeof CSS !== "undefined" && CSS.highlights && typeof Highlight !== "undefined";
  }

  function charRangeIn(el, c0, c1) {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let pos = 0;
    let node;
    let start = null;
    while ((node = walker.nextNode())) {
      const len = node.textContent.length;
      if (start === null && c0 < pos + len) start = [node, c0 - pos];
      if (c1 <= pos + len) {
        if (!start) return null;
        const range = new Range();
        range.setStart(start[0], Math.max(0, start[1]));
        range.setEnd(node, c1 - pos);
        return range;
      }
      pos += len;
    }
    return null;
  }

  function stopKaraoke() {
    if (karaoke.raf) cancelAnimationFrame(karaoke.raf);
    karaoke.raf = null;
    karaoke.segI = null;
    karaoke.ranges = null;
    karaoke.times = null;
    karaoke.idx = -1;
    if (karaokeSupported()) CSS.highlights.delete("karaoke");
  }

  function startKaraoke(i) {
    stopKaraoke();
    if (!karaokeSupported() || state.blind) return;
    const entries = wordTimings[data.segments[i].id];
    if (!entries || !entries.length) return;
    const en = document.querySelector(`.seg[data-i="${i}"] .en`);
    if (!en || en.querySelector(".dict-input")) return; // 听写态不高亮
    const ranges = [];
    const times = [];
    entries.forEach(([t0, t1, c0, c1]) => {
      const range = charRangeIn(en, c0, c1);
      if (range) { ranges.push(range); times.push(t0); }
    });
    if (!ranges.length) return;
    karaoke.segI = i;
    karaoke.ranges = ranges;
    karaoke.times = times;
    const tick = () => {
      if (karaoke.segI !== i || !state.audio) return;
      const t = state.audio.currentTime;
      // 最后一个 t0 <= t 的词保持高亮到下一词开始: 停顿期不闪烁
      let lo = 0, hi = times.length - 1, idx = -1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (times[mid] <= t) { idx = mid; lo = mid + 1; } else hi = mid - 1;
      }
      if (idx !== karaoke.idx) {
        karaoke.idx = idx;
        if (idx < 0) CSS.highlights.delete("karaoke");
        else CSS.highlights.set("karaoke", new Highlight(ranges[idx]));
      }
      karaoke.raf = requestAnimationFrame(tick);
    };
    karaoke.raf = requestAnimationFrame(tick);
  }

  function seekSeg(i, t) {
    if (state.cur === i && state.audio) {
      state.audio.currentTime = t;
      if (state.audio.paused) {
        state.audio.play().catch(() => {});
        setPlayIcon(true);
      }
      return;
    }
    playSeg(i, false);
    const audio = state.audio;
    if (!audio) return;
    const apply = () => { if (state.audio === audio) audio.currentTime = t; };
    if (audio.readyState >= 1) apply();
    else audio.addEventListener("loadedmetadata", apply, { once: true });
  }

  function charOffsetFromPoint(en, x, y) {
    let node = null;
    let offset = 0;
    if (document.caretRangeFromPoint) {
      const r = document.caretRangeFromPoint(x, y);
      if (r) { node = r.startContainer; offset = r.startOffset; }
    } else if (document.caretPositionFromPoint) {
      const pos = document.caretPositionFromPoint(x, y);
      if (pos) { node = pos.offsetNode; offset = pos.offset; }
    }
    if (!node || node.nodeType !== Node.TEXT_NODE || !en.contains(node)) return null;
    let acc = 0;
    const walker = document.createTreeWalker(en, NodeFilter.SHOW_TEXT);
    let cur;
    while ((cur = walker.nextNode())) {
      if (cur === node) return acc + offset;
      acc += cur.textContent.length;
    }
    return null;
  }

  function handleWordSeekClick(event) {
    if (state.blind) return;
    if (event.detail > 1) return; // 双击是划词查询, 不抢
    const en = event.target.closest?.(".seg .en");
    if (!en) return;
    if (event.target.closest("mark.hl, button, textarea, a")) return;
    const segEl = en.closest(".seg");
    const i = Number(segEl.dataset.i);
    const entries = wordTimings[data.segments[i] ? data.segments[i].id : ""];
    if (!entries || !entries.length) return;
    const off = charOffsetFromPoint(en, event.clientX, event.clientY);
    if (off === null) return;
    const hit = entries.find(entry => off >= entry[2] && off < entry[3]);
    if (!hit) return;
    clearTimeout(seekTimer);
    // 延迟一拍: 若随后形成选区(划词/双击), 放弃跳播
    seekTimer = setTimeout(() => {
      const sel = window.getSelection();
      if (sel && !sel.isCollapsed) return;
      if (document.querySelector(".term-popover")) return;
      seekSeg(i, Math.max(0, hit[0] - 0.05));
    }, 260);
  }

  /* ---------- A-B 复读 ---------- */

  function resetAB() {
    state.ab = { phase: 0, a: 0, b: 0 };
    updateABBtn();
  }

  function updateABBtn() {
    const btn = $("#abBtn");
    if (!btn) return;
    const labels = ["A·B", "A ✓ →B", "A-B 循环中"];
    btn.textContent = labels[state.ab.phase];
    btn.classList.toggle("on", state.ab.phase > 0);
  }

  function cycleAB() {
    const audio = state.audio;
    if (state.ab.phase === 2) {
      resetAB();
      toast("已退出 A-B 复读");
      return;
    }
    if (!audio || !audio.src || audio.paused) {
      toast("先播放一段 mp3，再点 A·B 设循环点");
      return;
    }
    if (state.ab.phase === 0) {
      state.ab = { phase: 1, a: audio.currentTime, b: 0 };
      toast("A 点已设，到结束位置再点一下设 B 点");
    } else {
      if (audio.currentTime <= state.ab.a + 0.3) {
        toast("B 点要在 A 点之后，再听一会儿再点");
        return;
      }
      state.ab = { phase: 2, a: state.ab.a, b: audio.currentTime };
      audio.currentTime = state.ab.a;
      toast("A-B 循环开始，再点一下取消");
    }
    updateABBtn();
  }

  function playSeg(i, auto = false) {
    if (i < 0 || i >= data.segments.length) return;
    stopAudio();
    if (state.cur !== i) resetAB();
    state.cur = i;
    if (state.blind) renderBlindGrid();
    $$(".seg").forEach(el => el.classList.remove("active"));
    const el = document.querySelector(`.seg[data-i="${i}"]`);
    if (el) el.classList.add("active");
    setNow(i);
    setPlayIcon(true);
    const audio = new Audio(audioSrc(i));
    state.audio = audio;
    audio.playbackRate = state.rate;
    startKaraoke(i);
    // guard on identity: play() rejections and error events can arrive after a
    // segment switch; a stale fallback would talk over the current segment
    const isCurrent = () => state.audio === audio;
    audio.onended = () => { if (isCurrent()) handleEnded(i); };
    audio.onerror = () => { if (isCurrent()) speakSeg(i, () => handleEnded(i)); };
    audio.ontimeupdate = () => {
      if (isCurrent() && state.ab.phase === 2 && audio.currentTime >= state.ab.b) {
        audio.currentTime = state.ab.a;
      }
    };
    audio.play().catch(() => { if (isCurrent()) speakSeg(i, () => handleEnded(i)); });
    if (!auto) {
      state.plays[i] = (Number(state.plays[i]) || 0) + 1;
      writeJSON(KEYS.plays, state.plays);
      writeLast(i);
      renderHeat();
    }
  }

  function playSegSlow(i) {
    if (i < 0 || i >= data.segments.length) return;
    stopAudio();
    if (state.cur !== i) resetAB();
    state.cur = i;
    $$(".seg").forEach(el => el.classList.remove("active"));
    const el = document.querySelector(`.seg[data-i="${i}"]`);
    if (el) el.classList.add("active");
    setNow(i);
    setPlayIcon(true);
    const audio = new Audio(audioSrc(i));
    state.audio = audio;
    audio.playbackRate = 0.8;
    const isCurrent = () => state.audio === audio;
    let didFallback = false;
    const fallback = () => {
      if (!isCurrent() || didFallback) return;
      didFallback = true;
      speakText(data.segments[i].tts || data.segments[i].en, 0.95);
    };
    audio.onended = () => { if (isCurrent()) setPlayIcon(false); };
    audio.onerror = fallback;
    audio.play().catch(fallback);
  }

  function speakSeg(i, onend = null) {
    speakText(data.segments[i].tts || data.segments[i].en, state.rate, onend);
  }

  /* ---------- agent prompts (copy-out surface) ---------- */

  function askWordPrompt(word, context) {
    return [
      "请用中文解释这个英文表达。",
      `表达: ${word}`,
      `上下文: ${context}`,
      "请给出: 1) 中文释义 2) 在本句里的意思 3) 一个程序员工作场景例句。"
    ].join("\n");
  }

  function askPassagePrompt(text) {
    return [
      "请帮我精读这段英文:",
      `"${text}"`,
      "",
      "请给我: 1) 通顺的中文翻译 2) 其中的难词/术语/固定搭配(各附中文释义) 3) 拆解 1-2 个长难句的结构。",
      "(我在做英语精读, 目标是彻底读懂并能复述这段。)"
    ].join("\n");
  }

  function lessonHeader() {
    return `本课:《${data.meta.title}》(${data.meta.source})`;
  }

  function askSegPrompt(i) {
    const seg = data.segments[i];
    const prev = i > 0 ? data.segments[i - 1].en.split(".").slice(-1)[0].trim() : "";
    return [
      lessonHeader(),
      "请用中文拆解这段英文, 不要全文直译。",
      prev ? `前段衔接: ${prev}` : "",
      `原文: ${seg.en}`,
      `我已有的大意: ${seg.zh}`,
      "请输出: 1) 句子主干 2) 逻辑转折 3) 背景知识 4) 难点表达 5) 这段的理解提示。"
    ].filter(Boolean).join("\n");
  }

  function basketPrompt() {
    const words = state.basket.filter(item => item.type === "word");
    const segs = state.basket.filter(item => item.type === "seg");
    const lines = [
      lessonHeader(),
      `今天这课我攒了 ${state.basket.length} 个问题。请先找共性, 再逐项讲解, 最后给明天复习建议。`,
      "",
      "词/短语:",
      ...words.map(item => `- ${item.w}: ${item.ctx || ""}`),
      "",
      "段落:",
      ...segs.map(item => {
        const seg = data.segments.find(s => s.id === item.id);
        return `- ${item.id}: ${seg ? seg.en : ""}`;
      })
    ];
    const retell = localStorage.getItem(KEYS.out);
    if (retell) lines.push("", `我的复述: ${retell}`);
    return lines.join("\n");
  }

  function retellPrompt() {
    return [
      "请批改我的英文复述。",
      `原文标题: ${data.meta.title}`,
      `我的复述: ${localStorage.getItem(KEYS.out) || ""}`,
      "请检查: 1) 是否漏掉要点 2) 英文是否自然 3) 给出更地道版本。"
    ].join("\n");
  }

  function transferPrompt() {
    const task = (data.transfer_tasks || [])[0];
    return [
      lessonHeader(),
      "请批改我的英文职场迁移输出。",
      `任务: ${task ? task.task : ""}`,
      `提示词块: ${task ? task.hint_chunks.join(", ") : ""}`,
      `我的输出: ${localStorage.getItem(KEYS.transfer) || ""}`,
      "请检查: 1) 词块是否用对 2) 语域是否匹配体裁 3) 句式是否自然。"
    ].join("\n");
  }

  /* ---------- term popover ---------- */

  function markSeenTerm(term) {
    state.seen[term.toLowerCase()] = Date.now();
    writeJSON(KEYS.seen, state.seen);
    $$(`[data-term="${CSS.escape(term)}"], [data-chunk="${CSS.escape(term)}"]`).forEach(el => el.classList.add("seen"));
  }

  function closePopovers() {
    $$(".term-popover").forEach(el => el.remove());
  }

  function lookupLexicon(term) {
    const lex = data.lexicon || {};
    const lower = term.toLowerCase();
    const raw = lex[lower];
    if (!raw) return null;
    const entry = raw.def ? raw : (raw.lemma ? lex[raw.lemma] : null);
    if (!entry || !entry.def) return null;
    return {
      def: entry.def,
      type: "word",
      ipa: entry.ipa || "",
      lemma: raw.lemma || ""
    };
  }

  function mergeLexiconInfo(term, base) {
    const lexHit = lookupLexicon(term);
    if (!lexHit) return base;
    return {
      ...base,
      ipa: base.ipa || lexHit.ipa || "",
      lemma: base.lemma || lexHit.lemma || ""
    };
  }

  function escapeRegExp(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function termOccurrences(term) {
    const re = new RegExp(`\\b${escapeRegExp(term)}\\b`, "i");
    const hits = [];
    data.segments.forEach((seg, i) => {
      if (re.test(seg.en)) hits.push(i + 1);
    });
    return hits;
  }

  function lookupTerm(term, anchor) {
    if (anchor && anchor.dataset && anchor.dataset.def) {
      return mergeLexiconInfo(term, { def: anchor.dataset.def, type: anchor.dataset.type || "word" });
    }
    const lower = term.toLowerCase();
    for (const seg of data.segments) {
      const hit = (seg.hard || []).find(item => item.w.toLowerCase() === lower);
      if (hit) return mergeLexiconInfo(term, { def: hit.def || "", type: hit.type || "word" });
    }
    const chunk = (data.chunks || []).find(item => item.t.toLowerCase() === lower);
    if (chunk) return mergeLexiconInfo(term, { def: chunk.cn, eg: chunk.eg || "", type: "chunk" });
    const lexHit = lookupLexicon(term);
    if (lexHit) return lexHit;
    return { def: "", type: "word" };
  }

  function positionPopover(popover, anchor) {
    const rect = anchor.getBoundingClientRect();
    const w = popover.offsetWidth;
    const h = popover.offsetHeight;
    // 左缘对齐选区起点（不再水平居中），减少对正文的覆盖面
    let left = Math.max(12, Math.min(rect.left, window.innerWidth - w - 12));
    // 默认在选区下方 8px；放不下翻到上方；再放不下贴底 clamp
    let top = rect.bottom + 8;
    if (top + h > window.innerHeight - 12) top = rect.top - h - 8;
    if (top < 12) top = Math.max(12, window.innerHeight - h - 12);
    popover.style.left = `${left}px`;
    popover.style.top = `${top}px`;
  }

  function popCardHTML(word, info, context) {
    const occ = termOccurrences(word);
    const occLine = occ.length
      ? `本课 ${occ.length} 次 · ${occ.slice(0, 4).map(n => `<button class="pop-seglink" data-jump-seg="${n - 1}">§${n}</button>`).join(" ")}`
      : "";
    const metaBits = [
      info.lemma ? `${esc(word.toLowerCase())} → ${esc(info.lemma)}` : "",
      occLine
    ].filter(Boolean);
    return `
      <div class="pop-head">
        <span class="pop-word">${esc(word)}</span>
        <span class="pop-type ${esc(info.type)}">${esc(info.badge || TYPE_CN[info.type] || "词条")}</span>
        <button class="pop-speak" data-speak="${esc(word)}" title="朗读">🔊</button>
      </div>
      ${info.ipa ? `<div class="pop-ipa">${esc(info.ipa)}</div>` : ""}
      ${info.def ? `<div class="pop-def">${esc(info.def)}</div>` : ""}
      ${info.eg ? `<div class="pop-eg">例：${esc(info.eg)}</div>` : ""}
      ${metaBits.length ? `<div class="pop-meta">${metaBits.join('<span class="pop-dot">·</span>')}</div>` : ""}
      <button class="pop-ask ${info.def ? "ghost-ask" : ""}" data-copy-word="${esc(word)}" data-copy-context="${esc(context)}">${info.def ? "仍不懂？复制 → 问你的 agent" : "📋 复制 → 问你的 agent"}</button>
      ${info.def ? "" : `<div class="pop-sub">复制「表达 + 原句 + 学习目标」，粘给本地 agent 即可</div>`}
    `;
  }

  function showTermPopover(anchor, term, context) {
    markSeenTerm(term);
    closePopovers();
    const info = lookupTerm(term, anchor);
    const popover = document.createElement("div");
    popover.className = "term-popover";
    popover.innerHTML = popCardHTML(term, info, context);
    document.body.appendChild(popover);
    positionPopover(popover, anchor);
  }

  /* ---------- selection popover (划词复制, S4 冗余通道) ---------- */

  const SELECTION_WORD_CAP = 120;
  const SELECTION_CHAR_CAP = 1200;
  // passage text lives here instead of a data attribute: selections run long
  let selectionPassage = "";

  function selectionInfo() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
    const text = String(sel).trim();
    if (text.length < 2) return null;
    if (/[一-龥]/.test(text)) return null;
    const range = sel.getRangeAt(0);
    const host = (range.startContainer.nodeType === 1
      ? range.startContainer
      : range.startContainer.parentElement)?.closest?.(".seg, .pattern");
    if (!host) return null;
    const segEl = host.classList.contains("seg") ? host : null;
    const patternEl = segEl ? null : host;
    const words = text.split(/\s+/).filter(Boolean);
    return { text, words: words.length, chars: text.length, range, segEl, patternEl };
  }

  function selectionSentence(info) {
    if (info.patternEl) {
      const sentence = info.patternEl.querySelector("b");
      return (sentence ? sentence.textContent : info.patternEl.textContent).trim().slice(0, 280);
    }
    const en = data.segments[Number(info.segEl.dataset.i)]?.en || "";
    const probe = info.text.slice(0, 60);
    const hit = en.split(/(?<=[.!?])\s+/).find(s => s.includes(probe));
    return hit || en.slice(0, 280);
  }

  function showSelectionPopover(info) {
    closePopovers();
    const isPhrase = info.words <= 5 && info.chars <= 40;
    const popover = document.createElement("div");
    popover.className = "term-popover";
    if (isPhrase) {
      const context = selectionSentence(info);
      const hit = info.words === 1 ? lookupTerm(info.text, null) : { def: "", type: "word" };
      if (hit.def) markSeenTerm(info.text);
      // miss 态徽标保持现状"划词"（CC 二审 RISK-6：不让 TYPE_CN 把它改名成"生词"）
      popover.innerHTML = popCardHTML(info.text, hit.def ? hit : { def: "", type: "word", badge: "划词" }, context);
    } else {
      selectionPassage = info.text;
      popover.innerHTML = `
        <div class="pop-head">
          <span class="pop-word pop-count">已选 ${info.words} 词 · ${info.chars} 字符</span>
          <span class="pop-type chunk">选段</span>
        </div>
        <button class="pop-ask" data-copy-passage="1">📋 复制整段 → 让 agent 精读</button>
        <div class="pop-sub">翻译 + 难词释义 + 长难句拆解，粘给本地 agent 即可</div>
      `;
    }
    document.body.appendChild(popover);
    positionPopover(popover, info.range);
  }

  function handleSelectionEnd(event) {
    if (event.target.closest?.(".term-popover, textarea, input, .player")) return;
    const info = selectionInfo();
    if (!info) return;
    if (info.words > SELECTION_WORD_CAP || info.chars > SELECTION_CHAR_CAP) {
      toast(`最多支持 ${SELECTION_WORD_CAP} 词，试着选短一点`);
      return;
    }
    showSelectionPopover(info);
  }

  /* ---------- basket ---------- */

  function addBasket(item) {
    state.basket.push({ ...item, ts: Date.now() });
    writeJSON(KEYS.basket, state.basket);
    updateBasketChip();
    renderBasket();
  }

  function updateBasketChip() {
    const chip = $("#basketChip");
    if (!chip) return;
    if (!state.basket.length) {
      chip.classList.add("hidden");
      chip.textContent = "0";
      return;
    }
    chip.classList.remove("hidden");
    chip.textContent = `🧺 ${state.basket.length}`;
  }

  function basketSegLabel(id) {
    const seg = data.segments.find(item => item.id === id);
    if (!seg) return id;
    const snippet = seg.en.length > 56 ? `${seg.en.slice(0, 56)}…` : seg.en;
    return `§${segmentNumber(id)} · ${snippet}`;
  }

  function renderBasket() {
    const block = $("#basketBlock");
    if (!block) return;
    if (!state.basket.length) {
      block.innerHTML = "";
      block.classList.add("hidden");
      return;
    }
    block.classList.remove("hidden");
    const words = state.basket.filter(item => item.type === "word");
    const segs = state.basket.filter(item => item.type === "seg");
    block.innerHTML = `
      <h2>问题筐</h2>
      <p class="block-sub">${state.basket.length} 个问题 · ${words.length} 词 + ${segs.length} 段 — 学习时不打断，学完一次性问 agent</p>
      <ul class="basket-list">${state.basket.map((item, idx) => `
        <li>
          <span class="b-type ${esc(item.type)}">${item.type === "word" ? "词" : "段"}</span>
          <span class="b-text">${esc(item.w || basketSegLabel(item.id))}</span>
          <button class="b-del" data-remove-basket="${idx}" title="移除" aria-label="移除">×</button>
        </li>
      `).join("")}</ul>
      <button class="primary-btn" id="copyBasket">📋 复制今日问题汇总 → 问 agent</button>
    `;
  }

  /* ---------- heat strip ---------- */

  function renderHeat() {
    const block = $("#heatBlock");
    if (!block) return;
    const vals = data.segments.map((_, i) => Number(state.plays[i]) || 0);
    const max = Math.max(...vals);
    if (!max) {
      block.innerHTML = "";
      block.classList.add("hidden");
      return;
    }
    block.classList.remove("hidden");
    block.innerHTML = `
      <h2>回访热力</h2>
      <p class="block-sub">颜色越深 = 重播越多 · 点一格直达该段复习</p>
      <div class="heat-strip">${vals.map((count, i) => `
        <button class="heat-cell" style="background:rgba(59,91,219,${(0.14 + 0.78 * (count / max)).toFixed(2)})" title="§${i + 1} · 播放 ${count} 次" data-jump="${esc(data.segments[i].id)}" aria-label="§${i + 1} 播放 ${count} 次"></button>
      `).join("")}</div>
    `;
  }

  /* ---------- recording (B1: memory-only, never persisted or uploaded) ---------- */

  async function startRecording(i) {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      toast("当前浏览器不支持录音");
      return;
    }
    if (state.dictI !== null) exitDictation(state.dictI);
    stopRecording();
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      toast("麦克风不可用 — 请检查浏览器权限（file:// 下需用 HTTP 打开）");
      return;
    }
    const chunks = [];
    const recorder = new MediaRecorder(stream);
    recorder.ondataavailable = event => {
      if (event.data && event.data.size) chunks.push(event.data);
    };
    recorder.onstop = () => {
      const old = state.recordings[i];
      if (old?.url) URL.revokeObjectURL(old.url);
      const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
      const url = URL.createObjectURL(blob);
      state.recordings[i] = { url, blob };
      stream.getTracks().forEach(track => track.stop());
      state.recording = null;
      state.counts[i] = (Number(state.counts[i]) || 0) + 1;
      writeJSON(KEYS.counts, state.counts);
      writeLast(i);
      renderRecordingControls(i);
      updateRecProgress();
    };
    recorder.start();
    const seg = document.querySelector(`.seg[data-i="${i}"]`);
    const slot = $(".train-slot", seg);
    slot.innerHTML = `
      <div class="recording-bar">
        <span class="rec-dot"></span>
        <span class="rec-label">录音中 — 跟着原音读这一段</span>
        <button class="pill-btn" data-stop-record="${i}">停止录音</button>
      </div>
    `;
    state.recording = recorder;
  }

  function stopRecording() {
    if (state.recording && state.recording.state !== "inactive") {
      state.recording.stop();
    }
  }

  function renderRecordingControls(i) {
    const seg = document.querySelector(`.seg[data-i="${i}"]`);
    const slot = $(".train-slot", seg);
    const count = Number(state.counts[i]) || 0;
    slot.innerHTML = `
      <div class="recording-bar">
        <span class="rec-label">第 ${count} 次跟读 ${count >= 3 ? "· 本段达标 ✓" : "· 3 次达标"}</span>
        <button class="pill-btn" data-play="${i}">▶ 原音</button>
        <button class="pill-btn" data-play-mine="${i}">🎙 我的</button>
        <button class="pill-btn" data-play-ab="${i}">🔁 交替对照</button>
        <button class="pill-btn ghost" data-record="${i}">再录一次</button>
      </div>
    `;
  }

  function playMine(i) {
    const rec = state.recordings[i];
    if (!rec) return;
    stopAudio();
    state.audio = new Audio(rec.url);
    state.audio.play();
  }

  function playAB(i) {
    playSeg(i, true);
    if (state.audio) state.audio.onended = () => playMine(i);
  }

  function updateRecProgress() {
    const el = $("#recProgress");
    if (!el) return;
    const done = data.segments.filter((_, i) => (Number(state.counts[i]) || 0) >= 3).length;
    const any = Object.keys(state.counts).length > 0;
    const hit = done === data.segments.length && done > 0;
    el.classList.toggle("hidden", !any);
    el.textContent = hit
      ? `🎙 ${done}/${data.segments.length} 段达标 · 可以写复述了`
      : `🎙 ${done}/${data.segments.length} 段达标`;
    el.classList.toggle("hit", hit);
  }

  /* ---------- dictation (B3) ---------- */

  function enterDictation(i) {
    if (state.blind) return;
    if (state.dictI !== null && state.dictI !== i) exitDictation(state.dictI);
    state.dictI = i;
    if (karaoke.segI === i) stopKaraoke();
    const seg = document.querySelector(`.seg[data-i="${i}"]`);
    const en = $(".en", seg);
    if (!en.dataset.original) en.dataset.original = en.innerHTML;
    en.innerHTML = `<textarea class="dict-input" placeholder="Type what you hear for this whole segment."></textarea>`;
    const slot = $(".train-slot", seg);
    slot.innerHTML = `
      <div class="dict-actions">
        <button class="pill-btn" data-check-dict="${i}">检查</button>
        <button class="pill-btn ghost" data-reveal-dict="${i}">揭原文</button>
        <span class="dict-hint">提示：先点本段 ▶ 听几遍再写 · Enter 检查 · Shift+Enter 换行 · Esc 退出</span>
      </div>
    `;
    const input = $(".dict-input", seg);
    input?.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        checkDictation(i);
      } else if (e.key === "Escape") {
        e.preventDefault();
        exitDictation(i);
      }
    });
    input?.focus();
  }

  function exitDictation(i) {
    const seg = document.querySelector(`.seg[data-i="${i}"]`);
    const en = $(".en", seg);
    if (en?.dataset.original) {
      en.innerHTML = en.dataset.original;
      delete en.dataset.original;
    }
    const slot = $(".train-slot", seg);
    if (slot) slot.innerHTML = "";
    if (state.dictI === i) state.dictI = null;
  }

  function checkDictation(i) {
    const segData = data.segments[i];
    const seg = document.querySelector(`.seg[data-i="${i}"]`);
    const input = $(".dict-input", seg)?.value || "";
    $(".train-slot", seg).innerHTML = `
      <p class="dict-note">按原文拼写为准；数字和缩写差异不计入学习判断。</p>
      <div class="dict-diff">${diffWords(input, segData.en)}</div>
      <div class="dict-actions">
        <button class="pill-btn" data-dict="${i}">再听写一次</button>
        <button class="pill-btn ghost" data-reveal-dict="${i}">揭原文</button>
      </div>
    `;
  }

  function diffWords(input, expected) {
    const a = input.trim().split(/\s+/).filter(Boolean);
    const b = expected.trim().split(/\s+/).filter(Boolean);
    const dp = Array.from({ length: a.length + 1 }, () => Array(b.length + 1).fill(0));
    for (let i = a.length - 1; i >= 0; i--) {
      for (let j = b.length - 1; j >= 0; j--) {
        dp[i][j] = normalize(a[i]) === normalize(b[j]) ? 1 + dp[i + 1][j + 1] : Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
    let i = 0, j = 0, out = [];
    while (i < a.length || j < b.length) {
      if (i < a.length && j < b.length && normalize(a[i]) === normalize(b[j])) {
        out.push(`<span>${esc(b[j])}</span>`);
        i++;
        j++;
      } else if (j < b.length && (i === a.length || dp[i][j + 1] >= (dp[i + 1]?.[j] || 0))) {
        out.push(`<span class="diff-add">${esc(b[j])}</span>`);
        j++;
      } else if (i < a.length) {
        out.push(`<span class="diff-del">${esc(a[i])}</span>`);
        i++;
      }
    }
    return out.join(" ");
  }

  function normalize(word) {
    return word.toLowerCase().replace(/[.,!?;:"'()]/g, "");
  }

  /* ---------- blind listening ---------- */

  function fmtDuration(sec) {
    const s = Math.round(sec);
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }

  let durationRefresh = null;
  function loadDurations() {
    data.segments.forEach((seg, i) => {
      if (state.durations[i] || audioStatus.missing.includes(seg.id)) return;
      const probe = new Audio(audioSrc(i));
      probe.preload = "metadata";
      probe.onloadedmetadata = () => {
        state.durations[i] = probe.duration;
        clearTimeout(durationRefresh);
        durationRefresh = setTimeout(() => {
          if (state.blind) renderBlindGrid();
        }, 120);
      };
    });
  }

  function enterBlind() {
    if (state.dictI !== null) exitDictation(state.dictI);
    closePopovers();
    state.blind = true;
    loadDurations();
    document.body.classList.add("blind");
    $("#revealBtn").classList.remove("hidden");
    $("#zhBtn").classList.add("hidden");
    renderBlindGrid();
    playSeg(0, true);
  }

  function exitBlind() {
    state.blind = false;
    document.body.classList.remove("blind");
    $("#revealBtn").classList.add("hidden");
    $("#zhBtn").classList.remove("hidden");
    $("#blindGrid").classList.add("hidden");
    stopAudio();
  }

  function renderBlindGrid() {
    const grid = $("#blindGrid");
    if (!grid) return;
    grid.classList.remove("hidden");
    const done = state.blindPlayed.size;
    grid.innerHTML = `
      <div class="blind-head">
        <span class="blind-title">盲听模式</span>
        <span class="blind-sub">不看文本听全篇，听完一段自动播下一段 · 已听 ${done}/${data.segments.length}</span>
      </div>
      <div class="blind-chips">${data.segments.map((seg, i) => {
        const cls = [
          "blind-chip",
          i === state.cur ? "current" : "",
          state.blindPlayed.has(i) ? "done" : ""
        ].filter(Boolean).join(" ");
        const label = state.blindPlayed.has(i) ? "✓" : `§${i + 1}`;
        const dur = state.durations[i];
        const chipTitle = dur ? `§${i + 1} · ${fmtDuration(dur)}` : `§${i + 1}`;
        return `<button class="${cls}" title="${chipTitle}" data-blind-play="${i}">${label}</button>`;
      }).join("")}</div>
    `;
  }

  function renderBlindComplete() {
    const grid = $("#blindGrid");
    if (!grid || $("#blindDoneReveal")) return;
    grid.insertAdjacentHTML("beforeend", `<button class="primary-btn reveal-all" id="blindDoneReveal">🎉 全部听完 — 揭晓全文</button>`);
  }

  /* ---------- reset / navigation ---------- */

  function resetLesson() {
    // ir_ui (旧图标发现性标记) 一并清掉, 兼容老页面残留
    [KEYS.counts, KEYS.out, KEYS.transfer, KEYS.week, KEYS.last, KEYS.basket, KEYS.seen, KEYS.plays, "ir_ui"].forEach(key => localStorage.removeItem(key));
    location.reload();
  }

  function jumpToSegment(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.add("jump-highlight");
    setTimeout(() => el.classList.remove("jump-highlight"), 1400);
  }

  /* ---------- ambience: entrance stagger + halo ---------- */

  function observeFadeIns() {
    const els = $$(".study-card, .seg, .learning-block");
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced || !("IntersectionObserver" in window)) {
      els.forEach(el => el.classList.add("in"));
      return;
    }
    const io = new IntersectionObserver(entries => {
      entries.filter(entry => entry.isIntersecting).forEach((entry, k) => {
        const el = entry.target;
        io.unobserve(el);
        setTimeout(() => el.classList.add("in"), Math.min(k * 70, 420));
      });
    }, { threshold: 0.06 });
    els.forEach(el => io.observe(el));
  }

  function startHalo() {
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const canvas = document.getElementById("halo");
    if (!canvas || !canvas.getContext) return;
    const ctx = canvas.getContext("2d");
    let W, H;
    const size = () => {
      W = canvas.width = window.innerWidth;
      H = canvas.height = Math.min(window.innerHeight, 720);
    };
    size();
    window.addEventListener("resize", size);
    const blobs = [
      { x: .2, y: .2, r: 230, c: "59,91,219", a: .10, dx: .00006, dy: .00009 },
      { x: .8, y: .15, r: 200, c: "194,65,12", a: .07, dx: -.00007, dy: .00006 },
      { x: .6, y: .35, r: 260, c: "21,128,61", a: .06, dx: .00005, dy: -.00008 }
    ];
    let tlast = null;
    const draw = ts => {
      if (tlast === null) tlast = ts;
      const dt = Math.min(ts - tlast, 50);
      tlast = ts;
      ctx.clearRect(0, 0, W, H);
      blobs.forEach(b => {
        b.x += b.dx * dt;
        b.y += b.dy * dt;
        if (b.x < .05 || b.x > .95) b.dx *= -1;
        if (b.y < .05 || b.y > .55) b.dy *= -1;
        const g = ctx.createRadialGradient(b.x * W, b.y * H, 0, b.x * W, b.y * H, b.r);
        g.addColorStop(0, `rgba(${b.c},${b.a})`);
        g.addColorStop(1, `rgba(${b.c},0)`);
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(b.x * W, b.y * H, b.r, 0, 7);
        ctx.fill();
      });
      requestAnimationFrame(draw);
    };
    requestAnimationFrame(draw);
  }

  /* ---------- prefs & events ---------- */

  function applyInitialPrefs() {
    const zhBtn = $("#zhBtn");
    if (localStorage.getItem(KEYS.zh) === "0") {
      document.body.classList.add("hide-zh");
    } else if (zhBtn) {
      zhBtn.classList.add("on");
    }
    const fs = localStorage.getItem(KEYS.fs);
    if (fs) document.documentElement.style.setProperty("--fs", `${fs}px`);
    $$(".rate").forEach(btn => btn.classList.toggle("on", parseFloat(btn.dataset.rate) === state.rate));
    updateRecProgress();
  }

  function flashSaved(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = "已自动保存 ✓";
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.textContent = ""; }, 1200);
  }

  function markContext(mark) {
    const segEl = mark.closest(".seg");
    if (segEl) return data.segments[Number(segEl.dataset.i)].en;
    return mark.textContent;
  }

  function bindBaseEvents() {
    document.addEventListener("click", handleWordSeekClick);
    document.addEventListener("click", event => {
      const raw = event.target;
      if (!raw || !raw.closest) return;
      const mark = raw.closest("mark.hl[data-term]");
      const target = raw.closest("button");
      // a live selection means the mouseup handler just opened the selection
      // popover; closing here would kill it before the user can click it
      const hasSelection = !!String(window.getSelection() || "").trim();
      if (!mark && !hasSelection && !raw.closest(".term-popover") && !(target && target.dataset.chunk)) closePopovers();
      if (mark) {
        showTermPopover(mark, mark.dataset.term, markContext(mark));
        return;
      }
      if (!target) return;

      const speakBtn = event.target.closest("[data-speak]");
      if (speakBtn) {
        playWordAudio(speakBtn.dataset.speak);
        return;
      }
      const segLink = event.target.closest("[data-jump-seg]");
      if (segLink) {
        closePopovers();
        const target = document.querySelector(`.seg[data-i="${segLink.dataset.jumpSeg}"]`);
        target?.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }

      if (target.dataset.play) playSeg(Number(target.dataset.play));
      if (target.dataset.read) {
        const i = Number(target.dataset.read);
        playSegSlow(i);
        writeLast(i);
      }
      if (target.dataset.confuse) {
        const i = Number(target.dataset.confuse);
        addBasket({ type: "seg", id: data.segments[i].id });
        copyText(askSegPrompt(i), target).then(() => toast("已复制拆解 prompt · 已加入问题筐"));
      }
      if (target.dataset.term) {
        const term = target.dataset.term;
        const context = target.closest(".seg")?.innerText.slice(0, 280) || "";
        showTermPopover(target, term, context);
      }
      if (target.dataset.chunk) {
        const term = target.dataset.chunk;
        const chunk = (data.chunks || []).find(item => item.t === term);
        showTermPopover(target, term, chunk ? chunk.eg : target.innerText);
      }
      if (target.dataset.copyWord) {
        const term = target.dataset.copyWord;
        const context = target.dataset.copyContext || "";
        addBasket({ type: "word", w: term, ctx: context });
        copyText(askWordPrompt(term, context), target).then(() => toast("已复制，去粘给你的 agent · 已加入问题筐"));
      }
      if (target.dataset.copyPassage) {
        copyText(askPassagePrompt(selectionPassage), target).then(() => toast("已复制整段精读 prompt，去粘给你的 agent"));
      }
      if (target.dataset.jump) jumpToSegment(target.dataset.jump);
      if (target.dataset.blindPlay) playSeg(Number(target.dataset.blindPlay), true);
      if (target.dataset.record) startRecording(Number(target.dataset.record));
      if (target.dataset.stopRecord) stopRecording();
      if (target.dataset.playMine) playMine(Number(target.dataset.playMine));
      if (target.dataset.playAb) playAB(Number(target.dataset.playAb));
      if (target.dataset.dict) enterDictation(Number(target.dataset.dict));
      if (target.dataset.checkDict) checkDictation(Number(target.dataset.checkDict));
      if (target.dataset.revealDict) exitDictation(Number(target.dataset.revealDict));
      if (target.dataset.removeBasket) {
        state.basket.splice(Number(target.dataset.removeBasket), 1);
        writeJSON(KEYS.basket, state.basket);
        updateBasketChip();
        renderBasket();
      }
      if (target.classList.contains("day")) {
        const day = Number(target.dataset.day);
        const week = readJSON(KEYS.week, []);
        const next = week.includes(day) ? week.filter(d => d !== day) : [...week, day];
        writeJSON(KEYS.week, next);
        target.classList.toggle("on", next.includes(day));
      }
      if (target.id === "startBlind") enterBlind();
      if (target.id === "revealBtn" || target.id === "blindDoneReveal") exitBlind();
      if (target.id === "resetBtn") resetLesson();
      if (target.id === "basketChip") $("#basketBlock")?.scrollIntoView({ behavior: "smooth" });
      if (target.id === "copyBasket") copyText(basketPrompt(), target);
      if (target.id === "copyRetell") {
        const text = localStorage.getItem(KEYS.out) || "";
        if (!text.trim()) {
          toast("先在上面写下你的英文复述");
          $("#retellInput")?.focus();
        } else {
          copyText(retellPrompt(), target).then(() => toast("批改 prompt 已复制"));
        }
      }
      if (target.id === "copyTransfer") {
        const text = localStorage.getItem(KEYS.transfer) || "";
        if (!text.trim()) {
          toast("先在上面写下你的迁移输出");
          $("#transferInput")?.focus();
        } else {
          copyText(transferPrompt(), target).then(() => toast("批改 prompt 已复制"));
        }
      }
      if (target.classList.contains("rate")) {
        state.rate = parseFloat(target.dataset.rate);
        localStorage.setItem(KEYS.rate, String(state.rate));
        if (state.audio) state.audio.playbackRate = state.rate;
        $$(".rate").forEach(btn => btn.classList.toggle("on", btn === target));
      }
      if (target.id === "playBtn") {
        if (state.audio && !state.audio.paused && state.audio.src) {
          state.audio.pause();
          setPlayIcon(false);
        } else if (state.audio && state.audio.paused && state.audio.src) {
          state.audio.play().catch(() => {});
          setPlayIcon(true);
        } else {
          playSeg(state.cur >= 0 ? state.cur : 0);
        }
      }
      if (target.id === "prevBtn") playSeg(Math.max(0, state.cur - 1));
      if (target.id === "nextBtn") playSeg(Math.min(data.segments.length - 1, state.cur + 1));
      if (target.id === "abBtn") cycleAB();
    });

    document.addEventListener("mouseup", handleSelectionEnd);

    document.addEventListener("keydown", event => {
      if ((event.key === "Enter" || event.key === " ") && event.target.matches?.("mark.hl[data-term]")) {
        event.preventDefault();
        event.target.click();
      }
      if (event.key === "Escape" && document.querySelector(".term-popover")) closePopovers();
    });

    window.addEventListener("scroll", closePopovers, { passive: true });

    $("#zhBtn").addEventListener("click", () => {
      const hidden = document.body.classList.toggle("hide-zh");
      $("#zhBtn").classList.toggle("on", !hidden);
      localStorage.setItem(KEYS.zh, hidden ? "0" : "1");
    });

    $("#fsUp").addEventListener("click", () => adjustFont(1));
    $("#fsDown").addEventListener("click", () => adjustFont(-1));
    $("#retellInput").value = localStorage.getItem(KEYS.out) || "";
    $("#retellInput").addEventListener("input", event => {
      localStorage.setItem(KEYS.out, event.target.value);
      flashSaved("retellSaved");
    });
    const transfer = $("#transferInput");
    if (transfer) {
      transfer.value = localStorage.getItem(KEYS.transfer) || "";
      transfer.addEventListener("input", event => {
        localStorage.setItem(KEYS.transfer, event.target.value);
        flashSaved("transferSaved");
      });
    }
  }

  function adjustFont(delta) {
    const current = parseInt(localStorage.getItem(KEYS.fs) || "20", 10);
    const next = Math.max(16, Math.min(24, current + delta));
    localStorage.setItem(KEYS.fs, String(next));
    document.documentElement.style.setProperty("--fs", `${next}px`);
  }

  window.ImmersionReader = {
    data,
    state,
    KEYS,
    render,
    readJSON,
    writeJSON,
    playSeg,
    startRecording,
    stopRecording,
    renderRecordingControls,
    enterDictation,
    exitDictation,
    diffWords,
    enterBlind,
    exitBlind,
    askSegPrompt,
    basketPrompt,
    retellPrompt,
    transferPrompt
  };
  console.log(
    "%c📖 Immersion Reader%c compiled from segments.json — poke around: window.ImmersionReader",
    "color:#3b5bdb;font-weight:700",
    "color:inherit"
  );
  render();
})();
