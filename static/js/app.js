/* ==========================================================================
   KaleemGPT — frontend
   - Conversations & messages live on the server (SQLite); localStorage only
     keeps per-device preferences.
   - All UI events go through one delegated handler using data-action, so no
     inline onclick handlers are needed (keeps DOMPurify strict).
   ========================================================================== */
(() => {
'use strict';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

/* ---------- Icons (inline SVG, lucide-style) ---------- */
const ICONS = {
  plus: '<path d="M5 12h14M12 5v14"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  panel: '<rect width="18" height="18" x="3" y="3" rx="3"/><path d="M9 3v18"/>',
  settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  theme: '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 0 0 18Z" fill="currentColor"/>',
  trash: '<path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  pencil: '<path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>',
  copy: '<rect width="13" height="13" x="9" y="9" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  refresh: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
  volume: '<path d="M11 5 6 9H2v6h4l5 4V5Z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"/>',
  stop: '<rect x="6" y="6" width="12" height="12" rx="2.5" fill="currentColor" stroke="none"/>',
  'arrow-up': '<path d="m5 12 7-7 7 7M12 19V5"/>',
  'arrow-down': '<path d="M12 5v14M19 12l-7 7-7-7"/>',
  paperclip: '<path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M19 10v1a7 7 0 0 1-14 0v-1M12 18v4"/>',
  chevron: '<path d="m6 9 6 6 6-6"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  file: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4M9 13h6M9 17h4"/>',
  code: '<path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/>',
  sparkles: '<path d="M12 3 13.9 8.6 19.5 10.5 13.9 12.4 12 18 10.1 12.4 4.5 10.5 10.1 8.6Z"/><path d="M19 17v4M17 19h4"/>',
  chart: '<path d="M3 3v18h18"/><path d="M18 17V9M13 17V5M8 17v-3"/>',
  globe: '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10Z"/>',
  bulb: '<path d="M9 18h6M10 22h4"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/>',
  more: '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
  loader: '<path d="M21 12a9 9 0 1 1-6.22-8.56"/>',
  alert: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
};
const AGENT_ICONS = { sparkles: 'sparkles', code: 'code', search: 'globe', file: 'file', chart: 'chart' };

function icon(name, size) {
  return `<svg class="i${size ? ' i-' + size : ''}${name === 'loader' ? ' spin' : ''}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ''}</svg>`;
}
function hydrateIcons(root = document) {
  $$('[data-icon]', root).forEach((el) => {
    el.insertAdjacentHTML('afterbegin', icon(el.dataset.icon, el.dataset.size));
    el.removeAttribute('data-icon');
  });
}

/* ---------- Utils ---------- */
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function newId() {
  // crypto.randomUUID needs HTTPS; getRandomValues works everywhere.
  const b = new Uint8Array(12);
  crypto.getRandomValues(b);
  return Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');
}
const nowISO = () => new Date().toISOString();
function makeTitle(t) {
  const c = String(t || '').replace(/\s+/g, ' ').trim();
  return c ? (c.length > 50 ? c.slice(0, 50) + '…' : c) : 'New Chat';
}
function fmtSize(n) {
  if (n < 1024) return n + ' B';
  if (n < 1048576) return (n / 1024).toFixed(0) + ' KB';
  return (n / 1048576).toFixed(1) + ' MB';
}
function fmtTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const sameDay = d.toDateString() === new Date().toDateString();
  return sameDay
    ? d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
    : d.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
const isMobile = () => window.matchMedia('(max-width: 860px)').matches;

async function api(path, opts = {}) {
  const headers = opts.body && !(opts.body instanceof FormData) ? { 'Content-Type': 'application/json' } : undefined;
  const res = await fetch(path, { headers, ...opts });
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) {
    let msg = data && (data.message || data.error || data.detail);
    if (Array.isArray(msg)) msg = msg[0]?.msg;
    throw new Error(msg || `Request failed (${res.status})`);
  }
  return data;
}

/* ---------- Settings (per device) ---------- */
const SETTINGS_KEY = 'kaleemgpt_settings';
const DEFAULT_SETTINGS = {
  theme: 'dark', displayName: 'Kaleem', defaultAgent: 'general', model: '',
  enterToSend: true, showTimestamps: false, markdown: true,
  voiceInput: true, voiceOutput: false, voiceURI: '', speechRate: '1',
  sidebarCollapsed: false,
};
function loadSettings() {
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}') || {}; } catch { /* ignore */ }
  state.settings = { ...DEFAULT_SETTINGS, ...saved };
}
function saveSettings() {
  try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(state.settings)); } catch { /* private mode */ }
}

/* ---------- State ---------- */
const state = {
  config: null,
  conversations: [],
  convLoaded: false,
  currentId: null,
  messages: [],
  agent: 'general',
  model: '',
  attachments: [],
  stream: null,
  stick: true,
  recording: false,
  search: '',
  settings: { ...DEFAULT_SETTINGS },
};
const historyCache = new Map();

const FALLBACK_AGENTS = [{ key: 'general', name: 'General Assistant', description: 'Chat, answer questions, help with tasks', icon: 'sparkles' }];

const SUGGESTIONS = [
  { icon: 'globe', title: 'Catch me up on AI news', sub: 'Search the web for this week', agent: 'research', prompt: 'What are the most important AI news stories this week?' },
  { icon: 'code', title: 'Debug my code', sub: 'Find the root cause and fix it', agent: 'coding', prompt: 'Help me debug this code:\n\n```python\n\n```' },
  { icon: 'file', title: 'Summarize a document', sub: 'Upload a PDF, DOCX or text file', agent: 'document', attach: true },
  { icon: 'chart', title: 'Crunch some numbers', sub: '$10k at 7% for 10 years', agent: 'data', prompt: 'If I invest $10,000 at 7% annual interest compounded monthly, how much will I have after 10 years?' },
  { icon: 'bulb', title: 'Remember a preference', sub: 'Saved across all chats', prompt: 'Remember that I prefer concise answers with practical examples.' },
  { icon: 'edit', title: 'Improve my writing', sub: 'Clearer, sharper, same voice', prompt: 'Improve the clarity and tone of this text:\n\n' },
];

/* ==========================================================================
   Markdown
   ========================================================================== */
