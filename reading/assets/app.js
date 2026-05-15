const minRevealMs = 1000;
const maxRevealMs = 3600;
const speedStepMin = -5;
const speedStepMax = 5;
const speedStepFactor = 0.12;

const corpusUrl = './corpus.json';
const chineseSegmenter =
  typeof Intl !== 'undefined' && typeof Intl.Segmenter === 'function'
    ? new Intl.Segmenter('zh', { granularity: 'word' })
    : null;

const punctuationTokenRE = /^[，。；！？、：,.!?;:（）()《》「」『』【】\[\]“”"'‘’—…]+$/;
const sentencePunctuationRE = /[。！？!?；;]/;
const softPunctuationRE = /[，、：,:]/;
const quotePunctuationRE = /[“”"'‘’（）()《》「」『』【】\[\]]/;
const blinkingTailPunctuationRE = /[、，。！？!?]/;
const pairedOpenToClose = new Map([
  ['（', '）'],
  ['(', ')'],
  ['【', '】'],
  ['《', '》'],
  ['「', '」'],
  ['『', '』'],
  ['“', '”'],
  ['‘', '’'],
]);
const pairedCloseSet = new Set(pairedOpenToClose.values());

const state = {
  entries: [],
  index: 0,
  speedStep: 0,
  paused: false,
  originalProgress: 0,
  runId: 0,
  autoScrollTimer: 0,
  lastScrollY: 0,
  userScrolled: false,
  immersiveBound: false,
};

const el = {
  source: document.getElementById('source'),
  stageLabel: document.getElementById('stageLabel'),
  progressFill: document.getElementById('progressFill'),
  content: document.getElementById('content'),
  original: document.getElementById('original'),
  prev: document.getElementById('prev'),
  center: document.getElementById('center'),
  next: document.getElementById('next'),
  slow: document.getElementById('slow'),
  fast: document.getElementById('fast'),
  count: document.getElementById('count'),
};

function normalizeEntry(raw) {
  const content = (raw?.original || raw?.content || '').trim();
  const source = (raw?.source || '').trim();
  return {
    id: String(raw?.id ?? raw?.unified_id ?? raw?.统一ID ?? raw?.original_id ?? ''),
    source,
    original: content,
    light_explanation: (raw?.light_explanation || '').trim(),
    deep_explanation: (raw?.deep_explanation || '').trim(),
  };
}

function splitIntoChunks(text) {
  const clean = String(text || '').replace(/\s+/g, ' ').trim();
  if (!clean) return [];

  const shortChunkThreshold = 10;
  const targetChunkChars = 12;
  const maxChunkChars = 18;

  if ([...clean].length <= shortChunkThreshold) {
    return [clean];
  }

  const chars = [...clean];
  const tokens = [];
  const sentences = [];

  function pushChineseBlock(block) {
    if (!block) return;
    if (chineseSegmenter) {
      for (const item of chineseSegmenter.segment(block)) {
        const seg = String(item.segment || '').trim();
        if (seg) tokens.push(seg);
      }
      return;
    }

    const fallback = block.match(/[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*|[^\sA-Za-z0-9]/g) || [];
    for (const seg of fallback) {
      if (seg.trim()) tokens.push(seg);
    }
  }

  let i = 0;
  while (i < chars.length) {
    const char = chars[i];

    if (/\s/.test(char)) {
      i += 1;
      continue;
    }

    if (punctuationTokenRE.test(char)) {
      tokens.push(char);
      i += 1;
      continue;
    }

    if (/[A-Za-z0-9]/.test(char)) {
      let j = i + 1;
      while (j < chars.length && /[A-Za-z0-9\-']/.test(chars[j])) j += 1;
      tokens.push(chars.slice(i, j).join(''));
      i = j;
      continue;
    }

    let j = i + 1;
    while (
      j < chars.length &&
      !/\s/.test(chars[j]) &&
      !punctuationTokenRE.test(chars[j]) &&
      !/[A-Za-z0-9]/.test(chars[j])
    ) {
      j += 1;
    }
    pushChineseBlock(chars.slice(i, j).join(''));
    i = j;
  }

  function visibleLen(token) {
    return [...String(token || '').replace(/\s+/g, '')].length;
  }

  function isSentenceEndToken(token) {
    return /^[。！？!?]+$/.test(String(token || '').trim());
  }

  for (const token of tokens) {
    if (!token) continue;
    const currentSentence = sentences.length ? sentences[sentences.length - 1] : null;
    if (!currentSentence || currentSentence.closed) {
      sentences.push({ tokens: [token], closed: isSentenceEndToken(token) });
      continue;
    }
    currentSentence.tokens.push(token);
    if (isSentenceEndToken(token)) {
      currentSentence.closed = true;
    }
  }

  const chunks = [];

  function chunkSentenceTokens(sentenceTokens) {
    const sentenceChunks = [];
    let buffer = '';
    let pendingPrefix = '';

    function flushLocalBuffer() {
      const chunk = buffer.trim();
      if (chunk) sentenceChunks.push(chunk);
      buffer = '';
    }

    for (const token of sentenceTokens) {
      if (!token) continue;
      const text = String(token || '').trim();
      if (!text) continue;

      if (punctuationTokenRE.test(text)) {
        if (buffer) {
          buffer += text;
          flushLocalBuffer();
        } else if (sentenceChunks.length) {
          sentenceChunks[sentenceChunks.length - 1] += text;
        } else {
          pendingPrefix += text;
        }
        continue;
      }

      if (pendingPrefix) {
        buffer += pendingPrefix;
        pendingPrefix = '';
      }
      buffer += text;
    }

    flushLocalBuffer();
    if (pendingPrefix) sentenceChunks.push(pendingPrefix);
    return mergePairedChunks(sentenceChunks.filter(Boolean));
  }

  for (const sentence of sentences) {
    chunks.push(...chunkSentenceTokens(sentence.tokens));
  }

  return chunks.filter(Boolean);
}

function mergePairedChunks(chunks) {
  const merged = [];
  let pendingPrefix = '';

  function isOpen(token) {
    return pairedOpenToClose.has(token);
  }

  function isChunkPunctuation(token) {
    return punctuationTokenRE.test(String(token || '').trim());
  }

  for (const token of chunks) {
    const text = String(token || '').trim();
    if (!text) continue;

    if (isChunkPunctuation(text)) {
      if (isOpen(text)) {
        pendingPrefix += text;
        continue;
      }
      if (merged.length) {
        merged[merged.length - 1] += text;
      } else {
        pendingPrefix += text;
      }
      continue;
    }

    merged.push(`${pendingPrefix}${text}`);
    pendingPrefix = '';
  }

  return merged.filter(Boolean);
}

function clearTimers() {
  for (const id of state.timers || []) {
    window.clearTimeout(id);
  }
  state.timers = [];
}

function stopAutoScroll() {
  if (state.autoScrollTimer) {
    window.cancelAnimationFrame(state.autoScrollTimer);
    state.autoScrollTimer = 0;
  }
}

function scheduleAutoScroll() {
  stopAutoScroll();
  state.autoScrollTimer = window.requestAnimationFrame(() => {
    state.autoScrollTimer = 0;
    const pane = el.content;
    if (!pane) return;
    const viewportHeight = pane.clientHeight;
    const remaining = Math.max(0, pane.scrollHeight - (pane.scrollTop + viewportHeight));
    const baseStep = Math.max(28, Math.round(viewportHeight * 0.08));
    const edgeBonus = remaining < viewportHeight * 0.2 ? Math.round(viewportHeight * 0.06) : 0;
    const target = Math.min(remaining, baseStep + edgeBonus);
    if (target > 0) {
      pane.scrollBy({ top: target, behavior: 'smooth' });
    }
  });
}

function installScrollTracking() {
  const pane = el.content;
  if (!pane) return;
  state.lastScrollY = pane.scrollTop || 0;
  pane.addEventListener(
    'scroll',
    () => {
      const y = pane.scrollTop || 0;
      if (Math.abs(y - state.lastScrollY) > 12) {
        state.userScrolled = true;
        state.lastScrollY = y;
      }
    },
    { passive: true }
  );
}

function maybeEnterFullscreen() {
  if (!window.matchMedia('(max-width: 720px)').matches) return;
  if (state.immersiveBound) return;
  state.immersiveBound = true;

  const attemptFullscreen = async () => {
    try {
      if (document.fullscreenElement || !document.documentElement.requestFullscreen) return;
      await document.documentElement.requestFullscreen({ navigationUI: 'hide' });
    } catch {
      // Browsers may block fullscreen without a user gesture or on iOS Safari.
    }
  };

  const onFirstGesture = () => {
    attemptFullscreen();
    document.removeEventListener('touchend', onFirstGesture);
    document.removeEventListener('pointerdown', onFirstGesture);
  };

  document.addEventListener('touchend', onFirstGesture, { passive: true, once: true });
  document.addEventListener('pointerdown', onFirstGesture, { passive: true, once: true });
}

function wait(ms, runId) {
  return new Promise((resolve) => {
    let remaining = ms;
    let last = performance.now();

    const tick = () => {
      if (runId !== state.runId) return;
      if (state.paused) {
        last = performance.now();
        const pausedId = window.setTimeout(tick, 80);
        (state.timers || (state.timers = [])).push(pausedId);
        return;
      }

      const now = performance.now();
      remaining -= now - last;
      last = now;

      if (remaining <= 0) {
        resolve();
        return;
      }

      const id = window.setTimeout(tick, Math.min(80, remaining));
      (state.timers || (state.timers = [])).push(id);
    };

    tick();
  });
}

function setSpeed(mode) {
  state.speedStep = Math.max(speedStepMin, Math.min(speedStepMax, state.speedStep + mode));
  updateSpeedUI();
}

function getSpeedMultiplier() {
  if (state.speedStep === 0) return 1;
  if (state.speedStep > 0) {
    return Math.max(0.5, Math.pow(1 - speedStepFactor, state.speedStep));
  }
  return Math.min(1.7, Math.pow(1 + speedStepFactor, Math.abs(state.speedStep)));
}

function updateSpeedUI() {
  if (!el.slow && !el.fast) return;
  const currentMultiplier = getSpeedMultiplier();
  if (el.slow) {
    el.slow.classList.toggle('active', state.speedStep < 0);
    el.slow.setAttribute('aria-label', `减慢，当前倍率 ${currentMultiplier.toFixed(2)}x`);
  }
  if (el.fast) {
    el.fast.classList.toggle('active', state.speedStep > 0);
    el.fast.setAttribute('aria-label', `加快，当前倍率 ${currentMultiplier.toFixed(2)}x`);
  }
}

function syncPauseUI() {
  el.center.classList.toggle('active', state.paused);
  el.center.textContent = '⏯';
  el.center.setAttribute('aria-label', state.paused ? '继续' : '暂停');
  document.querySelectorAll('.reveal, .tail-punctuation, .chunk.punctuation.blink').forEach((node) => {
    node.style.animationPlayState = state.paused ? 'paused' : 'running';
  });
}

function currentEntry() {
  return state.entries[state.index];
}

function updateMeta() {
  const total = state.entries.length || 1;
  const entry = currentEntry() || {};
  if (el.count) {
    el.count.textContent = `${state.index + 1} / ${total}`;
  }
  el.source.textContent = entry.source || '暂无语料';
  if (el.title) {
    el.title.textContent = entry.id || '';
  }
  el.stageLabel.textContent = '原文';
  if (el.stageHint) {
    if (state.originalProgress <= 0) {
      el.stageHint.textContent = '原文自动渐显';
    } else if (state.originalProgress < 0.7) {
      el.stageHint.textContent = `已读 ${Math.round(state.originalProgress * 100)}%，读到七成后可前后切换`;
    } else if (state.originalProgress < 1) {
      el.stageHint.textContent = '可以前后切换';
    } else {
      el.stageHint.textContent = '本段已读完';
    }
  }
}

function updateProgress() {
  el.progressFill.style.width = `${Math.max(2, Math.round(state.originalProgress * 100))}%`;
}

function setNavigationState() {
  const canNavigate = state.originalProgress >= 0.7;
  const canGoPrev = canNavigate && state.index > 0;
  const canGoNext = canNavigate && state.index < state.entries.length - 1;
  el.prev.disabled = !canGoPrev;
  el.next.disabled = !canGoNext;
}

function resetContainers() {
  el.original.innerHTML = '';
  if (el.content) {
    el.content.scrollTop = 0;
  }
}

function clearBlinkingPunctuation(container) {
  container.querySelectorAll('.blink').forEach((node) => node.classList.remove('blink'));
}

function appendChunk(container, chunk, speedClass = 'soft', durationMultiplier = 1) {
  const span = document.createElement('span');
  span.className = isPunctuationChunk(chunk) ? 'chunk punctuation' : `chunk reveal ${speedClass}`;
  const charCount = [...String(chunk || '').replace(/\s+/g, '')].length || 1;
  const duration = getRevealDuration(chunk, charCount, durationMultiplier);
  const { body, tail, suffix } = splitBlinkingTail(chunk);

  if (isPunctuationChunk(chunk)) {
    span.textContent = chunk;
  } else if (tail) {
    span.append(document.createTextNode(body));
    const tailSpan = document.createElement('span');
    tailSpan.className = 'tail-punctuation';
    tailSpan.textContent = tail;
    span.appendChild(tailSpan);
    if (suffix) {
      span.appendChild(document.createTextNode(suffix));
    }
    span.style.setProperty('--reveal-duration', `${duration}ms`);
  } else {
    span.textContent = chunk;
    span.style.setProperty('--reveal-duration', `${duration}ms`);
  }
  container.appendChild(span);
  scheduleAutoScroll();
  return duration;
}

function splitBlinkingTail(chunk) {
  const text = String(chunk || '');
  const match = text.match(/^(.*?)([、，。！？!?]+)([”"’'）)\]】》」』]*?)$/);
  if (!match) {
    return { body: text, tail: '', suffix: '' };
  }
  if (!blinkingTailPunctuationRE.test(match[2].slice(-1))) {
    return { body: text, tail: '', suffix: '' };
  }
  return {
    body: match[1],
    tail: match[2],
    suffix: match[3] || '',
  };
}

function getRevealDuration(chunk, charCount, durationMultiplier = 1) {
  if (isPunctuationChunk(chunk)) {
    return Math.max(90, Math.round(100 * durationMultiplier));
  }
  const length = Math.max(1, charCount);
  const base = 1700 + Math.min(1900, length * 145);
  const speedMultiplier = getSpeedMultiplier();
  return Math.max(
    minRevealMs,
    Math.min(maxRevealMs, Math.round(base * speedMultiplier * durationMultiplier * 2))
  );
}

function getChunkPause(chunk, duration) {
  const tail = String(chunk || '').trim().slice(-1);
  const speedMultiplier = getSpeedMultiplier();
  if (/[。！？!?]/.test(tail)) {
    return Math.max(180, Math.round(Math.max(260, duration * 0.45) * speedMultiplier));
  }
  if (/、/.test(tail)) {
    return Math.max(18, Math.round(35 * speedMultiplier));
  }
  if (/[，：,:；;]/.test(tail)) {
    return Math.max(28, Math.round(60 * speedMultiplier));
  }
  if (quotePunctuationRE.test(tail)) {
    return Math.max(20, Math.round(40 * speedMultiplier));
  }
  return 0;
}

async function revealChunks(container, chunks, runId, speedClass = 'soft', progressMode = null) {
  let openingSentence = true;
  for (let i = 0; i < chunks.length; i += 1) {
    if (runId !== state.runId) return false;
    const chunk = chunks[i];
    const isFinalChunk = i === chunks.length - 1;
    clearBlinkingPunctuation(container);
    const duration = appendChunk(container, chunk, speedClass, openingSentence ? 3 : 1);
    const lastVisible = container.lastElementChild;
    if (lastVisible && !isFinalChunk) {
      const tail = lastVisible.querySelector('.tail-punctuation');
      if (tail) {
        tail.classList.add('blink');
      } else if (isPunctuationChunk(chunk) && blinkingTailPunctuationRE.test(String(chunk || '').trim().slice(-1))) {
        lastVisible.classList.add('blink');
      }
    }
    if (progressMode === 'original') {
      state.originalProgress = (i + 1) / chunks.length;
      updateMeta();
      updateProgress();
      setNavigationState();
    }
    await wait(duration + getChunkPause(chunk, duration), runId);
    if (openingSentence) {
      openingSentence = false;
    }
  }
  return runId === state.runId;
}

function isPunctuationChunk(chunk) {
  return /^[，。；！？、：,.!?;:（）()《》「」『』【】\[\]“”"'‘’—…]+$/.test(String(chunk || '').trim());
}

async function startEntry(index) {
  if (index < 0 || index >= state.entries.length) return;
  state.runId += 1;
  const runId = state.runId;
  clearTimers();
  stopAutoScroll();
  state.index = index;
  state.originalProgress = 0;
  resetContainers();
  updateMeta();
  updateProgress();
  setNavigationState();

  const entry = currentEntry();
  const originalChunks = splitIntoChunks(entry.original || '');

  el.prev.disabled = index === 0;
  el.next.disabled = true;

  await revealChunks(el.original, originalChunks, runId, 'soft', 'original');
  scheduleAutoScroll();
}

function canAdvance() {
  return state.originalProgress >= 0.7 && state.index < state.entries.length - 1;
}

function bindEvents() {
  el.prev.addEventListener('click', async () => {
    if (state.index <= 0 || state.originalProgress < 0.7) return;
    await startEntry(state.index - 1);
  });

  el.next.addEventListener('click', async () => {
    if (!canAdvance()) return;
    await startEntry(state.index + 1);
  });

  el.center.addEventListener('click', async () => {
    state.paused = !state.paused;
    syncPauseUI();
  });

  if (el.slow) {
    el.slow.addEventListener('click', () => setSpeed(-1));
  }
  if (el.fast) {
    el.fast.addEventListener('click', () => setSpeed(1));
  }
}

async function loadCorpus() {
  const response = await fetch(corpusUrl, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Failed to load corpus: ${response.status}`);
  }
  const data = await response.json();
  state.entries = Array.isArray(data) ? data.map(normalizeEntry).filter((item) => item.original) : [];
}

async function init() {
  bindEvents();
  installScrollTracking();
  maybeEnterFullscreen();
  updateSpeedUI();
  syncPauseUI();
  await loadCorpus();
  if (!state.entries.length) {
    el.source.textContent = '暂无语料';
    if (el.title) {
      el.title.textContent = '请检查 corpus.json';
    }
    el.stageLabel.textContent = '就绪';
    if (el.stageHint) {
      el.stageHint.textContent = '';
    }
    el.prev.disabled = true;
    el.next.disabled = true;
    return;
  }
  await startEntry(0);
}

init().catch((error) => {
  console.error(error);
  el.source.textContent = '加载失败';
  if (el.title) {
    el.title.textContent = '无法读取 corpus.json';
  }
  el.stageLabel.textContent = '错误';
  if (el.stageHint) {
    el.stageHint.textContent = String(error.message || error);
  }
});
