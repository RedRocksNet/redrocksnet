const minRevealMs = 300;
const maxRevealMs = 2600;
const fadeDurationMs = window.matchMedia('(max-width: 720px)').matches ? 1000 : 5000;
const navigationDelayMs = 3000;
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
const blinkingTailPunctuationRE = /$^/;
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

function visibleChars(text) {
  return [...String(text || '').replace(/\s+/g, '')].length;
}

function getChunkText(chunk) {
  if (chunk && typeof chunk === 'object' && 'text' in chunk) {
    return String(chunk.text || '');
  }
  return String(chunk || '');
}

function getChunkKind(chunk) {
  if (chunk && typeof chunk === 'object' && 'kind' in chunk) {
    return String(chunk.kind || '');
  }
  return '';
}

function isOpeningPunctuationToken(token) {
  return pairedOpenToClose.has(String(token || '').trim());
}

function collapseShortPairedRuns(tokens) {
  const output = [];
  for (let i = 0; i < tokens.length; i += 1) {
    const token = String(tokens[i] || '').trim();
    if (!token) continue;
    if (!pairedOpenToClose.has(token)) {
      output.push(token);
      continue;
    }

    let depth = 1;
    let j = i + 1;
    while (j < tokens.length) {
      const current = String(tokens[j] || '').trim();
      if (!current) {
        j += 1;
        continue;
      }
      if (pairedOpenToClose.has(current)) {
        depth += 1;
      } else if (pairedCloseSet.has(current)) {
        depth -= 1;
        if (depth === 0) break;
      }
      j += 1;
    }

    if (depth === 0) {
      const slice = tokens.slice(i, j + 1).map((item) => String(item || '').trim()).filter(Boolean);
      const innerVisible = slice.slice(1, -1).reduce((sum, item) => sum + visibleChars(item), 0);
      if (innerVisible <= 6) {
        output.push(slice.join(''));
      } else {
        output.push(...slice);
      }
      i = j;
      continue;
    }

    output.push(token);
  }
  return output;
}