let highlightOn = true;

function setupMarkdown() {
  if (window.marked) {
    marked.use({
      gfm: true,
      breaks: true,
      renderer: {
        // Works with both marked <13 (code, lang) and >=13 ({text, lang}) signatures.
        code(code, infostring) {
          let text = code, lang = infostring;
          if (code && typeof code === 'object') { text = code.text; lang = code.lang; }
          lang = String(lang || '').trim().split(/\s+/)[0];
          let body = null;
          if (highlightOn && window.hljs && lang && hljs.getLanguage(lang)) {
            try { body = hljs.highlight(String(text), { language: lang, ignoreIllegals: true }).value; } catch { /* fall through */ }
          }
          if (body == null) body = esc(text);
          return `<div class="code-block"><div class="code-head"><span>${esc(lang || 'text')}</span>` +
            `<button class="code-copy" data-action="copy-code">${icon('copy', 'sm')}<span>Copy</span></button></div>` +
            `<pre><code class="hljs">${body}</code></pre></div>`;
        },
      },
    });
  }
  if (window.DOMPurify) {
    DOMPurify.addHook('afterSanitizeAttributes', (node) => {
      if (node.tagName === 'A') {
        node.setAttribute('target', '_blank');
        node.setAttribute('rel', 'noopener noreferrer');
      }
    });
  }
}

function renderMarkdown(text, { highlight = true } = {}) {
  if (!state.settings.markdown || !window.marked || !window.DOMPurify) {
    return `<p class="plain">${esc(text)}</p>`;
  }
  highlightOn = highlight;
  let html = marked.parse(String(text || ''));
  html = html.replace(/<table>/g, '<div class="table-wrap"><table>').replace(/<\/table>/g, '</table></div>');
  return DOMPurify.sanitize(html, { FORBID_TAGS: ['style', 'form', 'input', 'textarea', 'select', 'iframe'] });
}

/* ==========================================================================
   Theme / profile
   ========================================================================== */
const darkMQ = window.matchMedia('(prefers-color-scheme: dark)');
function resolvedTheme() {
  const t = state.settings.theme;
  return t === 'system' ? (darkMQ.matches ? 'dark' : 'light') : t;
}
function applyTheme() {
  const t = resolvedTheme();
  document.documentElement.setAttribute('data-theme', t);
  const hl = $('#hljs-theme');
  const href = `https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/${t === 'dark' ? 'github-dark' : 'github'}.min.css`;
  if (hl && hl.getAttribute('href') !== href) hl.setAttribute('href', href);
  $('meta[name="theme-color"]')?.setAttribute('content', t === 'dark' ? '#0d0d12' : '#ffffff');
  $('#theme-btn').innerHTML = icon(t === 'dark' ? 'sun' : 'moon');
  $('#theme-menu-label').textContent = t === 'dark' ? 'Light mode' : 'Dark mode';
}
darkMQ.addEventListener?.('change', () => { if (state.settings.theme === 'system') applyTheme(); });

function toggleTheme() {
  state.settings.theme = resolvedTheme() === 'dark' ? 'light' : 'dark';
  saveSettings();
  applyTheme();
}

function applyProfile() {
  const name = (state.settings.displayName || '').trim() || 'You';
  $('#profile-name').textContent = name;
  $('#profile-avatar').textContent = name.charAt(0).toUpperCase();
}

/* ==========================================================================
   Toasts & modals
   ========================================================================== */
function toast(message, type = 'info', ms = 3200) {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = (type === 'error' ? icon('alert', 'sm') : type === 'success' ? icon('check', 'sm') : '') + `<span>${esc(message)}</span>`;
  $('#toasts').append(el);
  setTimeout(() => { el.classList.add('out'); setTimeout(() => el.remove(), 220); }, ms);
}

let lastFocus = null;
function openModal(id) {
  closeMenus();
  lastFocus = document.activeElement;
  const m = $('#' + id);
  m.classList.add('open');
  setTimeout(() => (m.querySelector('input:not([type=checkbox]), .btn-primary, .btn-danger, select, button') || m).focus(), 60);
}
function closeModal(el) {
  const m = el?.closest ? el.closest('.modal-backdrop') : el;
  if (!m || !m.classList.contains('open')) return;
  m.classList.remove('open');
  if (m.id === 'confirm-modal' && confirmResolve) { confirmResolve(false); confirmResolve = null; }
  lastFocus?.focus?.();
}
const openModalEl = () => $('.modal-backdrop.open');

let confirmResolve = null;
function confirmDialog(title, text, ok = 'Delete') {
  $('#confirm-title').textContent = title;
  $('#confirm-text').textContent = text;
  $('#confirm-ok').textContent = ok;
  openModal('confirm-modal');
  return new Promise((resolve) => { confirmResolve = resolve; });
}

/* ==========================================================================
   Menus (agent, model, profile)
   ========================================================================== */
const MENUS = { 'agent-menu': 'agent-btn', 'model-menu': 'model-btn', 'profile-menu': 'profile-btn' };
function toggleMenu(id) {
  const menu = $('#' + id);
  const open = !menu.classList.contains('open');
  closeMenus();
  if (open) {
    menu.classList.add('open');
    $('#' + MENUS[id]).setAttribute('aria-expanded', 'true');
    (menu.querySelector('.selected') || menu.querySelector('.menu-item'))?.focus();
  }
}
function closeMenus() {
  Object.entries(MENUS).forEach(([m, b]) => {
    $('#' + m).classList.remove('open');
    $('#' + b).setAttribute('aria-expanded', 'false');
  });
}

function agents() { return state.config?.agents?.length ? state.config.agents : FALLBACK_AGENTS; }

function renderAgentMenu() {
  $('#agent-menu').innerHTML = '<div class="menu-title">Agent</div>' + agents().map((a) => {
    const sel = a.key === state.agent;
    return `<button class="menu-item${sel ? ' selected' : ''}" role="option" aria-selected="${sel}" data-action="pick-agent" data-key="${esc(a.key)}">
      <span class="mi-icon">${icon(AGENT_ICONS[a.icon] || 'sparkles')}</span>
      <span class="mi-text"><span class="mi-name">${esc(a.name)}</span><span class="mi-desc">${esc(a.description)}</span></span>
      <span class="mi-check">${icon('check')}</span></button>`;
  }).join('');
  const current = agents().find((a) => a.key === state.agent) || agents()[0];
  $('#agent-label').textContent = current.name;
}
function setAgent(key) {
  state.agent = agents().some((a) => a.key === key) ? key : 'general';
  renderAgentMenu();
}

