(() => {
  const bootstrap = JSON.parse(document.getElementById("bootstrap-data").textContent);
  const state = {
    siteBaseUrl: bootstrap.site?.site_base_url || "https://www.redrocks.net",
    articles: bootstrap.articles || [],
    categories: bootstrap.categories || [],
    themes: bootstrap.themes || [],
    activeDraft: null,
    activeMode: "edit",
    dirty: false,
    timer: null,
    savedRange: null,
    pauseSelectionTracking: false,
    pendingColor: "#f3eee4",
  };

  const els = {
    articleList: document.getElementById("articleList"),
    categoryList: document.getElementById("categoryList"),
    categorySelect: document.getElementById("categorySelect"),
    themeSelect: document.getElementById("themeSelect"),
    editor: document.getElementById("editor"),
    previewFrame: document.getElementById("previewFrame"),
    htmlView: document.getElementById("htmlView"),
    statusLine: document.getElementById("statusLine"),
    publishResult: document.getElementById("publishResult"),
    metaForm: document.getElementById("metaForm"),
    saveDraftBtn: document.getElementById("saveDraftBtn"),
    previewBtn: document.getElementById("previewBtn"),
    publishBtn: document.getElementById("publishBtn"),
    newArticleBtn: document.getElementById("newArticleBtn"),
    fileInput: document.getElementById("fileInput"),
    imageInput: document.getElementById("imageInput"),
    openColorPanelBtn: document.getElementById("openColorPanelBtn"),
    textColorInput: document.getElementById("textColorInput"),
    colorPanel: document.getElementById("colorPanel"),
    colorSwatches: document.getElementById("colorSwatches"),
    colorPreviewDot: document.getElementById("colorPreviewDot"),
    colorPreviewLabel: document.getElementById("colorPreviewLabel"),
    colorCancelBtn: document.getElementById("colorCancelBtn"),
    colorApplyBtn: document.getElementById("colorApplyBtn"),
    toolbar: document.getElementById("toolbar"),
  };

  const COLOR_SWATCHES = [
    "#f3eee4",
    "#ffffff",
    "#c7a86b",
    "#d97706",
    "#ef4444",
    "#7c3aed",
    "#2563eb",
    "#0f766e",
    "#111412",
  ];

  const SYNC_STATE_LABELS = {
    synced: "已同步",
    "missing-public": "缺发布页",
    "missing-source": "缺本地正文",
    "metadata-only": "仅元数据",
    "draft-synced": "草稿已生成",
    "draft-local-only": "仅本地草稿",
    "draft-public-only": "仅网页副本",
  };

  const WECHAT_CONTENT_SELECTORS = [
    "#img-content .rich_media_content",
    "#img-content",
    "#js_content",
    "#js_article .rich_media_content",
    "#js_article",
    ".rich_media_content",
  ];

  const WECHAT_REMOVE_SELECTORS = [
    "script",
    "style",
    "meta",
    "link",
    "iframe",
    "noscript",
    "title",
    "svg",
    ".menu_options",
    ".underline-container",
    ".underline_comment_dialog",
    ".drawer_main",
    ".discuss_mod",
    ".rich_media_meta_list",
    ".rich_media_tool",
    ".rich_media_title",
    ".original_area",
    ".js_share_appmsg",
    ".share_iframe_wrp",
    ".recommend_box",
    ".reward_area",
    ".copyright_info",
  ];

  const WECHAT_REMOVE_IDS = [
    "activity-name",
    "js_article",
    "js_content",
    "js_cmt_drawer_main",
    "js_pc_qrcode",
    "js_share_appmsg",
    "js_share_appmsg_desc",
  ];

  const EMPTY_TITLE_HINTS = new Set(["", "untitled", "在这里开始写作。"]);

  function setStatus(text, tone = "") {
    els.statusLine.textContent = text;
    els.statusLine.dataset.tone = tone;
  }

  function fillCategories() {
    els.categorySelect.innerHTML = "";
    els.categoryList.innerHTML = "";
    state.categories.forEach((cat) => {
      const opt = document.createElement("option");
      opt.value = cat.id;
      opt.textContent = `${cat.name} (${cat.directory})`;
      els.categorySelect.appendChild(opt);

    });
    renderCategoryList();
  }

  function getSelectedCategoryId() {
    return els.categorySelect.value || state.activeDraft?.category_id || state.categories[0]?.id || "";
  }

  function renderCategoryList() {
    const selectedId = getSelectedCategoryId();
    els.categoryList.innerHTML = "";
    state.categories.forEach((cat) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.classList.toggle("active", cat.id === selectedId);
      chip.setAttribute("aria-pressed", String(cat.id === selectedId));
      chip.textContent = cat.name;
      chip.addEventListener("click", () => {
        if (els.categorySelect.value !== cat.id) {
          els.categorySelect.value = cat.id;
          if (state.activeDraft) state.activeDraft.category_id = cat.id;
          renderCategoryList();
          markDirty();
        }
      });
      els.categoryList.appendChild(chip);
    });
  }

  function syncStateLabel(item) {
    return SYNC_STATE_LABELS[item?.sync_state] || "待检查";
  }

  function syncStateTone(item) {
    switch (item?.sync_state) {
      case "synced":
      case "draft-synced":
        return "ok";
      case "missing-public":
      case "missing-source":
      case "metadata-only":
      case "draft-public-only":
      case "draft-local-only":
        return "warn";
      default:
        return "neutral";
    }
  }

  function renderConsistencySummary() {
    const total = state.articles.length;
    const issues = state.articles.filter((item) => ["missing-public", "missing-source", "metadata-only"].includes(item.sync_state)).length;
    const synced = state.articles.filter((item) => item.sync_state === "synced" || item.sync_state === "draft-synced").length;
    const drafts = state.articles.filter((item) => item.sync_state?.startsWith("draft")).length;
    const lines = [
      `总计 ${total} 篇`,
      `同步 ${synced} 篇`,
      `草稿 ${drafts} 篇`,
      issues ? `${issues} 项待核对` : "本地-网络对应正常",
    ];
    const el = document.getElementById("consistencySummary");
    if (el) {
      el.innerHTML = lines.map((line, index) => `<span class="consistency-pill ${index === 3 && issues ? "danger" : ""}">${escapeHtml(line)}</span>`).join("");
    }
  }

  function fillThemes() {
    els.themeSelect.innerHTML = "";
    state.themes.forEach((theme) => {
      const opt = document.createElement("option");
      opt.value = theme.name;
      opt.textContent = theme.name;
      els.themeSelect.appendChild(opt);
    });
  }

  function renderArticleList() {
    const sorted = [...state.articles].sort((a, b) => (b.updated_date || "").localeCompare(a.updated_date || "") || (a.title || "").localeCompare(b.title || ""));
    const groups = new Map();
    state.categories.forEach((cat) => groups.set(cat.id, { category: cat, items: [] }));
    const uncategorized = { category: { id: "", name: "未分类", directory: "" }, items: [] };
    sorted.forEach((item) => {
      const bucket = groups.get(item.category_id);
      if (bucket) {
        bucket.items.push(item);
      } else {
        uncategorized.items.push(item);
      }
    });

    els.articleList.innerHTML = "";
    const renderGroup = (group) => {
      if (!group.items.length) return;
      const section = document.createElement("section");
      section.className = "article-group";

      const head = document.createElement("div");
      head.className = "article-group-head";
      head.innerHTML = `
        <div>
          <strong>${escapeHtml(group.category.name)}</strong>
          <span>${escapeHtml(group.category.directory || "未分类")}</span>
        </div>
        <span class="article-group-count">${group.items.length}</span>
      `;
      section.appendChild(head);

      group.items.forEach((item) => {
        const card = document.createElement("div");
        card.className = "article-item";

        const body = document.createElement("button");
        body.type = "button";
        body.className = "article-item-main";
        body.innerHTML = `
          <strong>${escapeHtml(item.title)}</strong>
          <div class="article-item-meta">
            <span>${escapeHtml(item.updated_date || "")}</span>
            <span class="article-sync ${syncStateTone(item)}">${escapeHtml(syncStateLabel(item))}</span>
          </div>
        `;
        body.addEventListener("click", () => editArticle(item));

        const actions = document.createElement("div");
        actions.className = "article-item-actions";

        const openBtn = document.createElement("button");
        openBtn.type = "button";
        openBtn.className = "article-action-btn";
        openBtn.textContent = "打开";
        openBtn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          openPublishedArticle(item);
        });

        const editBtn = document.createElement("button");
        editBtn.type = "button";
        editBtn.className = "article-action-btn";
        editBtn.textContent = "编辑";
        editBtn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          editArticle(item);
        });

        const deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.className = "article-action-btn article-action-danger";
        deleteBtn.textContent = "删除";
        deleteBtn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          deleteArticle(item);
        });

        actions.append(openBtn, editBtn, deleteBtn);
        card.append(body, actions);
        section.appendChild(card);
      });

      els.articleList.appendChild(section);
    };

    state.categories.forEach((cat) => renderGroup(groups.get(cat.id)));
    renderGroup(uncategorized);
    renderConsistencySummary();
  }

  async function reloadArticles() {
    const res = await fetch(`/api/articles?ts=${Date.now()}`, { cache: "no-store" });
    const payload = await res.json();
    if (res.ok && Array.isArray(payload.articles)) {
      state.articles = payload.articles;
      renderArticleList();
    }
  }

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
  }

  function articlePublishUrl(article) {
    return article?.canonical_url || new URL(`/articles/${encodeURIComponent(article?.category_directory || "")}/${encodeURIComponent(article?.slug || "")}.html`, state.siteBaseUrl).href;
  }

  function articleLocalMarkdownPath(article) {
    return article?.path || `articles/${article?.category_directory || ""}/${article?.slug || ""}.md`;
  }

  function articleLocalHtmlPath(article) {
    return article?.public_html_exists
      ? `articles/${article?.category_directory || ""}/${article?.slug || ""}.html`
      : article?.local_html_url || articlePublishUrl(article);
  }

  function renderPublishResult(payload, draft) {
    const articleUrl = payload.article_url || articlePublishUrl({
      category_directory: draft.category_directory || draft.category_id,
      slug: payload.slug || draft.slug,
      canonical_url: null,
    });
    const rows = [
      ["文章", draft.title || payload.title || ""],
      ["分类", draft.category_name || draft.category_id || ""],
      ["状态", "已发布"],
      ["本地正文", articleLocalMarkdownPath(draft)],
      ["发布页", articleUrl],
      ["提交", payload.commit || ""],
    ];
    els.publishResult.innerHTML = `
      <div class="publish-result-head">发布完成</div>
      <div class="publish-result-note">本地正文已写回，栏目页与文章索引已重建，发布状态已同步。</div>
      <div class="publish-result-grid">
        ${rows.map(([label, value]) => `
          <div class="publish-result-cell">
            <span class="publish-result-label">${escapeHtml(label)}</span>
            <span class="publish-result-value">${value ? escapeHtml(value) : "<span class='publish-result-empty'>未提供</span>"}</span>
          </div>
        `).join("")}
      </div>
    `;
  }

  function buildDeleteConfirmation(article) {
    const localMd = articleLocalMarkdownPath(article);
    const localHtml = articleLocalHtmlPath(article);
    const publicUrl = articlePublishUrl(article);
    return [
      `确定永久删除《${article.title}》吗？`,
      ``,
      `分类：${article.category_name || article.category_id || ""}`,
      `本地正文：${localMd}`,
      `本地页面：${localHtml}`,
      `发布页：${publicUrl}`,
      ``,
      `操作会删除本地文件、重建网站索引并同步 git。`,
      `此操作无法撤销。`,
    ].join("\n");
  }

  function normalizeWhitespace(text) {
    return String(text || "").replace(/\s+/g, " ").trim();
  }

  function extractTitleTextFromNode(node) {
    if (!node) return "";
    const parts = [];
    for (const child of node.childNodes || []) {
      if (child.nodeType === Node.ELEMENT_NODE && child.tagName === "BR") break;
      if (child.nodeType === Node.TEXT_NODE) {
        parts.push(child.textContent || "");
      } else if (child.nodeType === Node.ELEMENT_NODE) {
        if (child.tagName === "IMG" || child.tagName === "VIDEO" || child.tagName === "IFRAME") break;
        parts.push(child.textContent || "");
      }
    }
    const head = normalizeWhitespace(parts.join(" "));
    return head || normalizeWhitespace(node.textContent || "");
  }

  function extractTrailingFragmentAfterBreak(node) {
    const frag = document.createDocumentFragment();
    if (!node) return frag;
    let seenBreak = false;
    for (const child of node.childNodes || []) {
      if (!seenBreak) {
        if (child.nodeType === Node.ELEMENT_NODE && child.tagName === "BR") {
          seenBreak = true;
        }
        continue;
      }
      frag.appendChild(child.cloneNode(true));
    }
    return frag;
  }

  function trimEmptyBlocks(container) {
    container.querySelectorAll("p,div,section,article,span").forEach((node) => {
      const hasContent = node.textContent.trim() || node.querySelector("img,video,iframe,table,ul,ol,blockquote,hr");
      if (!hasContent) node.remove();
    });
  }

  function cleanImportedHtml(htmlText) {
    const sourceText = String(htmlText || "").trim();
    if (!sourceText) return { html: "", title: "" };

    const parser = new DOMParser();
    const doc = parser.parseFromString(sourceText, "text/html");
    const titleNode = doc.querySelector("#activity-name, .rich_media_title") || doc.querySelector("h1");
    const detectedTitle = extractTitleTextFromNode(titleNode);

    let source = null;
    for (const selector of WECHAT_CONTENT_SELECTORS) {
      source = doc.querySelector(selector);
      if (source) break;
    }
    if (!source) source = doc.body;

    const container = document.createElement("div");
    container.innerHTML = source.innerHTML || "";

    if (titleNode) {
      const trailing = extractTrailingFragmentAfterBreak(titleNode);
      if (trailing.childNodes.length) {
        container.prepend(trailing);
      }
      WECHAT_REMOVE_IDS.forEach((id) => {
        container.querySelectorAll(`[id="${id}"]`).forEach((node) => node.remove());
      });
      WECHAT_REMOVE_SELECTORS.forEach((selector) => {
        if (selector === "h1" || selector === "h2") return;
        container.querySelectorAll(selector).forEach((node) => node.remove());
      });
      if (titleNode.id === "activity-name" || titleNode.classList.contains("rich_media_title")) {
        container.querySelectorAll("#activity-name, .rich_media_title").forEach((node) => node.remove());
      } else if (titleNode.tagName === "H1" && source.querySelectorAll("h1").length === 1) {
        container.querySelector("h1")?.remove();
      }
    } else {
      WECHAT_REMOVE_SELECTORS.forEach((selector) => {
        container.querySelectorAll(selector).forEach((node) => node.remove());
      });
      WECHAT_REMOVE_IDS.forEach((id) => {
        container.querySelectorAll(`[id="${id}"]`).forEach((node) => node.remove());
      });
    }

    trimEmptyBlocks(container);

    return { html: container.innerHTML.trim(), title: detectedTitle };
  }

  function normalizeEditorHtml(htmlText) {
    const cleaned = cleanImportedHtml(htmlText);
    return cleaned.html || String(htmlText || "");
  }

  function shouldAdoptImportedTitle(currentTitle, importedTitle) {
    return EMPTY_TITLE_HINTS.has(String(currentTitle || "").trim().toLowerCase()) && !!normalizeWhitespace(importedTitle);
  }

  function applyImportedContent(htmlText) {
    const cleaned = cleanImportedHtml(htmlText);
    const html = cleaned.html || String(htmlText || "");
    els.editor.innerHTML = html;
    if (shouldAdoptImportedTitle(state.activeDraft?.title, cleaned.title)) {
      state.activeDraft.title = cleaned.title;
      els.metaForm.title.value = cleaned.title;
      syncSlugFromTitle();
    }
    state.activeDraft.html = html;
    state.activeDraft.plain_text = els.editor.innerText;
    return cleaned;
  }

  function openPublishedArticle(article) {
    const networkUrl = articlePublishUrl(article);
    const localUrl = article.local_html_url || networkUrl;
    const url = article.public_html_exists ? networkUrl : localUrl;
    if (article.public_html_exists) {
      setStatus(`已打开发布页：${article.title}`);
    } else if (article.local_html_url) {
      setStatus(`发布页尚未生成，已打开本地副本：${article.title}`, "error");
    } else {
      setStatus(`文章页尚未生成：${article.title}`, "error");
    }
    window.open(url, "_blank", "noopener");
  }

  function makeTitleSlug(title, publishedDate) {
    const cleanTitle = Array.from(String(title || "").trim().replace(/[\s_]+/g, ""))
      .filter((ch) => /[0-9A-Za-z\u4e00-\u9fff]/.test(ch))
      .join("");
    const clipped = cleanTitle.slice(0, 8) || "untitled";
    const datePrefix = String(publishedDate || new Date().toISOString().slice(0, 10)).replace(/\D+/g, "");
    return `${datePrefix}-${clipped}`;
  }

  function syncSlugFromTitle() {
    const title = els.metaForm.title.value.trim();
    const slug = els.metaForm.slug.value.trim();
    if (!title) return;
    if (slug && slug.toLowerCase() !== "untitled") return;
    els.metaForm.slug.value = makeTitleSlug(title, els.metaForm.published_date.value);
  }

  function newDraft() {
    const id = crypto.randomUUID();
    state.activeDraft = {
      article_id: id,
      title: "",
      english_title: "",
      subtitle: "",
      summary: "",
      author: "RedRocks",
      published_date: new Date().toISOString().slice(0, 10),
      updated_date: new Date().toISOString(),
      status: "draft",
      slug: "",
      category_id: state.categories[0]?.id || "misc",
      themes: [],
      tags: [],
      featured: false,
      source_format: "paste",
      html: "<p>在这里开始写作。</p>",
      plain_text: "在这里开始写作。",
      metadata: { article_id: id },
    };
    syncForm();
    els.editor.innerHTML = state.activeDraft.html;
    syncSlugFromTitle();
    setMode("edit");
    markDirty();
  }

  function openArticle(article) {
    fetch(`/api/articles/${encodeURIComponent(article.article_id)}`)
      .then((r) => {
        if (!r.ok) {
          throw new Error(`加载失败：${r.status}`);
        }
        return r.json();
      })
      .then((payload) => {
        const rawHtml = payload.content_html || "<p>请通过右侧草稿重新打开文章进行编辑。</p>";
        const cleaned = cleanImportedHtml(rawHtml);
        const cleanedHtml = cleaned.html || rawHtml;
        const adoptedTitle = shouldAdoptImportedTitle(payload.title, cleaned.title) ? cleaned.title : payload.title;
        const resolvedArticleId = payload.article_id || article.article_id;
        const resolvedSummary = payload.summary || article.summary || "";
        state.activeDraft = {
          article_id: resolvedArticleId,
          title: adoptedTitle,
          english_title: payload.english_title || "",
          subtitle: payload.subtitle || "",
          summary: resolvedSummary,
          author: "RedRocks",
          published_date: payload.published_date || new Date().toISOString().slice(0, 10),
          updated_date: payload.updated_date || new Date().toISOString(),
          status: payload.status || "draft",
          slug: payload.slug || payload.title,
          category_id: payload.category_id,
          themes: payload.metadata?.themes || [],
          tags: payload.metadata?.tags || [],
          featured: false,
          source_format: payload.source_format || "markdown",
          html: cleanedHtml,
          plain_text: payload.plain_text || "",
          metadata: payload.metadata || { article_id: resolvedArticleId, canonical_url: payload.path },
        };
        els.editor.innerHTML = state.activeDraft.html;
        syncForm();
        syncSlugFromTitle();
        setMode("edit");
        if (cleanedHtml !== rawHtml || adoptedTitle !== payload.title) {
          state.dirty = true;
          setStatus("已整理微信复制内容，请保存或发布以写回干净版本", "dirty");
          return;
        }
        setStatus(`已打开：${payload.title}`);
      })
      .catch((err) => {
        setStatus(`打开失败：${err.message}`, "error");
      });
  }

  function editArticle(article) {
    openArticle(article);
  }

  function syncForm() {
    const draft = state.activeDraft;
    if (!draft) return;
    els.metaForm.title.value = draft.title || "";
    els.metaForm.english_title.value = draft.english_title || "";
    els.metaForm.subtitle.value = draft.subtitle || "";
    els.metaForm.summary.value = draft.summary || "";
    els.metaForm.author.value = draft.author || "RedRocks";
    els.metaForm.published_date.value = draft.published_date || new Date().toISOString().slice(0, 10);
    els.categorySelect.value = draft.category_id || state.categories[0]?.id || "";
    Array.from(els.themeSelect.options).forEach((opt) => {
      opt.selected = (draft.themes || []).includes(opt.value);
    });
    els.metaForm.tags.value = (draft.tags || []).join(", ");
    els.metaForm.slug.value = draft.slug || "";
    els.metaForm.cover_image_path.value = draft.cover_image_path || "";
    els.metaForm.featured.checked = !!draft.featured;
    els.metaForm.status.value = draft.status || "draft";
    renderCategoryList();
  }

  function readForm() {
    const form = els.metaForm;
    return {
      title: form.title.value.trim(),
      english_title: form.english_title.value.trim(),
      subtitle: form.subtitle.value.trim(),
      summary: form.summary.value.trim(),
      author: form.author.value.trim() || "RedRocks",
      published_date: form.published_date.value,
      category_id: form.category_id.value,
      themes: Array.from(els.themeSelect.selectedOptions).map((o) => o.value),
      tags: form.tags.value.split(",").map((s) => s.trim()).filter(Boolean),
      slug: form.slug.value.trim(),
      cover_image_path: form.cover_image_path.value.trim(),
      featured: form.featured.checked,
      status: form.status.value,
    };
  }

  function snapshotDraft() {
    if (!state.activeDraft) return null;
    const form = readForm();
    const html = normalizeEditorHtml(els.editor.innerHTML);
    return {
      ...state.activeDraft,
      ...form,
      html,
      plain_text: els.editor.innerText,
      updated_at: new Date().toISOString(),
      metadata: { ...(state.activeDraft.metadata || {}) },
    };
  }

  function markDirty() {
    state.dirty = true;
    if (state.activeDraft && state.activeDraft.status === "published" && els.metaForm.status.value === "published") {
      state.activeDraft.status = "modified";
      els.metaForm.status.value = "modified";
    }
    setStatus("有未保存修改", "dirty");
    clearTimeout(state.timer);
    state.timer = setTimeout(() => saveDraft(false), 1400);
  }

  function captureSelection() {
    if (state.pauseSelectionTracking) return;
    const selection = window.getSelection();
    if (!selection || !selection.rangeCount) return;
    const range = selection.getRangeAt(0);
    if (els.editor.contains(range.commonAncestorContainer)) {
      state.savedRange = range.cloneRange();
    }
  }

  function restoreSelection() {
    if (!state.savedRange) return false;
    const selection = window.getSelection();
    if (!selection) return false;
    selection.removeAllRanges();
    selection.addRange(state.savedRange);
    return true;
  }

  function placeCaretAtEnd() {
    const selection = window.getSelection();
    if (!selection) return false;
    const range = document.createRange();
    range.selectNodeContents(els.editor);
    range.collapse(false);
    selection.removeAllRanges();
    selection.addRange(range);
    state.savedRange = range.cloneRange();
    return true;
  }

  function ensureInsertSelection() {
    if (restoreSelection()) return true;
    els.editor.focus({ preventScroll: true });
    return placeCaretAtEnd();
  }

  function fileToDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ""));
      reader.onerror = () => reject(new Error("read image failed"));
      reader.readAsDataURL(file);
    });
  }

  function insertHtmlAtSelection(html) {
    if (!ensureInsertSelection()) return false;
    document.execCommand("insertHTML", false, html);
    state.activeDraft.html = els.editor.innerHTML;
    state.activeDraft.plain_text = els.editor.innerText;
    markDirty();
    captureSelection();
    return true;
  }

  function setPendingColor(color) {
    state.pendingColor = color;
    els.textColorInput.value = color;
    els.colorPreviewDot.style.background = color;
    els.colorPreviewLabel.textContent = color.toUpperCase();
  }

  function openColorPanel() {
    if (!state.savedRange) {
      setStatus("请先在正文里选中文字，再打开字体色彩", "error");
      return;
    }
    state.pauseSelectionTracking = true;
    els.colorPanel.classList.remove("hidden");
  }

  function closeColorPanel() {
    els.colorPanel.classList.add("hidden");
    state.pauseSelectionTracking = false;
  }

  function applyColorToSavedSelection(color) {
    if (!state.savedRange) {
      setStatus("请先在正文里选中文字，再选颜色", "error");
      return;
    }
    try {
      const selection = window.getSelection();
      if (!selection) {
        setStatus("颜色应用失败：无法获取选择区", "error");
        return;
      }

      const range = state.savedRange.cloneRange();
      if (range.collapsed) {
        setStatus("请先选中一段文字", "error");
        return;
      }

      els.editor.focus({ preventScroll: true });
      selection.removeAllRanges();
      selection.addRange(range);
      document.execCommand("styleWithCSS", false, true);
      const ok = document.execCommand("foreColor", false, color);
      if (!ok) {
        setStatus("颜色应用失败：浏览器拒绝执行", "error");
        return;
      }
      captureSelection();
      els.editor.focus({ preventScroll: true });
      state.activeDraft.html = els.editor.innerHTML;
      setStatus(`已应用字体颜色 ${color}`, "success");
      markDirty();
      closeColorPanel();
    } catch (err) {
      setStatus(`颜色应用失败：${err.message}`, "error");
    }
  }

  function setMode(mode) {
    state.activeMode = mode;
    document.querySelectorAll(".mode").forEach((btn) => btn.classList.toggle("active", btn.dataset.mode === mode));
    els.editor.classList.toggle("hidden", mode !== "edit");
    els.previewFrame.classList.toggle("hidden", mode !== "desktop" && mode !== "mobile");
    els.htmlView.classList.toggle("hidden", mode !== "html");
    if (mode === "desktop" || mode === "mobile") {
      refreshPreview(mode);
    }
    if (mode === "html") {
      els.htmlView.value = els.editor.innerHTML;
    }
  }

  function refreshPreview(mode) {
    const draft = snapshotDraft();
    if (!draft) return;
    fetch("/api/drafts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(draft) });
    els.previewFrame.src = `/api/preview/${encodeURIComponent(draft.article_id)}?mode=${mode}`;
    els.previewFrame.style.width = mode === "mobile" ? "390px" : "100%";
  }

  function saveDraft(showNotice = true) {
    const draft = snapshotDraft();
    if (!draft) return Promise.resolve();
    return fetch("/api/drafts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(draft),
    }).then((res) => res.json()).then((payload) => {
      state.activeDraft = draft;
      state.dirty = false;
      if (showNotice) setStatus("草稿已保存");
      return payload;
    }).catch((err) => {
      setStatus(`保存失败：${err.message}`, "error");
    });
  }

  function applyCommand(cmd, value) {
    if (!cmd) return;
    if (cmd === "createLink") {
      const url = window.prompt("链接地址");
      if (!url) return;
      restoreSelection();
      document.execCommand("createLink", false, url);
      markDirty();
      return;
    }
    restoreSelection();
    if (value) document.execCommand(cmd, false, value);
    else document.execCommand(cmd, false, null);
    markDirty();
  }

  async function importFile(file) {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/api/import", { method: "POST", body: form });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.error || "import failed");
    const cleanedHtml = normalizeEditorHtml(payload.html);
    els.editor.innerHTML = cleanedHtml;
    state.activeDraft.html = cleanedHtml;
    state.activeDraft.plain_text = payload.plain_text;
    if (!normalizeWhitespace(state.activeDraft.title)) {
      state.activeDraft.title = payload.title || file.name.replace(/\.[^.]+$/, "");
    }
    syncForm();
    markDirty();
  }

  async function publish() {
    try {
      const draft = snapshotDraft();
      if (!draft) return;
      if (state.activeDraft?.status === "published" && !state.dirty) {
        setStatus("当前内容已经是最新发布状态", "success");
        return;
      }
      syncSlugFromTitle();
      draft.slug = els.metaForm.slug.value.trim();
      draft.status = "published";
      await saveDraft(false);
      const res = await fetch("/api/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      const payload = await res.json();
      if (!res.ok) {
        els.publishResult.classList.add("hidden");
        setStatus(`发布失败：${payload.message || payload.error || "unknown"}`, "error");
        return;
      }
      renderPublishResult(payload, draft);
      els.publishResult.classList.remove("hidden");
      state.activeDraft = { ...draft, status: "published" };
      els.metaForm.status.value = "published";
      state.dirty = false;
      setStatus(`发布完成 · ${payload.commit || ""}`, "success");
      await reloadArticles();
    } catch (err) {
      setStatus(`发布失败：${err.message}`, "error");
      if (els.publishResult) els.publishResult.classList.add("hidden");
    }
  }

  async function deleteArticle(article) {
    const ok = window.confirm(buildDeleteConfirmation(article));
    if (!ok) return;
    const previousArticles = [...state.articles];
    state.articles = state.articles.filter((item) => item.article_id !== article.article_id);
    renderArticleList();
    setStatus(`正在删除并重建索引：${article.title}...`, "dirty");
    const res = await fetch(`/api/articles/${encodeURIComponent(article.article_id)}`, { method: "DELETE" });
    const payload = await res.json();
    if (!res.ok) {
      state.articles = previousArticles;
      renderArticleList();
      setStatus(`删除失败：${payload.error || payload.message || "unknown"}`, "error");
      return;
    }
    if (state.activeDraft?.article_id === article.article_id) {
      newDraft();
    }
    await reloadArticles();
    setStatus(`已删除并同步清理：${payload.title || article.title}`, "success");
  }

  function bindEvents() {
    els.editor.addEventListener("paste", (ev) => {
      const clipboard = ev.clipboardData;
      const html = clipboard?.getData("text/html") || "";
      if (!html) return;
      const cleaned = cleanImportedHtml(html);
      if (!cleaned.html) return;
      ev.preventDefault();
      insertHtmlAtSelection(cleaned.html);
      if (shouldAdoptImportedTitle(state.activeDraft?.title, cleaned.title)) {
        state.activeDraft.title = cleaned.title;
        els.metaForm.title.value = cleaned.title;
        syncSlugFromTitle();
      }
    });
    els.editor.addEventListener("input", () => {
      if (!state.activeDraft) return;
      state.activeDraft.html = els.editor.innerHTML;
      markDirty();
    });
    els.editor.addEventListener("mouseup", captureSelection);
    els.editor.addEventListener("keyup", captureSelection);
    els.editor.addEventListener("focus", captureSelection);
    document.addEventListener("selectionchange", () => {
      if (state.pauseSelectionTracking) return;
      const selection = window.getSelection();
      if (!selection || !selection.rangeCount) return;
      const range = selection.getRangeAt(0);
      if (els.editor.contains(range.commonAncestorContainer)) {
        state.savedRange = range.cloneRange();
      }
    });
    els.metaForm.addEventListener("input", markDirty);
    els.metaForm.title.addEventListener("input", () => {
      syncSlugFromTitle();
      markDirty();
    });
    els.metaForm.published_date.addEventListener("input", () => {
      syncSlugFromTitle();
      markDirty();
    });
    els.metaForm.slug.addEventListener("input", markDirty);
    els.categorySelect.addEventListener("change", () => {
      if (state.activeDraft) state.activeDraft.category_id = els.categorySelect.value;
      renderCategoryList();
      markDirty();
    });
    els.themeSelect.addEventListener("change", markDirty);
    document.querySelectorAll(".mode").forEach((btn) => {
      btn.addEventListener("click", () => setMode(btn.dataset.mode));
    });
    els.saveDraftBtn.addEventListener("click", () => saveDraft(true));
    els.previewBtn.addEventListener("click", () => setMode("desktop"));
    els.publishBtn.addEventListener("click", publish);
    els.newArticleBtn.addEventListener("click", newDraft);
    els.toolbar.addEventListener("click", (ev) => {
      const btn = ev.target.closest("button");
      if (!btn || !btn.dataset.cmd) return;
      applyCommand(btn.dataset.cmd, btn.dataset.value);
    });
    els.toolbar.addEventListener("mousedown", () => {
      captureSelection();
    });
    els.fileInput.addEventListener("change", async () => {
      const file = els.fileInput.files?.[0];
      if (!file) return;
      await importFile(file);
      els.fileInput.value = "";
    });
    els.imageInput.addEventListener("change", async () => {
      const file = els.imageInput.files?.[0];
      if (!file) return;
      try {
        const dataUrl = await fileToDataUrl(file);
        const safeName = escapeHtml(file.name.replace(/\.[^.]+$/, ""));
        const inserted = insertHtmlAtSelection(`<img class="article-image" src="${dataUrl}" alt="${safeName}" data-filename="${safeName}">`);
        if (!inserted) setStatus("插图失败：无法定位光标", "error");
      } catch (err) {
        setStatus(`插图失败：${err.message}`, "error");
      }
      els.imageInput.value = "";
    });
    els.imageInput.closest(".file-btn")?.addEventListener("mousedown", () => {
      captureSelection();
    });
    els.openColorPanelBtn.addEventListener("mousedown", (ev) => {
      ev.preventDefault();
      captureSelection();
    });
    els.openColorPanelBtn.addEventListener("click", openColorPanel);
    els.textColorInput.addEventListener("input", () => {
      setPendingColor(els.textColorInput.value || "#f3eee4");
    });
    els.colorCancelBtn.addEventListener("click", closeColorPanel);
    els.colorApplyBtn.addEventListener("click", () => {
      applyColorToSavedSelection(state.pendingColor || "#f3eee4");
    });
    COLOR_SWATCHES.forEach((color) => {
      const swatch = document.createElement("button");
      swatch.type = "button";
      swatch.className = "swatch";
      swatch.style.background = color;
      swatch.title = color.toUpperCase();
      swatch.addEventListener("click", () => setPendingColor(color));
      els.colorSwatches.appendChild(swatch);
    });
    setPendingColor("#f3eee4");
  }

  function init() {
    fillCategories();
    fillThemes();
    renderArticleList();
    bindEvents();
    newDraft();
    setStatus("已加载");
  }

  init();
})();