function segmentTextUnits(text) {
  const clean = String(text || '').trim();
  if (!clean) return [];
  if (chineseSegmenter) {
    const units = [];
    for (const item of chineseSegmenter.segment(clean)) {
      const seg = String(item.segment || '').trim();
      if (seg) units.push(seg);
    }
    return units;
  }
  return clean.match(/[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*|[^\sA-Za-z0-9]/g) || [];
}

function splitBalancedText(text, options = {}) {
  const clean = String(text || '').trim();
  if (!clean) return [];

  const threshold = options.threshold ?? 18;
  const minChunk = options.minChunk ?? 8;
  const maxChunk = options.maxChunk ?? 24;
  const units = segmentTextUnits(clean);
  const totalLen = visibleChars(clean);

  if (totalLen <= threshold || units.length <= 1) {
    return [clean];
  }

  const unitData = units.map((unit) => ({
    text: unit,
    len: visibleChars(unit),
  }));

  function isSemanticBridge(token) {
    return /^(的|了|在|把|被|和|与|及|并|而|但|然而|所以|因此|因为|如果|虽然|以及|或者|其中|同时|于是|就是|也|都|还|更|再|仍|又|且|就|却|而且|只是|不过)$/.test(
      String(token || '').trim()
    );
  }

  function splitRange(start, end) {
    const slice = unitData.slice(start, end);
    const sliceLen = slice.reduce((sum, item) => sum + item.len, 0);

    if (sliceLen <= maxChunk || slice.length <= 1) {
      return [slice.map((item) => item.text).join('')];
    }

    let bestIndex = -1;
    let bestScore = Infinity;
    let leftLen = 0;

    for (let i = start + 1; i < end; i += 1) {
      leftLen += unitData[i - 1].len;
      const rightLen = sliceLen - leftLen;
      let score = Math.abs(leftLen - rightLen);

      if (leftLen < minChunk || rightLen < minChunk) {
        score += 1000;
      }

      const prevText = unitData[i - 1].text;
      const nextText = unitData[i].text;
      if (pairedOpenToClose.has(prevText) || pairedCloseSet.has(nextText)) {
        score += 120;
      }

      if (isSemanticBridge(prevText)) {
        score -= 6;
      }
      if (isSemanticBridge(nextText)) {
        score -= 3;
      }

      if (score < bestScore) {
        bestScore = score;
        bestIndex = i;
      }
    }

    if (bestIndex <= start || bestIndex >= end) {
      return [slice.map((item) => item.text).join('')];
    }

    const left = splitRange(start, bestIndex);
    const right = splitRange(bestIndex, end);
    return left.concat(right);
  }

  return splitRange(0, unitData.length).filter(Boolean);
}

const state = {
  entries: [],
  index: 0,
  speedStep: 0,
  paused: false,
  originalProgress: 0,
  navigationReady: false,
  navigationTimer: 0,
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

  const compactViewport = window.matchMedia('(max-width: 720px)').matches;
  const shortChunkThreshold = compactViewport ? 10 : 18;
  const targetChunkChars = compactViewport ? 10 : 18;
  const maxChunkChars = compactViewport ? 12 : 28;

  if (visibleChars(clean) <= shortChunkThreshold) {
    return [{ text: clean, kind: 'content' }];
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

  const collapsedTokens = collapseShortPairedRuns(tokens);

  function isSentenceEndToken(token) {
    return /^[。！？!?]+$/.test(String(token || '').trim());
  }

  for (const token of collapsedTokens) {
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

  function chunkSentenceTokens(sentenceTokens, sentenceIndex) {
    const sentenceChunks = [];
    let buffer = '';
    let pendingPrefix = '';

    function flushLocalBuffer(kind = 'content', tail = '') {
      const chunk = buffer.trim();
      if (!chunk) {
        if (tail) {
          if (sentenceChunks.length) {
            sentenceChunks[sentenceChunks.length - 1].text += tail;
          } else {
            pendingPrefix += tail;
          }
        }
        buffer = '';
        return;
      }

      const pieces = splitBalancedText(chunk, {
        threshold: targetChunkChars,
        minChunk: compactViewport ? 4 : 8,
        maxChunk: maxChunkChars,
      });

      pieces.forEach((piece, index) => {
        sentenceChunks.push({
          text: index === pieces.length - 1 ? `${piece}${tail}` : piece,
          kind: index === pieces.length - 1 ? kind : 'internal',
        });
      });

      buffer = '';
    }

    function appendToBuffer(text) {
      const value = String(text || '').trim();
      if (!value) return;
      buffer += value;
    }

    for (let i = 0; i < sentenceTokens.length; i += 1) {
      const token = sentenceTokens[i];
      if (!token) continue;
      const text = String(token || '').trim();
      if (!text) continue;
      const nextToken = sentenceTokens[i + 1];
      const nextIsContent = nextToken ? !punctuationTokenRE.test(String(nextToken || '').trim()) : false;

      if (punctuationTokenRE.test(text)) {
        if (isOpeningPunctuationToken(text)) {
          if (buffer) {
            appendToBuffer(text);
          } else {
            pendingPrefix += text;
          }
          continue;
        }

        if (pendingPrefix) {
          appendToBuffer(pendingPrefix);
          pendingPrefix = '';
        }

        if (buffer) {
          appendToBuffer(text);
          flushLocalBuffer('content');
        } else if (sentenceChunks.length) {
          sentenceChunks[sentenceChunks.length - 1].text += text;
        } else {
          pendingPrefix += text;
        }
        continue;
      }

      if (pendingPrefix) {
        appendToBuffer(pendingPrefix);
        pendingPrefix = '';
      }

      appendToBuffer(text);
    }

    flushLocalBuffer('content');
    if (pendingPrefix) sentenceChunks.push({ text: pendingPrefix, kind: 'content' });

    const mergedChunks = mergePairedChunks(sentenceChunks.filter(Boolean));
    const sentenceChars = mergedChunks.reduce((sum, item) => sum + visibleChars(getChunkText(item)), 0);
    const sentenceChunkCount = mergedChunks.length || 1;
    return mergedChunks.map((item) => ({
      ...item,
      sentenceChars,
      sentenceChunkCount,
      sentenceIndex,
    }));
  }

  for (let sentenceIndex = 0; sentenceIndex < sentences.length; sentenceIndex += 1) {
    const sentence = sentences[sentenceIndex];
    chunks.push(...chunkSentenceTokens(sentence.tokens, sentenceIndex));
  }

  return chunks.filter(Boolean);
}

function mergePairedChunks(chunks) {
  const merged = [];
  let pendingPrefix = '';

  for (const item of chunks) {
    const text = getChunkText(item).trim();
    if (!text) continue;
    const kind = getChunkKind(item) || 'content';

    if (punctuationTokenRE.test(text)) {
      if (pairedOpenToClose.has(text)) {
        pendingPrefix += text;
        continue;
      }
      if (merged.length) {
        merged[merged.length - 1].text += text;
      } else {
        pendingPrefix += text;
      }
      continue;
    }

    merged.push({
      text: `${pendingPrefix}${text}`,
      kind,
    });
    pendingPrefix = '';
  }

  return merged.filter((item) => getChunkText(item).trim());
}

function clearTimers() {
  for (const id of state.timers || []) {
    window.clearTimeout(id);
  }
  state.timers = [];
  if (state.navigationTimer) {
    window.clearTimeout(state.navigationTimer);
    state.navigationTimer = 0;
  }
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
  document.querySelectorAll('.chunk.fade-shell, .chunk-core').forEach((node) => {
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
    } else if (!state.navigationReady) {
      el.stageHint.textContent = '3秒后可前后切换';
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
  const canNavigate = state.navigationReady;
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

function appendChunk(container, chunk, speedClass = 'soft', durationMultiplier = 1) {
  const text = getChunkText(chunk);
  const kind = getChunkKind(chunk);
  const span = document.createElement('span');
  span.className = isPunctuationChunk(text) ? 'chunk punctuation' : `chunk fade-shell ${speedClass}`;
  const sentenceChars = Math.max(1, Number(chunk?.sentenceChars || visibleChars(text) || 1));
  const revealDuration = getRevealDuration({ text, kind }, sentenceChars, durationMultiplier);
  const fadeDuration = getFadeDuration({ text, kind }, sentenceChars, durationMultiplier);
  const { body, tail, suffix } = splitBlinkingTail(text);

  if (isPunctuationChunk(text)) {
    span.textContent = text;
  } else if (tail) {
    const core = document.createElement('span');
    core.className = `chunk-core ${speedClass}`;
    core.style.setProperty('--reveal-duration', `${revealDuration}ms`);
    core.style.setProperty('--fade-duration', `${fadeDuration}ms`);
    core.append(document.createTextNode(body));
    const tailSpan = document.createElement('span');
    tailSpan.className = 'tail-punctuation';
    tailSpan.textContent = tail;
    core.appendChild(tailSpan);
    if (suffix) {
      core.appendChild(document.createTextNode(suffix));
    }
    span.appendChild(core);
  } else {
    const core = document.createElement('span');
    core.className = `chunk-core ${speedClass}`;
    core.style.setProperty('--reveal-duration', `${revealDuration}ms`);
    core.style.setProperty('--fade-duration', `${fadeDuration}ms`);
    core.textContent = text;
    span.appendChild(core);
  }
  container.appendChild(span);
  scheduleAutoScroll();
  return revealDuration;
}

function splitBlinkingTail(chunk) {
  const text = getChunkText(chunk);
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
  const text = getChunkText(chunk);
  if (isPunctuationChunk(text)) {
    return Math.max(90, Math.round(100 * durationMultiplier));
  }
  const length = Math.max(1, charCount);
  const base = 300 + Math.min(900, length * 95);
  const speedMultiplier = getSpeedMultiplier();
  return Math.max(
    minRevealMs,
    Math.min(maxRevealMs, Math.round(base * speedMultiplier * durationMultiplier * 200))
  );
}

function getFadeDuration(chunk, charCount, durationMultiplier = 1) {
  const text = getChunkText(chunk);
  if (isPunctuationChunk(text)) {
    return Math.max(220, Math.round(300 * durationMultiplier));
  }
  return Math.max(1000, Math.round(fadeDurationMs * durationMultiplier));
}

function getChunkPause(chunk, duration) {
  const text = getChunkText(chunk).trim();
  const kind = getChunkKind(chunk);
  const tail = text.slice(-1);
  const speedMultiplier = getSpeedMultiplier();
  const length = Math.max(1, visibleChars(text));
  if (/、/.test(tail)) {
    return 100;
  }
  if (kind === 'internal') {
    return 0;
  }
  if (/[。！？!?]/.test(tail)) {
    return Math.max(120, Math.round(length * 90 * speedMultiplier));
  }
  if (/[，：,:；;]/.test(tail)) {
    return Math.max(48, Math.round(length * 28 * speedMultiplier));
  }
  if (quotePunctuationRE.test(tail)) {
    return Math.max(32, Math.round(length * 18 * speedMultiplier));
  }
  return 0;
}

async function revealChunks(container, chunks, runId, speedClass = 'soft', progressMode = null) {
  let openingSentence = true;
  for (let i = 0; i < chunks.length; ) {
    if (runId !== state.runId) return false;
    const chunk = chunks[i];
    const sentenceIndex = Number(chunk?.sentenceIndex ?? i);
    const sentenceChunks = [];
    let j = i;
    while (j < chunks.length) {
      const candidate = chunks[j];
      const candidateIndex = Number(candidate?.sentenceIndex ?? j);
      if (candidateIndex !== sentenceIndex) break;
      sentenceChunks.push(candidate);
      j += 1;
    }
    const durationMultiplier = openingSentence ? 4 : 1;
    const durations = sentenceChunks.map((sentenceChunk) =>
      appendChunk(container, sentenceChunk, speedClass, durationMultiplier),
    );
    if (progressMode === 'original') {
      state.originalProgress = j / chunks.length;
      updateMeta();
      updateProgress();
      setNavigationState();
    }
    const waitDuration = Math.max(...durations, 0);
    await wait(waitDuration + getChunkPause(sentenceChunks[sentenceChunks.length - 1], waitDuration), runId);
    if (openingSentence) {
      openingSentence = false;
    }
    i = j;
  }
  return runId === state.runId;
}

function isPunctuationChunk(chunk) {
  const text = getChunkText(chunk);
  return /^[，。；！？、：,.!?;:（）()《》「」『』【】\[\]“”"'‘’—…]+$/.test(String(text || '').trim());
}
async function startEntry(index) {
  if (index < 0 || index >= state.entries.length) return;
  state.runId += 1;
  const runId = state.runId;
  clearTimers();
  stopAutoScroll();
  state.index = index;
  state.originalProgress = 0;
  state.navigationReady = false;
  resetContainers();
  updateMeta();
  updateProgress();
  setNavigationState();

  state.navigationTimer = window.setTimeout(() => {
    if (runId !== state.runId) return;
    state.navigationReady = true;
    state.navigationTimer = 0;
    updateMeta();
    setNavigationState();
  }, navigationDelayMs);

  const entry = currentEntry();
  const originalChunks = splitIntoChunks(entry.original || '');

  el.prev.disabled = index === 0;
  el.next.disabled = true;

  await revealChunks(el.original, originalChunks, runId, 'soft', 'original');
  scheduleAutoScroll();
}

function canAdvance() {
  return state.navigationReady && state.index < state.entries.length - 1;
}

function bindEvents() {
  el.prev.addEventListener('click', async () => {
    if (state.index <= 0 || !state.navigationReady) return;
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