function renderModelMenu() {
  const models = state.config?.models || [];
  const menu = $('#model-menu');
  if (!models.length) {
    menu.innerHTML = '<div class="menu-title">No models configured on the server</div>';
    $('#model-label').textContent = 'No model';
    return;
  }
  menu.innerHTML = '<div class="menu-title">Model</div>' + models.map((m) => {
    const sel = m.id === state.model;
    return `<button class="menu-item${sel ? ' selected' : ''}" role="option" aria-selected="${sel}" data-action="pick-model" data-id="${esc(m.id)}">
      <span class="mi-text"><span class="mi-name">${esc(m.name)}</span><span class="mi-desc">${esc(m.description)}</span></span>
      <span class="mi-check">${icon('check')}</span></button>`;
  }).join('');
  $('#model-label').textContent = models.find((m) => m.id === state.model)?.name || 'Model';
}
function setModel(id) {
  state.model = id;
  state.settings.model = id;
  saveSettings();
  renderModelMenu();
}

/* ==========================================================================
   Sidebar / conversations
   ========================================================================== */
const getConv = (id) => state.conversations.find((c) => c.thread_id === id);

async function loadConversations() {
  try {
    const d = await api('/conversations');
    state.conversations = d.conversations || [];
  } catch (e) {
    toast('Could not load chats: ' + e.message, 'error');
  }
  state.convLoaded = true;
  renderConvList();
}

function groupLabel(iso) {
  const d = new Date(iso);
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const diff = (today - new Date(d.getFullYear(), d.getMonth(), d.getDate())) / 86400000;
  if (diff <= 0) return 'Today';
  if (diff === 1) return 'Yesterday';
  if (diff <= 7) return 'Previous 7 days';
  if (diff <= 30) return 'Previous 30 days';
  return d.toLocaleDateString([], { month: 'long', year: 'numeric' });
}

function renderConvList() {
  const list = $('#conv-list');
  if (!state.convLoaded) {
    list.innerHTML = '<div class="skeleton"></div>'.repeat(6);
    return;
  }
  const q = state.search.trim().toLowerCase();
  const items = q ? state.conversations.filter((c) => c.title.toLowerCase().includes(q)) : state.conversations;
  if (!items.length) {
    list.innerHTML = `<div class="conv-empty">${q ? 'No chats match your search' : 'No chats yet.<br>Start a conversation!'}</div>`;
    return;
  }
  let html = '', lastGroup = '';
  for (const c of items) {
    const g = groupLabel(c.updated_at || c.created_at);
    if (g !== lastGroup) { html += `<div class="conv-group">${esc(g)}</div>`; lastGroup = g; }
    const active = c.thread_id === state.currentId;
    const live = state.stream && state.stream.threadId === c.thread_id;
    html += `<div class="conv-item${active ? ' active' : ''}">
      <button class="conv-link" data-action="open-chat" data-id="${esc(c.thread_id)}" ${active ? 'aria-current="page"' : ''} title="${esc(c.title)}">${esc(c.title)}</button>
      ${live ? '<span class="pulse" title="Generating"></span>' : ''}
      <div class="conv-actions">
        <button class="icon-btn" data-action="rename-chat" data-id="${esc(c.thread_id)}" title="Rename" aria-label="Rename chat">${icon('pencil', 'sm')}</button>
        <button class="icon-btn danger" data-action="delete-chat" data-id="${esc(c.thread_id)}" title="Delete" aria-label="Delete chat">${icon('trash', 'sm')}</button>
      </div></div>`;
  }
  list.innerHTML = html;
}

function toggleSidebar(force) {
  const app = $('#app');
  if (isMobile()) {
    app.classList.toggle('sidebar-open', force ?? !app.classList.contains('sidebar-open'));
  } else {
    const collapsed = force === undefined ? !app.classList.contains('sidebar-collapsed') : !force;
    app.classList.toggle('sidebar-collapsed', collapsed);
    state.settings.sidebarCollapsed = collapsed;
    saveSettings();
  }
}
const closeSidebarMobile = () => { if (isMobile()) $('#app').classList.remove('sidebar-open'); };

function setUrl(id) {
  const target = id ? `#/c/${id}` : '';
  if (location.hash !== target) history.pushState(null, '', id ? target : location.pathname + location.search);
}

async function openConversation(id, { push = true } = {}) {
  if (state.currentId === id && (state.messages.length || state.stream)) { closeSidebarMobile(); return; }
  if (state.stream) stopStreaming();

  state.currentId = id;
  const conv = getConv(id);
  setAgent(conv?.agent || state.settings.defaultAgent);
  if (push) setUrl(id);
  document.title = (conv?.title || 'Chat') + ' · KaleemGPT';
  renderConvList();
  closeSidebarMobile();

  const cached = historyCache.get(id);
  state.messages = cached || [];
  if (cached) renderChat(); else renderChatLoading();

  try {
    const d = await api(`/history/${encodeURIComponent(id)}`);
    if (state.currentId !== id || state.stream?.threadId === id) return;
    state.messages = (d.messages || []).map((m) => ({ ...m, key: String(m.id) }));
    historyCache.set(id, state.messages);
    renderChat();
  } catch (e) {
    if (state.currentId === id) { toast('Could not load this chat: ' + e.message, 'error'); renderChat(); }
  }
}

function newChat({ push = true } = {}) {
  if (state.stream) stopStreaming();
  state.currentId = null;
  state.messages = [];
  setAgent(state.settings.defaultAgent);
  if (push) setUrl(null);
  document.title = 'KaleemGPT';
  renderChat();
  renderConvList();
  closeSidebarMobile();
  $('#input').focus();
}

function routeFromUrl() {
  const m = location.hash.match(/^#\/c\/([A-Za-z0-9_-]{1,64})$/);
  if (m) openConversation(m[1], { push: false });
  else if (state.currentId) newChat({ push: false });
}

async function renameChat(id) {
  const conv = getConv(id);
  if (!conv) return;
  renameTarget = id;
  $('#rename-input').value = conv.title;
  openModal('rename-modal');
  setTimeout(() => $('#rename-input').select(), 70);
}
let renameTarget = null;
async function submitRename() {
  const title = $('#rename-input').value.trim();
  const id = renameTarget;
  if (!title || !id) return;
  closeModal($('#rename-modal'));
  try {
    const updated = await api(`/conversations/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify({ title }) });
    const conv = getConv(id);
    if (conv) conv.title = updated.title;
    if (state.currentId === id) document.title = updated.title + ' · KaleemGPT';
    renderConvList();
  } catch (e) { toast('Rename failed: ' + e.message, 'error'); }
}

async function deleteChat(id) {
  const conv = getConv(id);
  const ok = await confirmDialog('Delete chat?', `"${conv?.title || 'This chat'}" and its uploaded documents will be permanently deleted.`);
  if (!ok) return;
  try {
    if (state.stream?.threadId === id) stopStreaming();
    await api(`/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' });
    state.conversations = state.conversations.filter((c) => c.thread_id !== id);
    historyCache.delete(id);
    if (state.currentId === id) newChat(); else renderConvList();
    toast('Chat deleted', 'success');
  } catch (e) { toast('Delete failed: ' + e.message, 'error'); }
}

/* ==========================================================================
   Chat rendering
   ========================================================================== */
const chatScroll = () => $('#chat-scroll');

function scrollToBottom(force = false) {
  if (force) state.stick = true;
  if (!state.stick) return;
  const el = chatScroll();
  el.scrollTop = el.scrollHeight;
}

function welcomeHTML() {
  const name = (state.settings.displayName || '').trim();
  const noModels = state.config && !state.config.models?.length;
  const notice = noModels
    ? `<div class="notice">${icon('alert')}<div><strong>No AI model is configured.</strong> Set <code>GROQ_API_KEY</code> and/or <code>GEMINI_API_KEY</code> in the server's <code>.env</code> and restart.</div></div>`
    : '';
  return `<div class="welcome">
    <div class="welcome-mark">K</div>
    <h1>${name ? `How can I help, ${esc(name)}?` : 'How can I help you today?'}</h1>
    <p>Ask anything, search the web, or upload a document to chat with it.</p>
    ${notice}
    <div class="suggestions">
      ${SUGGESTIONS.map((s, i) => `<button class="suggestion" data-action="suggestion" data-i="${i}">
        <span class="s-icon">${icon(s.icon)}</span>
        <span><span class="s-title">${esc(s.title)}</span><span class="s-sub">${esc(s.sub)}</span></span></button>`).join('')}
    </div></div>`;
}

function renderChatLoading() {
  $('#chat-inner').innerHTML = '<div style="padding-top:24px">' + '<div class="skeleton" style="height:56px;margin:18px 0"></div>'.repeat(3) + '</div>';
}

function filePill(name, extra = '') {
  return `<span class="file-pill"><span class="fp-icon">${icon('file', 'sm')}</span><span style="min-width:0"><span class="fp-name">${esc(name)}</span>${extra}</span></span>`;
}

function assistantActions(m, isLast) {
  return `<div class="msg-actions">
    <button class="icon-btn" data-action="copy-msg" title="Copy" aria-label="Copy">${icon('copy', 'sm')}</button>
    <button class="icon-btn" data-action="speak-msg" title="Read aloud" aria-label="Read aloud">${icon('volume', 'sm')}</button>
    ${isLast ? `<button class="icon-btn" data-action="retry" title="Regenerate" aria-label="Regenerate">${icon('refresh', 'sm')}</button>` : ''}
  </div>`;
}

function messageHTML(m, isLast) {
  const meta = state.settings.showTimestamps && m.created_at ? `<div class="msg-meta">${esc(fmtTime(m.created_at))}</div>` : '';
  if (m.role === 'user') {
    const files = m.attachments?.length ? `<div class="msg-files">${m.attachments.map((n) => filePill(n)).join('')}</div>` : '';
    return `<div class="msg user" data-key="${esc(m.key)}"><div class="msg-body">${files}
      <div class="bubble">${esc(m.content)}</div>${meta}
      <div class="msg-actions"><button class="icon-btn" data-action="copy-msg" title="Copy" aria-label="Copy">${icon('copy', 'sm')}</button></div>
      </div></div>`;
  }
  const key = `${state.settings.markdown ? 'md' : 'txt'}`;
  if (m._htmlKey !== key) { m._html = renderMarkdown(m.content); m._htmlKey = key; }
  return `<div class="msg assistant${isLast ? ' last' : ''}" data-key="${esc(m.key)}">
    <div class="msg-avatar">K</div>
    <div class="msg-body"><div class="md">${m._html}</div>${meta}${assistantActions(m, isLast)}</div></div>`;
}

function renderChat() {
  const inner = $('#chat-inner');
  if (!state.messages.length) {
    inner.innerHTML = welcomeHTML();
    chatScroll().scrollTop = 0;
    return;
  }
  const n = state.messages.length;
  inner.innerHTML = state.messages.map((m, i) => messageHTML(m, i === n - 1 && m.role === 'assistant')).join('');
  scrollToBottom(true);
}

function appendUserMessage(m) {
  const inner = $('#chat-inner');
  if (inner.querySelector('.welcome') || state.messages.length === 1) inner.innerHTML = '';
  $$('.msg.last', inner).forEach((el) => {
    el.classList.remove('last');
    el.querySelector('[data-action="retry"]')?.remove();
  });
  inner.insertAdjacentHTML('beforeend', messageHTML(m, false));
  inner.lastElementChild.classList.add('enter');
  scrollToBottom(true);
}

/* ==========================================================================
   Sending & streaming
   ========================================================================== */
function createStreamView() {
  const el = document.createElement('div');
  el.className = 'msg assistant enter';
  el.innerHTML = `<div class="msg-avatar">K</div><div class="msg-body">
    <div class="status-slot"></div>
    <div class="md"><div class="typing"><span></span><span></span><span></span></div></div></div>`;
  $('#chat-inner').append(el);
  scrollToBottom(true);
  return { el, md: el.querySelector('.md'), status: el.querySelector('.status-slot'), text: '', raf: 0, error: null, stopped: false, messageId: null };
}

function setStatus(view, text) {
  view.status.innerHTML = text ? `<div class="status-pill">${icon('loader', 'sm')}<span>${esc(text)}</span></div>` : '';
  if (text) scrollToBottom();
}

function paintStream(view) {
  view.raf = 0;
  view.md.classList.remove('cursor');
  view.md.innerHTML = renderMarkdown(view.text, { highlight: false });
  let n = view.md;
  while (n.lastElementChild && !['PRE', 'TABLE', 'UL', 'OL'].includes(n.lastElementChild.tagName) && !n.lastElementChild.classList.contains('code-block') && !n.lastElementChild.classList.contains('table-wrap')) {
    n = n.lastElementChild;
  }
  n.classList.add('cursor');
  scrollToBottom();
}
// Coalesce tokens into at most one markdown render per animation frame.
function scheduleRender(view) {
  if (!view.raf) view.raf = requestAnimationFrame(() => paintStream(view));
}

function updateSendState() {
  const btn = $('#send-btn');
  if (state.stream) {
    btn.innerHTML = icon('stop');
    btn.disabled = false;
    btn.classList.add('stop');
    btn.setAttribute('aria-label', 'Stop generating');
    btn.title = 'Stop generating';
  } else {
    btn.innerHTML = icon('arrow-up');
    btn.classList.remove('stop');
    btn.disabled = !$('#input').value.trim() && !state.attachments.length;
    btn.setAttribute('aria-label', 'Send message');
    btn.title = 'Send message';
  }
}

function stopStreaming() {
  if (!state.stream) return;
  state.stream.view.stopped = true;
  state.stream.controller.abort();
}

async function readStream(res, view) {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  const handle = (block) => {
    const data = block.split('\n').filter((l) => l.startsWith('data:')).map((l) => l.slice(5).trimStart()).join('\n');
    if (!data) return;
    let evt;
    try { evt = JSON.parse(data); } catch { return; }
    if (evt.status) setStatus(view, evt.status + '…');
    if (evt.token) {
      if (!view.text) setStatus(view, '');
      view.text += evt.token;
      scheduleRender(view);
    }
    if (evt.error) view.error = evt.error;
    if (evt.message_id) view.messageId = evt.message_id;
  };
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf('\n\n')) >= 0) { handle(buf.slice(0, i)); buf = buf.slice(i + 2); }
  }
  if (buf.trim()) handle(buf);
}

async function send({ regenerate = false } = {}) {
  if (state.stream) return;
  const input = $('#input');
  const text = regenerate ? '' : input.value.trim();
  const files = regenerate ? [] : state.attachments.slice();
  if (!regenerate && !text && !files.length) return;
  if (!state.config?.models?.length) { toast('No AI model is configured on the server.', 'error'); return; }
  if (state.recording) stopVoice();
  stopSpeaking();

  let threadId = state.currentId;
  if (!threadId) {
    threadId = newId();
    state.currentId = threadId;
    setUrl(threadId);
  }
  const messages = state.messages;
  const message = text || (files.length ? `Please summarize the attached document${files.length > 1 ? 's' : ''}.` : '');

  if (!regenerate) {
    const userMsg = { key: newId(), role: 'user', content: message, attachments: files.map((f) => f.file.name), created_at: nowISO() };
    messages.push(userMsg);
    input.value = '';
    autosize();
    state.attachments = [];
    renderAttachments();
    appendUserMessage(userMsg);

    let conv = getConv(threadId);
    if (!conv) {
      conv = { thread_id: threadId, title: makeTitle(message), agent: state.agent, created_at: nowISO() };
      state.conversations.unshift(conv);
      document.title = conv.title + ' · KaleemGPT';
    } else {
      state.conversations = [conv, ...state.conversations.filter((c) => c !== conv)];
    }
    conv.updated_at = nowISO();
  }

  const view = createStreamView();
  const controller = new AbortController();
  state.stream = { controller, threadId, view };
  updateSendState();
  renderConvList();

  try {
    // 1) Upload attachments (indexed into the conversation's document store).
    const uploaded = [];
    for (const [i, f] of files.entries()) {
      setStatus(view, files.length > 1 ? `Reading ${f.file.name} (${i + 1}/${files.length})` : `Reading ${f.file.name}`);
      const fd = new FormData();
      fd.append('file', f.file);
      fd.append('thread_id', threadId);
      try {
        await api('/upload', { method: 'POST', body: fd, signal: controller.signal });
        uploaded.push(f.file.name);
      } catch (e) {
        if (e.name === 'AbortError') throw e;
        toast(`${f.file.name}: ${e.message}`, 'error', 5000);
      }
    }
    if (files.length && !uploaded.length && !text) throw new Error('None of the files could be processed.');
    setStatus(view, '');

    // 2) Stream the answer.
    const res = await fetch('/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, thread_id: threadId, model: state.model, agent: state.agent, attachments: uploaded, regenerate }),
      signal: controller.signal,
    });
    if (!res.ok) {
      let d = null;
      try { d = await res.json(); } catch { /* not json */ }
      throw new Error((d && (d.error || d.detail)) || `Server error (${res.status})`);
    }
    await readStream(res, view);
  } catch (e) {
    if (e.name !== 'AbortError') view.error = e.message || 'Network error';
  } finally {
    finishStream(view, threadId, messages);
  }
}

function finishStream(view, threadId, messages) {
  cancelAnimationFrame(view.raf);
  view.md.classList.remove('cursor');
  state.stream = null;
  updateSendState();
  setStatus(view, '');

  let msg = null;
  if (view.text.trim()) {
    msg = { key: newId(), id: view.messageId, role: 'assistant', content: view.text, created_at: nowISO() };
    messages.push(msg);
  }

  if (state.currentId !== threadId) {
    historyCache.delete(threadId); // we navigated away; reload from server next time
  } else {
    historyCache.set(threadId, messages);
    if (msg) {
      msg._html = renderMarkdown(msg.content);
      msg._htmlKey = state.settings.markdown ? 'md' : 'txt';
      view.md.innerHTML = msg._html;
      view.el.dataset.key = msg.key;
      view.el.classList.add('last');
      const meta = state.settings.showTimestamps ? `<div class="msg-meta">${esc(fmtTime(msg.created_at))}</div>` : '';
      view.md.insertAdjacentHTML('afterend', meta + assistantActions(msg, true));
    } else {
      view.md.innerHTML = '';
    }
    if (view.stopped && msg) view.md.insertAdjacentHTML('afterend', '<div class="stopped-note">Stopped</div>');
    if (view.error) {
      view.el.classList.add('errored');
      view.md.insertAdjacentHTML('afterend', `<div class="msg-error">${icon('alert')}<div><div>${esc(view.error)}</div>
        <button class="btn btn-ghost" style="height:30px;margin-top:8px" data-action="retry">${icon('refresh', 'sm')} Try again</button></div></div>`);
    }
    if (!msg && !view.error) view.el.remove();
    scrollToBottom();
    if (msg && state.settings.voiceOutput && !view.stopped) speak(msg.content, view.el.querySelector('[data-action="speak-msg"]'));
  }
  loadConversations(); // sync titles / ordering with the server
}

function regenerate() {
  if (state.stream) return;
  const inner = $('#chat-inner');
  const last = state.messages[state.messages.length - 1];
  if (last && last.role === 'assistant') {
    state.messages.pop();
    inner.querySelector(`.msg[data-key="${CSS.escape(last.key)}"]`)?.remove();
  }
  $$('.msg.errored', inner).forEach((el) => el.remove());
  if (!state.messages.length) return;
  send({ regenerate: true });
}

/* ==========================================================================
   Attachments
   ========================================================================== */
function addFiles(list) {
  const cfg = state.config || {};
  if (!cfg.features?.documents) { toast('Document upload is not configured on the server (GEMINI_API_KEY).', 'error', 4500); return; }
  const exts = cfg.upload?.extensions || [];
  const maxMb = cfg.upload?.max_mb || 20;
  for (const file of list) {
    if (state.attachments.length >= 5) { toast('You can attach up to 5 files at a time.'); break; }
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (exts.length && !exts.includes(ext)) { toast(`${file.name}: unsupported file type`, 'error'); continue; }
    if (file.size > maxMb * 1048576) { toast(`${file.name} is larger than ${maxMb} MB`, 'error'); continue; }
    state.attachments.push({ key: newId(), file });
  }
  renderAttachments();
  $('#input').focus();
}
function renderAttachments() {
  $('#attachments').innerHTML = state.attachments.map((a) => `
    <span class="file-pill"><span class="fp-icon">${icon('file', 'sm')}</span>
      <span style="min-width:0"><span class="fp-name">${esc(a.file.name)}</span><span class="fp-meta">${esc(a.file.name.split('.').pop().toUpperCase())} · ${fmtSize(a.file.size)}</span></span>
      <button type="button" class="icon-btn rm" data-action="remove-file" data-key="${a.key}" aria-label="Remove ${esc(a.file.name)}">${icon('x', 'sm')}</button>
    </span>`).join('');
  updateSendState();
}

/* ==========================================================================
   Voice input / output
   ========================================================================== */
let recog = null;
function setRecording(on) {
  state.recording = on;
  $('#voice-btn').classList.toggle('recording', on);
  $('#voice-live').classList.toggle('hidden', !on);
}
function stopVoice() { try { recog?.stop(); } catch { /* already stopped */ } setRecording(false); }

function toggleVoice() {
  if (state.recording) { stopVoice(); return; }
  if (!state.settings.voiceInput) { toast('Voice input is turned off in Settings.'); return; }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { toast("Voice input isn't supported in this browser. Try Chrome or Edge.", 'error'); return; }
  if (!window.isSecureContext) { toast('Voice input needs HTTPS (or localhost).', 'error'); return; }

  const input = $('#input');
  const base = input.value ? input.value.replace(/\s*$/, ' ') : '';
  recog = new SR();
  recog.continuous = true;
  recog.interimResults = true;
  recog.lang = navigator.language || 'en-US';
  recog.onresult = (e) => {
    let t = '';
    for (let i = 0; i < e.results.length; i++) t += e.results[i][0].transcript;
    input.value = base + t;
    autosize();
    updateSendState();
  };
  recog.onerror = (e) => {
    if (e.error === 'not-allowed' || e.error === 'service-not-allowed') toast('Microphone access was blocked.', 'error');
    else if (!['aborted', 'no-speech'].includes(e.error)) toast('Voice input error: ' + e.error, 'error');
  };
  recog.onend = () => setRecording(false);
  try { recog.start(); setRecording(true); } catch (e) { toast('Could not start voice input.', 'error'); }
}

let currentUtterance = null, speakingBtn = null;
function stopSpeaking() {
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  speakingBtn?.classList.remove('on');
  speakingBtn = null;
  currentUtterance = null;
}
function speak(text, btn) {
  if (!('speechSynthesis' in window)) { toast('Text-to-speech is not supported in this browser.', 'error'); return; }
  const toggleOff = btn && btn === speakingBtn;
  stopSpeaking();
  if (toggleOff) return;
  const clean = String(text)
    .replace(/```[\s\S]*?```/g, ' (code block) ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/[#*_>~|]/g, '')
    .replace(/\n{2,}/g, '. ')
    .replace(/\s+/g, ' ')
    .trim();
  const u = new SpeechSynthesisUtterance(clean);
  u.rate = parseFloat(state.settings.speechRate) || 1;
  const voice = speechSynthesis.getVoices().find((v) => v.voiceURI === state.settings.voiceURI);
  if (voice) u.voice = voice;
  const done = () => { if (currentUtterance === u) { speakingBtn?.classList.remove('on'); speakingBtn = null; currentUtterance = null; } };
  u.onend = done;
  u.onerror = done;
  currentUtterance = u;
  speakingBtn = btn || null;
  btn?.classList.add('on');
  speechSynthesis.speak(u);
}
function populateVoices() {
  if (!('speechSynthesis' in window)) return;
  const sel = $('#voice-select');
  const voices = speechSynthesis.getVoices();
  sel.innerHTML = '<option value="">System default</option>' + voices.map((v) =>
    `<option value="${esc(v.voiceURI)}">${esc(v.name)} (${esc(v.lang)})</option>`).join('');
  sel.value = state.settings.voiceURI || '';
}

/* ==========================================================================
   Clipboard
   ========================================================================== */
async function copyText(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(text); return true; }
  } catch { /* fall back */ }
  // Fallback for plain-HTTP deployments where the Clipboard API is unavailable.
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.setAttribute('readonly', '');
  ta.style.cssText = 'position:fixed;top:-1000px;opacity:0';
  document.body.append(ta);
  ta.select();
  let ok = false;
  try { ok = document.execCommand('copy'); } catch { /* ignore */ }
  ta.remove();
  return ok;
}

const msgByEl = (el) => {
  const key = el.closest('.msg')?.dataset.key;
  return state.messages.find((m) => m.key === key);
};

/* ==========================================================================
   Settings modal
   ========================================================================== */
function openSettings(tab = 'general') {
  $$('[data-setting]').forEach((el) => {
    const v = state.settings[el.dataset.setting];
    if (el.type === 'checkbox') el.checked = !!v; else el.value = v ?? '';
  });
  $('#default-agent-select').innerHTML = agents().map((a) => `<option value="${esc(a.key)}">${esc(a.name)}</option>`).join('');
  $('#default-agent-select').value = state.settings.defaultAgent;
  populateVoices();
  selectSettingsTab(tab);
  openModal('settings-modal');
}
function selectSettingsTab(tab) {
  $$('.settings-tab').forEach((t) => t.setAttribute('aria-selected', String(t.dataset.tab === tab)));
  $$('.settings-panel').forEach((p) => p.classList.toggle('hidden', p.dataset.panel !== tab));
  if (tab === 'memory') loadMemories();
}
function onSettingChange(el) {
  const key = el.dataset.setting;
  state.settings[key] = el.type === 'checkbox' ? el.checked : el.value;
  saveSettings();
  if (key === 'theme') applyTheme();
  if (key === 'displayName') { applyProfile(); if (!state.messages.length) renderChat(); }
  if (key === 'markdown' || key === 'showTimestamps') if (!state.stream) renderChat();
  if (key === 'defaultAgent' && !state.currentId) setAgent(el.value);
}

async function loadMemories() {
  const list = $('#memory-list');
  list.innerHTML = '<div class="skeleton"></div><div class="skeleton"></div>';
  try {
    const { memories } = await api('/memories');
    list.innerHTML = memories.length
      ? memories.map((m) => `<div class="memory-item"><p>${esc(m.memory)}</p>
          <button class="icon-btn" data-action="delete-memory" data-id="${m.id}" title="Forget" aria-label="Forget this">${icon('trash', 'sm')}</button></div>`).join('')
      : '<div class="conv-empty">Nothing saved yet. Try: "Remember that I live in Lahore."</div>';
  } catch (e) {
    list.innerHTML = `<div class="conv-empty">Could not load memories: ${esc(e.message)}</div>`;
  }
}

/* ==========================================================================
   Composer helpers
   ========================================================================== */
function autosize() {
  const ta = $('#input');
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 220) + 'px';
}

function useSuggestion(i) {
  const s = SUGGESTIONS[i];
  if (!s) return;
  if (s.agent) setAgent(s.agent);
  if (s.attach) { $('#file-input').click(); return; }
  const input = $('#input');
  input.value = s.prompt;
  autosize();
  updateSendState();
  input.focus();
  const p = s.prompt.indexOf('\n\n```');
  const pos = p >= 0 ? s.prompt.indexOf('\n', p + 5) + 1 : s.prompt.length;
  input.setSelectionRange(pos, pos);
}

/* ==========================================================================
   Events
   ========================================================================== */
const ACTIONS = {
  'new-chat': () => newChat(),
  'toggle-sidebar': () => toggleSidebar(),
  'close-sidebar': () => closeSidebarMobile(),
  'open-chat': (el) => openConversation(el.dataset.id),
  'rename-chat': (el) => renameChat(el.dataset.id),
  'delete-chat': (el) => deleteChat(el.dataset.id),
  'toggle-agent-menu': () => toggleMenu('agent-menu'),
  'toggle-model-menu': () => toggleMenu('model-menu'),
  'toggle-profile': () => toggleMenu('profile-menu'),
  'pick-agent': (el) => { setAgent(el.dataset.key); closeMenus(); $('#input').focus(); },
  'pick-model': (el) => { setModel(el.dataset.id); closeMenus(); $('#input').focus(); },
  'toggle-theme': () => { toggleTheme(); closeMenus(); },
  'open-settings': (el) => openSettings(el.dataset.tab),
  'settings-tab': (el) => selectSettingsTab(el.dataset.tab),
  'close-modal': (el) => closeModal(el),
  attach: () => $('#file-input').click(),
  'remove-file': (el) => { state.attachments = state.attachments.filter((a) => a.key !== el.dataset.key); renderAttachments(); },
  voice: () => toggleVoice(),
  suggestion: (el) => useSuggestion(+el.dataset.i),
  'scroll-bottom': () => { const s = chatScroll(); state.stick = true; s.scrollTo({ top: s.scrollHeight, behavior: 'smooth' }); },
  retry: () => regenerate(),
  'copy-msg': async (el) => {
    const m = msgByEl(el);
    if (m && await copyText(m.content)) {
      el.innerHTML = icon('check', 'sm');
      setTimeout(() => { el.innerHTML = icon('copy', 'sm'); }, 1500);
    }
  },
  'speak-msg': (el) => { const m = msgByEl(el); if (m) speak(m.content, el); },
  'copy-code': async (el) => {
    const code = el.closest('.code-block')?.querySelector('code')?.innerText || '';
    if (await copyText(code)) {
      el.classList.add('copied');
      el.innerHTML = `${icon('check', 'sm')}<span>Copied</span>`;
      setTimeout(() => { el.classList.remove('copied'); el.innerHTML = `${icon('copy', 'sm')}<span>Copy</span>`; }, 1600);
    }
  },
  'delete-memory': async (el) => {
    try { await api(`/memories/${el.dataset.id}`, { method: 'DELETE' }); el.closest('.memory-item').remove(); toast('Forgotten', 'success'); }
    catch (e) { toast(e.message, 'error'); }
  },
  'delete-all': async () => {
    const ok = await confirmDialog('Delete all chats?', 'Every conversation and uploaded document will be permanently deleted. Saved memories are kept.', 'Delete all');
    if (!ok) return;
    try {
      if (state.stream) stopStreaming();
      await api('/conversations', { method: 'DELETE' });
      state.conversations = [];
      historyCache.clear();
      closeModal($('#settings-modal'));
      newChat();
      toast('All chats deleted', 'success');
    } catch (e) { toast(e.message, 'error'); }
  },
  'reset-settings': () => {
    try { localStorage.removeItem(SETTINGS_KEY); } catch { /* ignore */ }
    state.settings = { ...DEFAULT_SETTINGS, model: state.model };
    applyTheme(); applyProfile(); openSettings('data'); renderChat();
    toast('Preferences reset', 'success');
  },
};

function bindEvents() {
  document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action]');
    if (el) {
      // Rendered model output may only trigger "copy code" (defence against injected buttons).
      if (el.closest('.md') && el.dataset.action !== 'copy-code') return;
      const fn = ACTIONS[el.dataset.action];
      if (fn) { e.preventDefault(); fn(el, e); }
    }
    if (!e.target.closest('.menu, #agent-btn, #model-btn, #profile-btn')) closeMenus();
  });

  // Close a modal when clicking its backdrop.
  $$('.modal-backdrop').forEach((m) => m.addEventListener('mousedown', (e) => { if (e.target === m) closeModal(m); }));
  $('#confirm-ok').addEventListener('click', () => { const r = confirmResolve; confirmResolve = null; closeModal($('#confirm-modal')); r?.(true); });
  $('#confirm-cancel').addEventListener('click', () => closeModal($('#confirm-modal')));
  $('#rename-form').addEventListener('submit', (e) => { e.preventDefault(); submitRename(); });

  $$('[data-setting]').forEach((el) => el.addEventListener('change', () => onSettingChange(el)));

  // Composer
  const input = $('#input');
  $('#composer').addEventListener('submit', (e) => { e.preventDefault(); state.stream ? stopStreaming() : send(); });
  input.addEventListener('input', () => { autosize(); updateSendState(); });
  input.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' || e.isComposing || e.keyCode === 229) return;
    const sendCombo = state.settings.enterToSend ? !e.shiftKey : (e.ctrlKey || e.metaKey);
    if (sendCombo && !isMobile()) { e.preventDefault(); if (!state.stream) send(); }
  });
  input.addEventListener('paste', (e) => {
    const files = Array.from(e.clipboardData?.files || []);
    if (files.length) { e.preventDefault(); addFiles(files); }
  });
  $('#file-input').addEventListener('change', (e) => { addFiles(e.target.files); e.target.value = ''; });

  // Drag & drop
  const main = $('#main'), overlay = $('#drop-overlay');
  let depth = 0;
  const hasFiles = (e) => Array.from(e.dataTransfer?.types || []).includes('Files');
  main.addEventListener('dragenter', (e) => { if (!hasFiles(e)) return; e.preventDefault(); depth++; overlay.classList.add('show'); });
  main.addEventListener('dragover', (e) => { if (hasFiles(e)) e.preventDefault(); });
  main.addEventListener('dragleave', () => { depth = Math.max(0, depth - 1); if (!depth) overlay.classList.remove('show'); });
  main.addEventListener('drop', (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault(); depth = 0; overlay.classList.remove('show');
    addFiles(e.dataTransfer.files);
  });

  // Scroll: follow the stream only while the user is at the bottom.
  const scroller = chatScroll();
  scroller.addEventListener('scroll', () => {
    const d = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
    state.stick = d < 80;
    $('#scroll-down').classList.toggle('show', d > 240);
  }, { passive: true });

  $('#search-input').addEventListener('input', debounce((e) => { state.search = e.target.value; renderConvList(); }, 120));

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      if (isMobile()) toggleSidebar(true); else if ($('#app').classList.contains('sidebar-collapsed')) toggleSidebar(true);
      $('#search-input').focus();
    } else if (mod && e.shiftKey && e.key.toLowerCase() === 'o') {
      e.preventDefault();
      newChat();
    } else if (e.key === 'Escape') {
      if (openModalEl()) closeModal(openModalEl());
      else if ($('.menu.open')) closeMenus();
      else closeSidebarMobile();
    }
  });

  window.addEventListener('popstate', routeFromUrl);
  window.addEventListener('resize', debounce(() => { if (!isMobile()) $('#app').classList.remove('sidebar-open'); }, 150));
  if ('speechSynthesis' in window) speechSynthesis.addEventListener?.('voiceschanged', populateVoices);
}

/* ==========================================================================
   Boot
   ========================================================================== */
async function init() {
  loadSettings();
  hydrateIcons();
  applyTheme();
  applyProfile();
  setupMarkdown();
  if (state.settings.sidebarCollapsed && !isMobile()) $('#app').classList.add('sidebar-collapsed');
  bindEvents();
  setAgent(state.settings.defaultAgent);
  renderConvList();
  if (/^#\/c\//.test(location.hash)) renderChatLoading(); else renderChat();
  updateSendState();

  try {
    state.config = await api('/config');
  } catch (e) {
    state.config = { models: [], agents: FALLBACK_AGENTS, features: {}, upload: { extensions: [], max_mb: 20 } };
    toast('Could not reach the server.', 'error');
  }
  const ids = state.config.models.map((m) => m.id);
  state.model = ids.includes(state.settings.model) ? state.settings.model : (state.config.default_model || ids[0] || '');
  renderModelMenu();
  setAgent(state.agent);
  const exts = state.config.upload?.extensions || [];
  $('#file-input').accept = exts.join(',');
  $('#drop-hint').textContent = exts.map((x) => x.slice(1).toUpperCase()).join(', ') + ` · up to ${state.config.upload?.max_mb || 20} MB`;
  if (!state.config.features?.documents) {
    $('#attach-btn').title = 'Document upload needs GEMINI_API_KEY on the server';
  }
  if (!state.messages.length && !/^#\/c\//.test(location.hash)) renderChat(); // config-aware welcome

  await loadConversations();
  routeFromUrl();
  if (!isMobile()) $('#input').focus();
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();
})();
