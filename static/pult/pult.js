(() => {
  'use strict';
  // ---------- constants
  // Data comes from the platform (apps/pult) instead of Google Sheets.
  const DS = document.body.dataset;
  const API = { data: DS.apiData, tasks: DS.apiTasks, report: DS.apiReport, plan: DS.apiPlan, planImport: DS.apiImport, sync: DS.apiSync, disc: DS.apiDisc, ciph: DS.apiCiph, ops: DS.apiOps };
  const CSRF = document.querySelector('meta[name="csrf-token"]').content;
  const REFRESH_MS = 60000;
  // Tabs whose data the platform does not provide yet (next integration stages).
  const PAGE_FEATURE = { comp: 'plan', plan: 'plan', money: 'finance', contracts: 'finance' };
  const ACTIVE = ['В работе', 'Есть вопрос', 'На доработке'];
  const WAIT = ['Новая', 'На согласовании', 'На проверке', 'Есть вопрос', 'Согласование'];
  const CLOSED = ['Принята', 'Отменена'];
  const STATUSES = ['Черновик', 'Новая', 'На согласовании', 'В работе', 'Есть вопрос', 'Согласование', 'На проверке', 'На доработке', 'Принята', 'Отменена'];
  const MONTHS = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'];
  const DAY = 86400000;
  const COLORS = { ok: 'var(--ink)', lag: 'var(--warn)', alert: 'var(--bad)', review: 'var(--ok)', done: 'var(--muted-bar)' };

  // ---------- small helpers
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const nf = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });
  const nf1 = new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
  const fNum = (v) => (isNum(v) ? nf.format(v) : '—');
  const fPct = (v) => (isNum(v) ? Math.round(v * 100) + '%' : '—');
  const fMln = (v) => (isNum(v) ? nf1.format(v / 1e6) + ' млн' : '—');
  const fUsd = (v) => (isNum(v) ? '$' + nf.format(v) : '—');
  const pad = (n) => String(n).padStart(2, '0');
  const iso = (d) => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  const parseD = (s) => { if (!s) return null; const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
  const fD = (s) => { const d = parseD(s); return d ? pad(d.getDate()) + '.' + pad(d.getMonth() + 1) + '.' + d.getFullYear() : '—'; };
  const fDs = (d) => pad(d.getDate()) + '.' + pad(d.getMonth() + 1);
  const today = () => { const n = new Date(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); };
  const ruDate = (d) => pad(d.getDate()) + '.' + pad(d.getMonth() + 1) + '.' + d.getFullYear();
  const plural = (n, a, b, c) => { const x = Math.abs(n) % 100, y = x % 10; if (x > 10 && x < 20) return c; if (y > 1 && y < 5) return b; if (y === 1) return a; return c; };
  const str = (v) => (v == null ? '' : String(v).trim());
  const toNum = (v) => {
    let t = str(v).replace(/[\s ]/g, '').replace(/[,.]$/, '');
    if (t === '' ) return null;
    if (t === '-' || t === '—') return 0;
    if (/^-?\d{1,3}(,\d{3})+(\.\d+)?$/.test(t)) t = t.replace(/,/g, '');
    else if (/^-?\d+,\d+$/.test(t)) t = t.replace(',', '.');
    const n = Number(t); return Number.isFinite(n) ? n : null;
  };
  const toPct = (v) => { const t = str(v); if (t === '') return null; if (t.endsWith('%')) { const n = toNum(t.slice(0, -1)); return n == null ? null : n / 100; } return toNum(t); };
  const toDate = (v) => {
    const t = str(v);
    let m = t.match(/^(\d{1,2})[./](\d{1,2})[./](\d{4})/);
    if (m) return m[3] + '-' + m[2].padStart(2, '0') + '-' + m[1].padStart(2, '0');
    m = t.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m) return m[0];
    if (/^\d{5}(\.\d+)?$/.test(t)) { const d = new Date(Math.round((Number(t) - 25569) * DAY)); return d.getUTCFullYear() + '-' + pad(d.getUTCMonth() + 1) + '-' + pad(d.getUTCDate()); }
    return null;
  };
  const fit = (sel, max) => sel.each(function () { while (this.getComputedTextLength() > max && this.textContent.length > 3) this.textContent = this.textContent.slice(0, -2) + '…'; });

  // header-based table parse
  function table(values, map, types = {}, headerRow = 0) {
    const head = values[headerRow] || [];
    const keys = head.map((h) => map[str(h)] || null);
    const missing = Object.entries(map).filter(([, k]) => !keys.includes(k)).map(([h]) => h);
    const rows = values.slice(headerRow + 1).map((r, i) => {
      const o = { _row: headerRow + 2 + i };
      keys.forEach((k, j) => { if (!k) return; const v = r[j]; const t = types[k]; o[k] = t === 'date' ? toDate(v) : t === 'pct' ? toPct(v) : t === 'num' ? toNum(v) : (str(v) === '' ? null : str(v)); });
      return o;
    });
    return { rows, missing };
  }

  // ---------- state
  const S = { raw: {}, payload: null, load: 'loading', loadErr: '', loadedAt: 0, d: {}, tab: 'home', mcp: null, fatal: null, filters: { project: '', person: '' }, gGroup: 'assignee', gDone: false, tSort: ['plan', 1], teamF: 'all', teamOpen: new Set(), kb: { f: { prio: new Set(), proj: new Set(), time: new Set(), who: new Set() }, over: new Map(), multi: false, oldDone: false, drag: null }, pl: { project: '', zoom: 'week', crit: true, base: true, links: true, owners: true, tails: true }, cp: { busy: new Set() }, kbMode: 'proj', pk: { project: '', f: { obj: new Set(), disc: new Set(), who: new Set(), sig: new Set() } }, rep: new Map(), repNote: '', as: null, me: null, meRaw: undefined, started: new Set(), dl: null, tStatus: 'open', cStatus: 'Открыт', kpiMonth: null };
  S.kpiMonth = (() => { const n = new Date(); return n.getFullYear() + '-' + String(n.getMonth() + 1).padStart(2, '0'); })();
  try { const t = localStorage.getItem('gx-tab'); if (t) S.tab = t; const g = localStorage.getItem('gx-group'); if (g) S.gGroup = g; const z = localStorage.getItem('gx-zoom'); if (z) S.pl.zoom = z; if (localStorage.getItem('gx-owners') === '0') S.pl.owners = false; const km = localStorage.getItem('gx-kbmode'); if (km) S.kbMode = km; } catch (e) { /* storage unavailable */ }
  const h = location.hash.slice(1); if (h) S.tab = h;

  // ---------- server payload into S.d (the same shapes the sheets used to give)
  function parseAll() {
    const P = S.payload; if (!P) { S.d = { cal: makeCal(null) }; return; }
    const d = { tasks: P.tasks, progress: P.progress, people: P.people, projects: P.projects, templates: P.templates, kpi: P.kpi, access: P.access, features: P.features || {} };
    d.cal = makeCal(P.calendar);
    d.disc = P.disc || []; d.stages = P.stages || []; d.ciph = new Map((P.ciphers || []).map((r) => [r.project, r]));
    if (d.features.finance) Object.assign(d, { ops: P.ops, contracts: P.contracts, home: P.home, months: P.months, rate: P.rate, lists: P.lists });
    // schedule() reads stages and disciplines through S.d, so publish them first
    S.d = d;
    d.plan = (P.plan || []).filter((r) => isNum(r.id) && r.project); d.planMissing = []; d.planVersion = P.planVersion;
    d.sched = schedule(planSubset(d.plan), d.cal, d.tasks || []);
    resolveMe();
  }

  // ---------- derived
  const noSource = (t) => ACTIVE.includes(t.status) && isNum(t.elapsed) && t.elapsed >= 0.5 && t.source_ok !== 'Да';
  const overdue = (t) => !CLOSED.includes(t.status) && !['На проверке', 'Черновик', 'Новая', 'На согласовании', 'Согласование'].includes(t.status) && t.plan && parseD(t.plan) < today();
  function problem(t) {
    if (t.control === 'ТРЕВОГА 70%') return { text: 'Тревога 70%', cls: 'bad', key: 0 };
    if (overdue(t)) return { text: 'Просрочена', cls: 'bad', key: 1 };
    if (t.control === 'Отстаёт') return { text: 'Отстаёт', cls: 'warn', key: 2 };
    if (noSource(t)) return { text: 'Нет исходника', cls: 'warn', key: 3 };
    if (t.status === 'На проверке') return { text: 'Проверьте работу', cls: 'ink', key: 4 };
    if (t.status === 'Есть вопрос') return { text: 'Есть вопрос', cls: 'warn', key: 5 };
    if (t.status === 'На согласовании') return { text: 'Согласуйте срок', cls: '', key: 6 };
    if (t.status === 'Согласование') return { text: t.approver === 'Заказчик' ? 'У заказчика' : 'Согласование у ГИПа', cls: 'ink', key: 4 };
    if (t.status === 'Новая') return { text: isNum(t.days) && t.days > 0 ? 'Ждёт принятия' : 'Ждёт срока', cls: '', key: 7 };
    if (t.status === 'Черновик') return { text: 'Ждёт ТЗ', cls: '', key: 8 };
    return null;
  }
  const taskColor = (t) => (CLOSED.includes(t.status) ? COLORS.done : t.control === 'ТРЕВОГА 70%' || overdue(t) ? COLORS.alert : t.control === 'Отстаёт' ? COLORS.lag : t.status === 'На проверке' ? COLORS.review : COLORS.ok);
  const fTasks = () => (S.d.tasks || []).filter((t) => (isBoss() || (isGip() && inMyProjects(t.project)) || t.assignee === viewer().person) && (!S.filters.project || t.project === S.filters.project) && (!S.filters.person || t.assignee === S.filters.person));
  const fOps = () => (S.d.ops || []).filter((o) => (!S.filters.project || o.project === S.filters.project) && (!S.filters.person || o.who === S.filters.person));
  const teamPeople = () => (S.d.people || []).filter((p) => p.inTasks === 'Да');
  const personBy = (name) => (S.d.people || []).find((p) => p.name === name);
  const eqUzs = (o) => (o.uzs || 0) + (o.usd || 0) * (S.d.rate || S.d.home?.rate || 0);

  function workload() {
    const tasks = S.d.tasks || []; const T0 = today();
    return teamPeople().map((p) => {
      const mine = tasks.filter((t) => t.assignee === p.name && !CLOSED.includes(t.status));
      const hours = d3.sum(mine, (t) => t.hours || 0); const norm = p.norm || 40;
      return { p, name: p.name, open: mine.length, urgent: mine.filter((t) => t.priority === 1).length, lag: mine.filter((t) => t.control === 'Отстаёт').length,
        alert: mine.filter((t) => t.control === 'ТРЕВОГА 70%').length, overdue: mine.filter(overdue).length, hours, norm, load: norm ? hours / norm : null };
    });
  }
  function kpiRows() {
    const K = S.d.kpi; if (!K || !S.d.tasks) return null;
    const ym = S.kpiMonth; const inMonth = (t) => t.finished && t.finished.slice(0, 7) === ym;
    const names = new Set(teamPeople().map((p) => p.name));
    S.d.tasks.filter((t) => t.status === 'Принята' && inMonth(t) && t.assignee).forEach((t) => names.add(t.assignee));
    const rows = [...names].map((name) => {
      const acc = S.d.tasks.filter((t) => t.assignee === name && t.status === 'Принята' && inMonth(t));
      const pts = acc.map((t) => (isNum(t.points) ? t.points : null)).filter(isNum);
      const sum = d3.sum(pts); const avg = acc.length ? sum / acc.length : null;
      const p = personBy(name);
      let cat = null;
      if (acc.length >= K.minTasks && avg != null) { const lv = K.levels.slice().sort((a, b) => b.min - a.min).find((l) => avg >= l.min); cat = lv ? lv.cat : 'D'; }
      const bonus = cat ? (K.levels.find((l) => l.cat === cat) || {}).bonus ?? 0 : null;
      return { name, pay: p?.pay || '—', accepted: acc.length, early: acc.filter((t) => isNum(t.delay) && t.delay < 0).length, ontime: acc.filter((t) => t.delay === 0).length, late: acc.filter((t) => isNum(t.delay) && t.delay > 0).length,
        reworks: d3.sum(acc, (t) => t.reworks || 0), points: sum, avg, cat, bonus, amount: d3.sum(acc, (t) => t.amount || 0) };
    });
    const ranked = rows.filter((r) => r.cat).sort((a, b) => b.avg - a.avg);
    rows.forEach((r) => { r.place = r.cat ? ranked.filter((x) => x.avg > r.avg).length + 1 : null; });
    return rows.sort((a, b) => (a.place ?? 1e9) - (b.place ?? 1e9) || (b.avg ?? -1e9) - (a.avg ?? -1e9) || a.name.localeCompare(b.name, 'ru'));
  }

  // ---------- data loading from the platform (apps/pult/api)
  // S.load: 'loading' | 'ok' | 'error'; S.loadErr keeps the last error text.
  const status = () => S.load;
  async function apiFetch(url, body) {
    let res;
    try {
      res = await fetch(url, body === undefined ? { credentials: 'same-origin', headers: { Accept: 'application/json' } }
        : { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF, Accept: 'application/json' }, body: JSON.stringify(body) });
    } catch (e) { throw userErr('Сервер не отвечает. Проверьте интернет и нажмите «Обновить».'); }
    if (res.status === 401 || res.redirected) { location.reload(); throw userErr('Сессия истекла, войдите снова.'); }
    let data = null; try { data = await res.json(); } catch (e) { data = null; }
    if (!res.ok || !data || data.ok === false) throw userErr((data && data.error) || `Ошибка сервера (${res.status}).`);
    return data;
  }
  // a request made while another load is in flight may follow a write, so it gets a fresh load of its own
  let loading = null, again = false;
  async function refreshAll() {
    if (loading) { again = true; return loading; }
    loading = (async () => {
      do {
        again = false;
        try { S.payload = await apiFetch(API.data); S.load = 'ok'; S.loadErr = ''; S.loadedAt = Date.now(); }
        catch (e) { if (!S.payload) S.load = 'error'; S.loadErr = e.userText || String(e); }
      } while (again);
      loading = null; scheduleRender();
    })();
    return loading;
  }
  async function boot() {
    S.mcp = true; // writes go through apiFetch; the flag only tells the UI that saving is possible
    // Excel/PDF exports: a plain browser download instead of Claude's downloads capability
    S.dl = { save: async ({ filename, data }) => { const url = URL.createObjectURL(data); const a = el('a'); a.href = url; a.download = filename; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 10000); } };
    await refreshAll();
    setInterval(() => { if (!document.hidden && !$('#modal-root').children.length) refreshAll(); }, REFRESH_MS);
  }
  const taskUrl = (id, what) => API.tasks + id + '/' + what + '/';
  const taskAction = (t, action, params = {}) => apiFetch(taskUrl(t.id, 'action'), { action, params, expect_status: t.status });
  function errText(e) { return (e && (e.userText || e.message)) || 'Не получилось: неизвестная ошибка'; }

  // ---------- toast
  let toastTimer;
  function toast(text) { const root = $('#toast-root'); root.replaceChildren(el('div', 'toast', text)); clearTimeout(toastTimer); toastTimer = setTimeout(() => root.replaceChildren(), 4200); }

  // ---------- rendering
  let rq = false;
  function scheduleRender() { if (rq) return; rq = true; requestAnimationFrame(() => { rq = false; render(); }); }
  function render() {
    parseAll();
    const pages = !S.payload ? ['work'] : allowedPages();
    if (!pages.includes(S.tab)) S.tab = pages[0] || 'work';
    $$('.tab').forEach((b) => { b.hidden = !pages.includes(b.dataset.tab); });
    renderBanner(); renderTop();
    $$('.tab').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.tab === S.tab)));
    $$('main > .page').forEach((p) => { p.hidden = p.id !== 'p-' + S.tab; });
    const fn = { work: renderWork, home: renderHome, tasks: renderTasks, kanban: renderKanban, gantt: renderGantt, comp: renderComp, plan: renderPlan, team: renderTeam, kpi: renderKpi, money: renderMoney, contracts: renderContracts }[S.tab];
    if (fn) fn();
  }
  function renderBanner() {
    const b = $('#banner'); b.replaceChildren();
    if (S.as) { const x = el('div', 'banner as-banner'); x.append(el('span', null, `Вы смотрите как ${S.as.person || '—'} (${S.as.role}). Кнопки работают от его имени — удобно, если сотрудник сообщил по телефону.`)); const r = el('button', 'btn sm', 'Вернуться к себе'); r.type = 'button'; r.addEventListener('click', () => { S.as = null; render(); }); x.append(r); b.append(x); }
    if (!S.loadErr) return;
    const x = el('div', 'banner bad');
    x.append(el('span', null, (S.payload ? 'Не удалось обновить данные, показаны прежние. ' : 'Не загрузилось. ') + S.loadErr));
    const r = el('button', 'btn sm', 'Повторить'); r.type = 'button'; r.addEventListener('click', refreshAll); x.append(r);
    b.append(x);
  }
  function renderTop() {
    $('#stamp').textContent = S.load === 'loading' ? 'загрузка…' : S.loadedAt ? 'обновлено ' + new Date(S.loadedAt).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '';
    // filters
    const fill = (sel, opts, all, val) => { if (document.activeElement === sel) return; sel.replaceChildren(new Option(all, ''), ...opts); sel.value = val; if (sel.value !== val) { sel.value = ''; } };
    const projs = (S.d.projects || []).filter((p) => p.status !== 'Закрыт').map((p) => p.name);
    fill($('#f-project'), projs.map((n) => new Option(n, n)), 'Все проекты', S.filters.project);
    const ppl = [...new Set([...teamPeople().map((p) => p.name), ...(S.d.tasks || []).map((t) => t.assignee).filter(Boolean)])].sort((a, b) => a.localeCompare(b, 'ru'));
    fill($('#f-person'), ppl.map((n) => new Option(n, n)), 'Все сотрудники', S.filters.person);
    $('#f-person').hidden = !isMgr(); $('#btn-op').hidden = !canFinance(); $('#btn-task').hidden = !isMgr(); $('#f-reset').hidden = !isMgr();
    const fa = $('#f-as'); const realBoss = S.me && (S.me.owner || S.me.role === 'Руководитель');
    fa.hidden = !realBoss || !(S.d.access || []).length;
    if (realBoss && document.activeElement !== fa) {
      const opts = (S.d.access || []).filter((r) => r.person && r.person !== S.me.person).map((r, i) => new Option(`как ${r.person} · ${r.role || '—'}`, String(i)));
      fa.replaceChildren(new Option('Смотреть как: я', ''), ...opts); fa.value = S.as ? String((S.d.access || []).filter((r) => r.person && r.person !== S.me.person).findIndex((r) => r.person === S.as.person)) : '';
    }
    // badge on tasks tab
    const att = (S.d.tasks || []).filter((t) => !CLOSED.includes(t.status) && problem(t) && problem(t).key <= 3).length;
    const tb = $('.tab[data-tab="tasks"]'); tb.textContent = 'Задачи'; if (att) tb.append(el('span', 'badge', String(att)));
  }

  const skel = (box, h = 120) => { box.replaceChildren(el('div', 'skel')); box.firstChild.style.height = h + 'px'; };
  const failIn = (box) => box.replaceChildren(el('div', 'fail', 'Не загрузилось: ' + (S.loadErr || 'ошибка сервера')));
  const emptyRow = (tbody, cols, text) => { const tr = el('tr'); const td = el('td', 'empty', text); td.colSpan = cols; tr.append(td); tbody.append(tr); };
  function tile(k, v, s, cls, goto) {
    const t = el(goto ? 'button' : 'div', 'tile ' + (cls || '')); if (goto) { t.type = 'button'; t.addEventListener('click', () => goTab(goto)); }
    t.append(el('span', 'k', k), el('span', 'v', v), el('span', 's', s || '')); return t;
  }
  function progBlock(t) {
    const box = el('div', 'prog');
    [['сделано', t.done, taskColor(t)], ['время', t.elapsed, 'var(--muted-bar)']].forEach(([label, v, color]) => {
      if (label === 'время' && !isNum(v)) return;
      const r = el('div', 'prog-row'); r.append(el('span', null, label));
      const tr = el('div', 'track'); const f = el('div', 'fill'); f.style.width = Math.max(0, Math.min(1, isNum(v) ? v : 0)) * 100 + '%'; f.style.background = color; tr.append(f);
      r.append(tr, el('span', 'num', fPct(v))); box.append(r);
    });
    return box;
  }
  const statusPill = (s) => el('span', 'pill ' + (s === 'Принята' ? 'ok' : s === 'На проверке' ? 'ink' : s === 'Есть вопрос' || s === 'На доработке' ? 'warn' : ''), s || '—');

  // ---------- HOME
  function renderHome() {
    const tt = $('#home-task-tiles'), mt = $('#home-money-tiles');
    if (S.d.tasks) {
      const ts = fTasks();
      tt.replaceChildren(
        tile('В работе', fNum(ts.filter((t) => ACTIVE.includes(t.status)).length), 'в работе, на доработке, с вопросом', '', 'tasks'),
        tile('Тревога 70%', fNum(ts.filter((t) => t.control === 'ТРЕВОГА 70%').length), 'прошло ≥70% срока, сделано <70%', 'bad', 'tasks'),
        tile('Просрочено', fNum(ts.filter(overdue).length), 'плановая дата прошла', 'bad', 'tasks'),
        tile('Отстают', fNum(ts.filter((t) => t.control === 'Отстаёт').length), '% работы ниже % времени', 'warn', 'tasks'),
        tile('Ждут вашего решения', fNum(ts.filter((t) => WAIT.includes(t.status)).length), 'новые, согласование, проверка, вопросы', 'ink', 'tasks'),
      );
    } else if (status('tasks') === 'error') failIn(tt, 'tasks'); else skel(tt, 84);
    const fin = !!S.d.features?.finance;
    mt.hidden = !fin; $('#home-flow').closest('.card').hidden = !fin;
    if (!fin) { /* finance arrives in a later integration stage */ }
    else if (S.d.home) {
      const H = S.d.home;
      mt.replaceChildren(
        tile('Деньги сейчас, сум', fMln(H.uzs), fNum(H.uzs) + ' сум', H.uzs < 0 ? 'bad' : '', 'money'),
        tile('Деньги сейчас, $', fUsd(H.usd), 'наличные и счёт в долларах', '', 'money'),
        tile('Всего в $', fUsd(H.totalUsd), 'по курсу ' + fNum(H.rate), 'ink', 'money'),
        tile('Чистая прибыль GASTEC', fUsd((H.profit.find((r) => /^Чистая прибыль/.test(r.label)) || {}).a), 'прогноз по открытым договорам', 'ok', 'money'),
        tile('Должны исполнителям', fUsd((H.profit.find((r) => /^Должны исполнителям/.test(r.label)) || {}).a), 'проекты GASTEC', 'warn', 'contracts'),
      );
    } else if (status('home') === 'error') failIn(mt, 'home'); else skel(mt, 84);
    // attention
    const tb = $('#att tbody'); tb.replaceChildren();
    if (!S.d.tasks) { if (status('tasks') !== 'error') emptyRow(tb, 6, 'Загрузка…'); else emptyRow(tb, 6, 'Не загрузилось'); }
    else {
      const rows = fTasks().filter((t) => !CLOSED.includes(t.status) && problem(t)).sort((a, b) => problem(a).key - problem(b).key || ((a.plan || '9') < (b.plan || '9') ? -1 : 1));
      rows.forEach((t) => {
        const tr = el('tr', 'click'); tr.addEventListener('click', () => openTask(t.id));
        const p = problem(t); const pc = el('td'); pc.append(el('span', 'pill ' + p.cls, p.text));
        const pg = el('td'); pg.append(progBlock(t));
        pg.className = 'hide-narrow'; tr.append(el('td', 'num', t.id ?? '—'), el('td', null, t.task || '—'), el('td', null, t.assignee || '—'), el('td', 'num', fD(t.plan)), pg, pc);
        tb.append(tr);
      });
      if (!rows.length) emptyRow(tb, 6, S.d.tasks.length ? 'Сейчас ничего не требует внимания.' : 'Задач пока нет. Поставьте первую кнопкой «+ Задача».');
    }
    if (fin) drawFlow($('#home-flow'), 30, 180);
  }

  // ---------- money flow chart (daily in/out bars)
  function drawFlow(box, daysBack, height) {
    if (!S.d.ops) { if (status('ops') === 'error') failIn(box, 'ops'); else skel(box, height); return; }
    const W = box.clientWidth; if (!W) return;
    const ops = fOps().filter((o) => o.date && o.cat !== 'Начальный остаток' && o.type !== 'Остаток');
    const T0 = today(); const d0 = new Date(T0.getTime() - (daysBack - 1) * DAY);
    const days = d3.timeDay.range(d0, new Date(T0.getTime() + DAY));
    const by = d3.rollup(ops.filter((o) => parseD(o.date) >= d0), (v) => ({ inn: d3.sum(v, (o) => Math.max(0, eqUzs(o))), out: d3.sum(v, (o) => Math.min(0, eqUzs(o))) }), (o) => o.date);
    const data = days.map((d) => ({ d, ...(by.get(iso(d)) || { inn: 0, out: 0 }) }));
    if (!ops.length) { box.replaceChildren(el('div', 'empty', 'Операций за период пока нет.')); return; }
    const m = { l: 56, r: 8, t: 24, b: 24 }; const H = height;
    const maxV = d3.max(data, (r) => Math.max(r.inn, -r.out)) || 1;
    const x = d3.scaleBand(days.map(iso), [m.l, W - m.r]).padding(0.25);
    const y = d3.scaleLinear([-maxV, maxV], [H - m.b, m.t]).nice();
    const svg = d3.create('svg').attr('width', '100%').attr('height', H).attr('viewBox', `0 0 ${W} ${H}`);
    y.ticks(4).forEach((v) => { svg.append('line').attr('x1', m.l).attr('x2', W - m.r).attr('y1', y(v)).attr('y2', y(v)).attr('stroke', 'var(--grid)');
      svg.append('text').attr('x', m.l - 6).attr('y', y(v) + 4).attr('text-anchor', 'end').attr('font-size', 10).attr('fill', 'var(--muted)').text(v === 0 ? '0' : nf1.format(v / 1e6)); });
    svg.append('text').attr('x', 4).attr('y', 10).attr('font-size', 10).attr('fill', 'var(--muted)').text('млн сум');
    const g = svg.append('g');
    g.selectAll('rect.in').data(data).join('rect').attr('x', (r) => x(iso(r.d))).attr('width', x.bandwidth()).attr('y', (r) => y(r.inn)).attr('height', (r) => Math.max(0, y(0) - y(r.inn))).attr('rx', 2).attr('fill', 'var(--ok)');
    g.selectAll('rect.out').data(data).join('rect').attr('x', (r) => x(iso(r.d))).attr('width', x.bandwidth()).attr('y', y(0)).attr('height', (r) => Math.max(0, y(r.out) - y(0))).attr('rx', 2).attr('fill', 'var(--bad)');
    svg.append('line').attr('x1', m.l).attr('x2', W - m.r).attr('y1', y(0)).attr('y2', y(0)).attr('stroke', 'var(--muted)');
    const step = Math.max(1, Math.ceil(44 / x.step()));
    days.forEach((d, i) => { if (i % step === 0) svg.append('text').attr('x', x(iso(d)) + x.bandwidth() / 2).attr('y', H - 6).attr('text-anchor', 'middle').attr('font-size', 10).attr('fill', 'var(--muted)').text(fDs(d)); });
    const tip = el('div', 'tip'); tip.hidden = true;
    svg.append('g').selectAll('rect').data(data).join('rect').attr('x', (r) => x(iso(r.d)) - x.step() * x.paddingInner() / 2).attr('width', x.step()).attr('y', m.t).attr('height', H - m.t - m.b).attr('fill', 'transparent')
      .on('mousemove', (ev, r) => { tip.replaceChildren(el('div', 't1', ruDate(r.d)), el('div', null, 'Приход: ' + fNum(r.inn) + ' сум'), el('div', null, 'Расход: ' + fNum(-r.out) + ' сум')); placeTip(tip, box, ev); })
      .on('mouseleave', () => { tip.hidden = true; });
    box.replaceChildren(svg.node(), tip);
  }
  function placeTip(t, box, ev) {
    const r = box.getBoundingClientRect(); t.hidden = false;
    let x = ev.clientX - r.left + 12, y = ev.clientY - r.top + 12; const w = t.offsetWidth, hh = t.offsetHeight;
    if (x + w > box.clientWidth - 4) x = ev.clientX - r.left - w - 12; if (x < 4) x = 4;
    if (y + hh > box.clientHeight) y = Math.max(0, ev.clientY - r.top - hh - 12);
    t.style.left = x + 'px'; t.style.top = y + 'px';
  }

  // ---------- TASKS tab
  const TCOLS = [['id', '№', 'r num'], ['task', 'Задача', 'wide'], ['assignee', 'Исполнитель'], ['project', 'Проект'], ['priority', 'Пр.', 'r num'], ['plan', 'Сдать до', 'num'], ['status', 'Статус'], ['done', 'Ход'], ['problem', 'Контроль'], ['source_ok', 'Исходник', 'hide-narrow'], ['points', 'Баллы', 'r num hide-narrow']];
  function renderTasks() {
    fillTaskSelects($('#q-person'), $('#q-project'));
    const head = $('#t-table thead tr');
    if (!head.children.length) head.append(...TCOLS.map(([k, label, cls]) => { const th = el('th', cls || null); const b = el('button', null, label); b.type = 'button'; b.addEventListener('click', () => { S.tSort = [k, S.tSort[0] === k ? -S.tSort[1] : 1]; renderTasks(); }); th.append(b); return th; }));
    $$('th', head).forEach((th, i) => th.setAttribute('aria-sort', TCOLS[i][0] === S.tSort[0] ? (S.tSort[1] > 0 ? 'ascending' : 'descending') : 'none'));
    const tb = $('#t-table tbody'); tb.replaceChildren();
    if (!S.d.tasks) { emptyRow(tb, TCOLS.length, status('tasks') === 'error' ? 'Не загрузилось' : 'Загрузка…'); return; }
    const q = $('#t-search').value.trim().toLowerCase(); const st = $('#t-status').value;
    let rows = fTasks().filter((t) => (st === 'open' ? !CLOSED.includes(t.status) : st ? t.status === st : true));
    if (q) rows = rows.filter((t) => [t.task, t.assignee, t.project, t.type, t.status, t.comment, String(t.id)].some((v) => v && String(v).toLowerCase().includes(q)));
    const [k, dir] = S.tSort; const val = (t) => (k === 'problem' ? (problem(t) ? problem(t).key : 99) : t[k]);
    rows = rows.slice().sort((a, b) => { const va = val(a), vb = val(b); if (va == null && vb == null) return 0; if (va == null) return 1; if (vb == null) return -1; return (isNum(va) && isNum(vb) ? va - vb : String(va).localeCompare(String(vb), 'ru')) * dir; });
    $('#t-count').textContent = `${rows.length} ${plural(rows.length, 'задача', 'задачи', 'задач')}`;
    rows.forEach((t) => {
      const tr = el('tr', 'click'); tr.addEventListener('click', () => openTask(t.id));
      TCOLS.forEach(([key, , cls]) => {
        const td = el('td', cls || null);
        if (key === 'status') td.append(statusPill(t.status));
        else if (key === 'done') td.append(progBlock(t));
        else if (key === 'problem') { const p = problem(t); if (p) td.append(el('span', 'pill ' + p.cls, p.text)); else if (t.control) td.append(el('span', 'pill ok', t.control)); }
        else if (key === 'plan') td.textContent = fD(t.plan);
        else if (key === 'points') td.textContent = fNum(t.points);
        else td.textContent = t[key] ?? '—';
        tr.append(td);
      });
      tb.append(tr);
    });
    if (!rows.length) emptyRow(tb, TCOLS.length, S.d.tasks.length ? 'По фильтрам ничего не найдено.' : 'Задач пока нет. Поставьте первую выше.');
  }
  function fillTaskSelects(selP, selPr, keepP, keepPr) {
    if (document.activeElement !== selP) {
      const cur = keepP ?? selP.value;
      const team = teamPeople().map((p) => p.name).sort((a, b) => a.localeCompare(b, 'ru'));
      const others = (S.d.people || []).filter((p) => p.inTasks !== 'Да' && !/^Заказчик$/.test(p.role || '') && !/^Партнёр$/.test(p.role || '')).map((p) => p.name).sort((a, b) => a.localeCompare(b, 'ru'));
      const g1 = el('optgroup'); g1.label = 'Сотрудники'; team.forEach((n) => g1.append(new Option(n, n)));
      const g2 = el('optgroup'); g2.label = 'Исполнители по договору'; others.forEach((n) => g2.append(new Option(n, n)));
      selP.replaceChildren(new Option('— выберите —', ''), g1, g2); selP.value = cur || S.filters.person || '';
    }
    if (document.activeElement !== selPr) {
      const cur = keepPr ?? selPr.value;
      selPr.replaceChildren(new Option('— проект —', ''), ...(S.d.projects || []).filter((p) => p.status !== 'Закрыт').map((p) => new Option(p.name, p.name))); selPr.value = cur || S.filters.project || '';
    }
  }

  // ---------- GANTT
  function renderGantt() {
    $('#g-group').value = S.gGroup; $('#g-done').checked = S.gDone;
    $('#g-legend').replaceChildren(...[['В графике', COLORS.ok], ['Отстаёт', COLORS.lag], ['Тревога / просрочка', COLORS.alert], ['На проверке', COLORS.review], ['Принята', COLORS.done]].map(([n, c]) => { const s = el('span'); const sw = el('i', 'sw'); sw.style.background = c; s.append(sw, document.createTextNode(n)); return s; }));
    const box = $('#g-chart');
    if (!S.d.tasks) { if (status('tasks') === 'error') failIn(box, 'tasks'); else skel(box, 200); return; }
    const W = box.clientWidth; if (!W) return;
    const by = S.gGroup === 'project' ? 'project' : S.gGroup === 'stage' ? 'stage' : 'assignee';
    const gkey = (t) => (by === 'stage' ? (isProjectTask(t) ? stageOf(t) : 'Нестандартные' + (t.dept ? ' · ' + t.dept : '')) : t[by] || '—');
    const all = fTasks().filter((t) => t.status !== 'Отменена' && (S.gDone || t.status !== 'Принята'));
    const items = all.filter((t) => t.start && t.plan).map((t) => ({ t, s: parseD(t.start), e: parseD(t.plan), f: parseD(t.finished) }));
    const undated = all.filter((t) => !(t.start && t.plan) && t.status !== 'Черновик');
    $('#g-undated').textContent = undated.length ? `Без дат (срок не согласован или нет даты начала): ${undated.length}` : '';
    $('#g-undated-list').replaceChildren(...undated.map((t) => { const b = el('button', 'pill', `№${t.id ?? '—'} · ${t.task || ''} · ${t.assignee || ''}`); b.type = 'button'; b.style.border = '0'; b.style.whiteSpace = 'normal'; b.addEventListener('click', () => openTask(t.id)); return b; }));
    if (!items.length) { box.replaceChildren(el('div', 'empty', 'Нет задач с датой начала и сроком.')); return; }
    const T0 = today();
    let d0 = d3.min(items, (i) => i.s), d1 = d3.max(items, (i) => d3.max([i.e, i.f || i.e]));
    if (T0 < d0) d0 = T0; if (T0 > d1) d1 = T0;
    d0 = new Date(d0.getTime() - DAY); d1 = new Date(d1.getTime() + 2 * DAY);
    if ((d1 - d0) / DAY < 14) d1 = new Date(d0.getTime() + 14 * DAY);
    const narrow = W < 640; const labelW = narrow ? Math.round(Math.min(150, W * 0.42)) : Math.min(320, Math.round(W * 0.3));
    const viewW = W - labelW; const days = Math.round((d1 - d0) / DAY); const tlW = Math.max(viewW, days * (narrow ? 18 : 26) + 16);
    const rowH = narrow ? 40 : 32, groupH = 28, axisH = 40;
    const x = d3.scaleTime([d0, d1], [6, tlW - 10]); const pxDay = (x(d1) - x(d0)) / days;
    const groups = d3.groups(items, (i) => gkey(i.t)).sort((a, b) => a[0].localeCompare(b[0], 'ru', { numeric: true }));
    const lines = []; let y = axisH;
    groups.forEach(([name, list]) => { lines.push({ kind: 'g', name, y, n: list.length }); y += groupH; list.sort((a, b) => a.s - b.s || a.e - b.e).forEach((i) => { lines.push({ kind: 't', i, y }); y += rowH; }); });
    const H = y + 8;
    const L = d3.create('svg').attr('width', labelW).attr('height', H).attr('viewBox', `0 0 ${labelW} ${H}`);
    const R = d3.create('svg').attr('width', tlW).attr('height', H).attr('viewBox', `0 0 ${tlW} ${H}`);
    const ticks = d3.timeDay.range(d0, d1); const step = Math.max(1, Math.ceil(46 / pxDay));
    R.append('g').selectAll('line').data(ticks).join('line').attr('x1', (t) => x(t)).attr('x2', (t) => x(t)).attr('y1', axisH - 6).attr('y2', H).attr('stroke', 'var(--grid)').attr('stroke-opacity', (t) => (t.getDay() === 1 ? 1 : 0.5));
    const lab = R.append('g').attr('font-size', 11).attr('fill', 'var(--muted)').attr('font-family', 'var(--f-num)');
    ticks.filter((t, k) => k % step === 0).forEach((t) => lab.append('text').attr('x', x(t) + 3).attr('y', axisH - 12).text(fDs(t)));
    d3.timeMonth.range(d3.timeMonth.floor(d0), d1).forEach((mo) => { const mx = Math.max(x(mo), 6); if (mx < tlW - 70) lab.append('text').attr('x', mx + 3).attr('y', 12).attr('fill', 'var(--fg)').attr('font-family', 'var(--f-ui)').text(MONTHS[mo.getMonth()] + ' ' + mo.getFullYear()); });
    L.append('text').attr('x', 6).attr('y', axisH - 12).attr('font-size', 11).attr('fill', 'var(--muted)').text(by === 'project' ? 'Проект / задача' : by === 'stage' ? 'Этап / задача' : 'Сотрудник / задача');
    const tip = el('div', 'tip'); tip.hidden = true;
    const showTip = (t) => (ev) => { tip.replaceChildren(el('div', 't1', `№${t.id ?? '—'} · ${t.project || ''}`), el('div', null, t.task || ''), el('div', null, `${t.assignee || '—'} · ${t.status || '—'}`), el('div', null, `${fD(t.start)} → ${fD(t.plan)} (${fNum(t.days)} дн.)` + (t.finished ? `, сдано ${fD(t.finished)}` : '')), el('div', null, `Сделано ${fPct(t.done)}` + (isNum(t.elapsed) ? `, прошло ${fPct(t.elapsed)} срока` : ''))); placeTip(tip, box, ev); };
    const hideTip = () => { tip.hidden = true; };
    lines.forEach((ln) => {
      if (ln.kind === 'g') {
        [L, R].forEach((s, k) => s.append('rect').attr('x', 0).attr('y', ln.y).attr('width', k ? tlW : labelW).attr('height', groupH).attr('fill', 'var(--panel-2)'));
        fit(L.append('text').attr('x', 6).attr('y', ln.y + groupH / 2 + 4).attr('font-size', 12).attr('font-weight', 600).attr('fill', 'var(--fg)').text(`${ln.name} · ${ln.n}`), labelW - 10);
        return;
      }
      const { t, s, e, f } = ln.i; const color = taskColor(t); const sub = by === 'project' ? (t.assignee || '') : by === 'stage' ? `${t.assignee || ''} · ${t.project || ''}` : (t.project || '');
      const lg = L.append('g').attr('transform', `translate(0,${ln.y})`).style('cursor', 'pointer');
      if (narrow) { fit(lg.append('text').attr('x', 6).attr('y', 16).attr('font-size', 12).attr('fill', 'var(--fg)').text(`№${t.id ?? '—'} ${t.task || ''}`), labelW - 10); fit(lg.append('text').attr('x', 6).attr('y', 31).attr('font-size', 10).attr('fill', 'var(--muted)').text(sub), labelW - 10); }
      else fit(lg.append('text').attr('x', 6).attr('y', rowH / 2 + 4).attr('font-size', 12).attr('fill', 'var(--fg)').text(`№${t.id ?? '—'} ${t.task || ''} · ${sub}`), labelW - 10);
      lg.append('rect').attr('width', labelW).attr('height', rowH).attr('fill', 'transparent').on('mousemove', showTip(t)).on('mouseleave', hideTip).on('click', () => openTask(t.id));
      const g = R.append('g').attr('transform', `translate(0,${ln.y})`).style('cursor', 'pointer');
      const barH = 14, barY = (rowH - barH) / 2; const x0 = x(s), x1 = Math.max(x(e), x0 + 3), w = x1 - x0;
      g.append('rect').attr('x', x0).attr('y', barY).attr('width', w).attr('height', barH).attr('rx', 4).attr('fill', color).attr('fill-opacity', 0.2).attr('stroke', color).attr('stroke-opacity', 0.55);
      const done = Math.max(0, Math.min(1, isNum(t.done) ? t.done : 0));
      if (done > 0) g.append('rect').attr('x', x0).attr('y', barY).attr('width', Math.max(2, w * done)).attr('height', barH).attr('rx', 4).attr('fill', color);
      if (overdue(t)) g.append('rect').attr('x', x1).attr('y', barY + barH / 2 - 2).attr('width', Math.max(0, x(T0) - x1)).attr('height', 4).attr('rx', 2).attr('fill', COLORS.alert);
      if (f) { const fx = x(f), cy = barY + barH / 2; g.append('path').attr('d', `M${fx},${cy - 6}L${fx + 6},${cy}L${fx},${cy + 6}L${fx - 6},${cy}Z`).attr('fill', 'var(--fg)'); }
      const pt = fPct(t.done);
      if (w > 36) g.append('text').attr('x', x0 + 5).attr('y', barY + barH - 3).attr('font-size', 10).attr('font-family', 'var(--f-num)').attr('fill', done * w > 32 ? 'var(--panel)' : 'var(--fg)').text(pt);
      else g.append('text').attr('x', x1 + 4).attr('y', barY + barH - 3).attr('font-size', 10).attr('font-family', 'var(--f-num)').attr('fill', 'var(--muted)').text(pt);
      g.append('rect').attr('x', 0).attr('width', tlW).attr('height', rowH).attr('fill', 'transparent').on('mousemove', showTip(t)).on('mouseleave', hideTip).on('click', () => openTask(t.id));
    });
    if (T0 >= d0 && T0 <= d1) { R.append('line').attr('x1', x(T0)).attr('x2', x(T0)).attr('y1', axisH - 8).attr('y2', H).attr('stroke', 'var(--fg)').attr('stroke-opacity', 0.5).attr('stroke-width', 2).style('pointer-events', 'none'); R.append('text').attr('x', x(T0) + 4).attr('y', axisH - 26).attr('font-size', 11).attr('fill', 'var(--fg)').text('сегодня'); }
    const prev = box.querySelector('.gr') ? box.querySelector('.gr').scrollLeft : null;
    const wrap = el('div', 'gwrap'); const left = el('div', 'gl'); left.style.width = labelW + 'px'; const right = el('div', 'gr');
    left.append(L.node()); right.append(R.node()); wrap.append(left, right); box.replaceChildren(wrap, tip);
    right.addEventListener('scroll', hideTip);
    if (tlW > viewW) right.scrollLeft = prev != null ? prev : Math.max(0, x(T0) - viewW * 0.65);
  }

  // ---------- TEAM (compact: one row per person, problems first, free people in one line)
  function renderTeam() {
    const list = $('#tm-list'), free = $('#tm-free');
    if (!S.d.people || !S.d.tasks) { if (status('people') === 'error' || status('tasks') === 'error') failIn(list, status('people') === 'error' ? 'people' : 'tasks'); else skel(list, 200); free.hidden = true; return; }
    const kp = kpiRows() || [];
    const openOf = (name) => (S.d.tasks || []).filter((t) => t.assignee === name && !CLOSED.includes(t.status) && t.status !== 'Черновик' && (!S.filters.project || t.project === S.filters.project));
    const names = [...new Set([...teamPeople().map((p) => p.name), ...(S.d.tasks || []).filter((t) => !CLOSED.includes(t.status) && t.assignee).map((t) => t.assignee)])]
      .filter((n) => !S.filters.person || n === S.filters.person);
    const rows = names.map((name) => {
      const p = personBy(name) || { name }; const mine = openOf(name).sort((x, y) => ((problem(x)?.key ?? 9) - (problem(y)?.key ?? 9)) || ((x.plan || '9') < (y.plan || '9') ? -1 : 1));
      const n = { overdue: mine.filter(overdue).length, alert: mine.filter((t) => t.control === 'ТРЕВОГА 70%' && !overdue(t)).length, lag: mine.filter((t) => t.control === 'Отстаёт' && !overdue(t)).length, nosrc: mine.filter((t) => noSource(t) && !overdue(t) && t.control !== 'ТРЕВОГА 70%').length, urgent: mine.filter((t) => t.priority === 1).length, review: mine.filter((t) => t.status === 'На проверке').length, question: mine.filter((t) => t.status === 'Есть вопрос').length };
      const hours = d3.sum(mine, (t) => t.hours || 0); const norm = p.norm || 40;
      const level = n.overdue || n.alert ? 'bad' : n.lag || n.nosrc ? 'warn' : '';
      return { name, p, mine, n, hours, norm, level, k: kp.find((r) => r.name === name) };
    });
    const rank = { bad: 0, warn: 1, '': 2 };
    const busy = rows.filter((r) => r.mine.length).sort((x, y) => rank[x.level] - rank[y.level] || y.mine.length - x.mine.length || x.name.localeCompare(y.name, 'ru'));
    const idle = rows.filter((r) => !r.mine.length && teamPeople().some((p) => p.name === r.name)).sort((x, y) => x.name.localeCompare(y.name, 'ru'));
    const prob = busy.filter((r) => r.level);
    $('#tm-n-all').textContent = busy.length + idle.length; $('#tm-n-prob').textContent = prob.length; $('#tm-n-work').textContent = busy.length;
    $$('#p-team .tm-chip').forEach((c) => c.setAttribute('aria-pressed', String(c.dataset.f === S.teamF)));
    const shown = S.teamF === 'prob' ? prob : busy;
    list.replaceChildren();
    shown.forEach((r) => {
      const row = el('div', 'tm-row ' + r.level); const open = S.teamOpen.has(r.name); if (open) row.setAttribute('open', '');
      const head = el('button', 'tm-head'); head.type = 'button'; head.setAttribute('aria-expanded', String(open));
      const mid = el('div'); const nm = el('div', 'tm-name', r.name); const role = r.p.sections || (r.p.role ? r.p.role.replace(/^Штатный, Исполнитель$/, 'Штатный') : '');
      if (role) nm.append(el('span', 'tm-role', role)); mid.append(nm);
      const l2 = el('div', 'tm-l2'); const add = (txt, cls) => { l2.append(document.createTextNode(' · ')); l2.append(cls ? el('span', cls, txt) : document.createTextNode(txt)); };
      l2.append(document.createTextNode(`${r.mine.length} ${plural(r.mine.length, 'задача', 'задачи', 'задач')}`));
      if (r.n.overdue) add(`просрочено ${r.n.overdue}`, 'bad');
      if (r.n.alert) add(`тревога ${r.n.alert}`, 'bad');
      if (r.n.lag) add(`отстаёт ${r.n.lag}`, 'warn');
      if (r.n.nosrc) add(`нет исходника ${r.n.nosrc}`, 'warn');
      if (r.n.question) add(`вопрос ${r.n.question}`, 'warn');
      if (r.n.review) add(`ждёт проверки ${r.n.review}`, 'ink');
      if (r.n.urgent) add(`срочных ${r.n.urgent}`);
      if (r.hours > 0) add(`загрузка ${Math.round(r.hours / r.norm * 100)}%`, r.hours > r.norm ? 'bad' : '');
      mid.append(l2);
      const right = el('div', 'tm-right'); const cat = r.k?.cat || '—';
      right.append(el('span', 'tm-kpi ' + (cat === 'A' ? 'ok' : cat === 'B' ? 'ink' : cat === 'C' ? 'warn' : cat === 'D' ? 'bad' : ''), 'KPI ' + cat), el('span', 'tm-chev', '›'));
      head.append(el('span', 'tm-stripe'), mid, right);
      const body = el('div', 'tm-body'); body.hidden = !open;
      r.mine.forEach((t) => {
        const tr = el('button', 'tm-task'); tr.type = 'button'; tr.addEventListener('click', () => openTask(t.id));
        tr.append(el('span', 'tm-t', `№${t.id ?? '—'} ${t.task || ''}`));
        const m = el('span', 'tm-m'); m.append(document.createTextNode(`${t.project || ''} · ${t.plan ? 'до ' + fD(t.plan).slice(0, 5) : 'без срока'} · ${fPct(t.done)}`));
        const pr = problem(t); if (pr) { m.append(document.createTextNode(' · ')); m.append(el('span', pr.cls === 'bad' ? 'bad' : pr.cls === 'warn' ? 'warn' : pr.cls === 'ink' ? 'ink' : '', pr.text)); }
        tr.append(m); body.append(tr);
      });
      const foot = el('div', 'tm-foot'); const ad = el('button', 'tm-add', '+ задача'); ad.type = 'button'; ad.addEventListener('click', () => openTask(null, { assignee: r.name }));
      foot.append(ad); if (r.k && r.k.accepted) foot.append(el('span', 'note', `за месяц принято ${r.k.accepted}` + (isNum(r.k.avg) ? `, средний балл ${nf1.format(r.k.avg)}` : '')));
      body.append(foot);
      head.addEventListener('click', () => { if (S.teamOpen.has(r.name)) S.teamOpen.delete(r.name); else S.teamOpen.add(r.name); const o = S.teamOpen.has(r.name); body.hidden = !o; row.toggleAttribute('open', o); head.setAttribute('aria-expanded', String(o)); });
      row.append(head, body); list.append(row);
    });
    if (!shown.length) list.append(el('div', 'empty', S.teamF === 'prob' ? 'Проблем нет: ни просрочек, ни тревог, ни отставаний.' : 'Ни у кого нет открытых задач.'));
    free.hidden = S.teamF !== 'all' || !idle.length;
    $('#tm-free-h').textContent = `Свободны · ${idle.length}`;
    $('#tm-free-names').replaceChildren(...idle.map((r) => { const b = el('button', null, r.name); b.type = 'button'; b.title = 'Поставить задачу: ' + r.name; b.append(el('span', null, '+')); b.addEventListener('click', () => openTask(null, { assignee: r.name })); return b; }));
  }

  // ---------- KPI
  function renderKpi() {
    const mi = $('#kpi-month'); if (!S.kpiMonth) S.kpiMonth = iso(today()).slice(0, 7); if (document.activeElement !== mi) mi.value = S.kpiMonth;
    const [yy, mm] = S.kpiMonth.split('-').map(Number); $('#kpi-month-label').textContent = MONTHS[mm - 1] + ' ' + yy;
    const K = S.d.kpi; const rows = kpiRows(); const tb = $('#kpi-table tbody'); tb.replaceChildren(); const box = $('#kpi-chart');
    if (!rows) { if (status('tasks') === 'error' || status('kpiset') === 'error') failIn(box, status('tasks') === 'error' ? 'tasks' : 'kpiset'); else skel(box, 160); return; }
    $('#kpi-note').textContent = `Средний балл за принятую задачу (максимум ${fNum(K.early + K.clean)}). В рейтинге участвуют те, у кого не меньше ${K.minTasks} принятых задач за месяц, остальные серые. Категории: ` + K.levels.filter((l) => l.min > -50).map((l) => `${l.cat} от ${nf.format(l.min)} → +${fPct(l.bonus)}`).join(', ') + '.';
    rows.forEach((r) => {
      const tr = el('tr'); const cat = el('td'); cat.append(el('span', 'pill ' + (r.cat === 'A' ? 'ok' : r.cat === 'D' ? 'bad' : r.cat === 'C' ? 'warn' : r.cat === 'B' ? 'ink' : ''), r.cat || '—'));
      tr.append(el('td', 'r num', r.place ?? '—'), el('td', null, r.name), el('td', 'hide-narrow', r.pay), el('td', 'r num', fNum(r.accepted)), el('td', 'r num', fNum(r.early)), el('td', 'r num', fNum(r.ontime)), el('td', 'r num', fNum(r.late)), el('td', 'r num', fNum(r.reworks)), el('td', 'r num', fNum(r.points)), el('td', 'r num', isNum(r.avg) ? nf1.format(r.avg) : '—'), cat, el('td', 'r num', r.cat ? fPct(r.bonus) : '—'), el('td', 'r num', r.pay === 'Договор' ? fNum(r.amount) : '—'));
      tb.append(tr);
    });
    if (!rows.length) emptyRow(tb, 13, 'Нет сотрудников.');
    const W = box.clientWidth; if (!W) return;
    const withAvg = rows; const rowH = 28, top = 24, lw = Math.min(150, W * 0.32), right = 76; const H = top + withAvg.length * rowH + 8;
    const vals = withAvg.map((r) => r.avg || 0); const lo = Math.min(0, d3.min(vals) ?? 0, -1), hi = Math.max(K.early + K.clean, d3.max(vals) ?? 0);
    const x = d3.scaleLinear([lo, hi], [lw, W - right]);
    const svg = d3.create('svg').attr('width', '100%').attr('height', H).attr('viewBox', `0 0 ${W} ${H}`);
    svg.append('line').attr('x1', x(0)).attr('x2', x(0)).attr('y1', top - 6).attr('y2', H - 4).attr('stroke', 'var(--muted)');
    K.levels.filter((l) => l.min > -50 && l.min <= hi).forEach((l) => { svg.append('line').attr('x1', x(l.min)).attr('x2', x(l.min)).attr('y1', top - 6).attr('y2', H - 4).attr('stroke', 'var(--faint)').attr('stroke-dasharray', '4 3'); svg.append('text').attr('x', x(l.min)).attr('y', 12).attr('text-anchor', 'middle').attr('font-size', 11).attr('fill', 'var(--muted)').text(`${l.cat} от ${nf.format(l.min)}`); });
    const color = (r) => (r.cat === 'A' ? 'var(--ok)' : r.cat === 'B' ? 'var(--ink)' : r.cat === 'C' ? 'var(--warn)' : r.cat === 'D' ? 'var(--bad)' : 'var(--muted-bar)');
    const g = svg.selectAll('g.r').data(withAvg).join('g').attr('transform', (r, i) => `translate(0,${top + i * rowH})`);
    fit(g.append('text').attr('x', 0).attr('y', rowH / 2 + 4).attr('font-size', 12).attr('fill', 'var(--fg)').text((r) => (r.place ? r.place + '. ' : '') + r.name), lw - 8);
    g.append('rect').attr('y', rowH / 2 - 7).attr('height', 14).attr('rx', 4).attr('x', (r) => x(Math.min(0, r.avg || 0))).attr('width', (r) => (isNum(r.avg) ? Math.max(2, Math.abs(x(r.avg) - x(0))) : 0)).attr('fill', color);
    g.append('text').attr('x', W - right + 8).attr('y', rowH / 2 + 4).attr('font-size', 11).attr('font-family', 'var(--f-num)').attr('fill', 'var(--muted)').text((r) => (isNum(r.avg) ? nf1.format(r.avg) : 'нет') + (r.cat ? ' · ' + r.cat : ''));
    box.replaceChildren(svg.node());
  }

  // ---------- MONEY
  function renderMoney() {
    const mt = $('#money-tiles');
    if (S.d.home) {
      const H = S.d.home; const ops = fOps().filter((o) => o.cat !== 'Начальный остаток' && o.type !== 'Остаток');
      const ym = iso(today()).slice(0, 7); const mon = ops.filter((o) => o.date && o.date.slice(0, 7) === ym);
      mt.replaceChildren(
        tile('Деньги сейчас, сум', fMln(H.uzs), fNum(H.uzs) + ' сум', H.uzs < 0 ? 'bad' : ''),
        tile('Деньги сейчас, $', fUsd(H.usd), ''),
        tile('Всего в $', fUsd(H.totalUsd), 'курс ' + fNum(H.rate), 'ink'),
        tile('Приход за месяц', fMln(d3.sum(mon, (o) => Math.max(0, eqUzs(o)))), S.filters.project || 'все проекты', 'ok'),
        tile('Расход за месяц', fMln(-d3.sum(mon, (o) => Math.min(0, eqUzs(o)))), S.filters.project || 'все проекты', 'bad'),
      );
      const pr = $('#profit'); const kv = el('div', 'kv'); kv.append(el('span', 'h', ''), el('span', 'h r', H.profitHead[0] || 'GASTEC'), el('span', 'h r', H.profitHead[1] || ''));
      H.profit.forEach((r) => { const tot = /Чистая прибыль|На каждого/.test(r.label); [el('span', tot ? 'tot' : null, r.label), el('span', 'num r' + (tot ? ' tot' : ''), r.label === 'Делим на' ? fNum(r.a) : fUsd(r.a)), el('span', 'num r' + (tot ? ' tot' : ''), r.label === 'Делим на' ? fNum(r.b) : fUsd(r.b))].forEach((x) => { x.style.textAlign = x.classList.contains('r') ? 'right' : ''; kv.append(x); }); });
      pr.replaceChildren(kv);
    } else if (status('home') === 'error') { failIn(mt, 'home'); $('#profit').replaceChildren(); } else { skel(mt, 84); skel($('#profit'), 160); }
    // project balances
    const pb = $('#proj-bal');
    if (S.d.ops) {
      const W = pb.clientWidth;
      const bal = d3.rollups(S.d.ops.filter((o) => o.project && (!S.filters.project || o.project === S.filters.project)), (v) => d3.sum(v, eqUzs), (o) => o.project).map(([p, v]) => ({ p, v })).sort((a, b) => b.v - a.v);
      if (W && bal.length) {
        const rowH = 22, lw = Math.min(130, W * 0.34), right = 104; const H = bal.length * rowH + 8;
        const ext = d3.extent([0, ...bal.map((b) => b.v)]); const x = d3.scaleLinear(ext, [lw, W - right]);
        const svg = d3.create('svg').attr('width', '100%').attr('height', H).attr('viewBox', `0 0 ${W} ${H}`);
        svg.append('line').attr('x1', x(0)).attr('x2', x(0)).attr('y1', 0).attr('y2', H).attr('stroke', 'var(--muted)');
        const g = svg.selectAll('g').data(bal).join('g').attr('transform', (b, i) => `translate(0,${i * rowH + 4})`);
        fit(g.append('text').attr('x', 0).attr('y', 13).attr('font-size', 11).attr('fill', 'var(--fg)').text((b) => b.p), lw - 6);
        g.append('rect').attr('x', (b) => x(Math.min(0, b.v))).attr('y', 3).attr('height', 12).attr('rx', 3).attr('width', (b) => Math.max(1, Math.abs(x(b.v) - x(0)))).attr('fill', (b) => (b.v < 0 ? 'var(--bad)' : 'var(--ink)'));
        g.append('text').attr('x', W - right + 6).attr('y', 13).attr('font-size', 11).attr('font-family', 'var(--f-num)').attr('fill', (b) => (b.v < 0 ? 'var(--bad)' : 'var(--muted)')).text((b) => fMln(b.v));
        pb.replaceChildren(svg.node());
      } else if (!bal.length) pb.replaceChildren(el('div', 'empty', 'Нет операций.'));
    } else if (status('ops') === 'error') failIn(pb, 'ops'); else skel(pb, 200);
    drawFlow($('#money-flow'), 60, 220);
    // operations table
    const tb = $('#op-table tbody'); tb.replaceChildren();
    if (!S.d.ops) emptyRow(tb, 10, status('ops') === 'error' ? 'Не загрузилось' : 'Загрузка…');
    else {
      const q = $('#op-search').value.trim().toLowerCase();
      let rows = fOps(); if (q) rows = rows.filter((o) => [o.project, o.who, o.cat, o.note, o.contract, o.by, String(o.id)].some((v) => v && String(v).toLowerCase().includes(q)));
      rows = rows.slice().sort((a, b) => (b.id || 0) - (a.id || 0));
      $('#op-count').textContent = `${rows.length}`;
      rows.slice(0, 300).forEach((o) => { const tr = el('tr'); const s = el('td', 'r num', fNum(o.uzs)); if (o.uzs < 0) s.style.color = 'var(--bad)'; const u = el('td', 'r num', o.usd ? fUsd(o.usd) : ''); if (o.usd < 0) u.style.color = 'var(--bad)';
        tr.append(el('td', 'r num', o.id ?? ''), el('td', 'num', fD(o.date)), el('td', null, o.project || ''), el('td', null, o.who || ''), el('td', null, o.cat || ''), s, u, el('td', 'hide-narrow', o.contract || ''), el('td', 'hide-narrow', o.note || ''), el('td', 'hide-narrow note', o.by || '')); tb.append(tr); });
      if (!rows.length) emptyRow(tb, 10, 'Операций нет.');
    }
    const mtb = $('#month-table tbody'); mtb.replaceChildren();
    (S.d.months || []).filter((r) => [r.inUzs, r.outUzs, r.inUsd, r.outUsd].some((v) => v)).forEach((r) => { const tr = el('tr'); tr.append(el('td', 'num', r.month), el('td', 'r num', fNum(r.inUzs)), el('td', 'r num', fNum(r.outUzs)), el('td', 'r num', fNum(r.inUsd)), el('td', 'r num', fNum(r.outUsd)), el('td', 'r num', fNum(r.salary)), el('td', 'r num', fNum(r.taxes)), el('td', 'r num', fNum(r.office))); mtb.append(tr); });
    if (!mtb.children.length) emptyRow(mtb, 8, S.d.months ? 'Движения по месяцам пока нет.' : 'Загрузка…');
  }

  // ---------- CONTRACTS
  function renderContracts() {
    const tb = $('#c-table tbody'); tb.replaceChildren();
    if (!S.d.contracts) { emptyRow(tb, 12, status('contracts') === 'error' ? 'Не загрузилось' : 'Загрузка…'); return; }
    const q = $('#c-search').value.trim().toLowerCase(); const st = $('#c-status').value;
    let rows = S.d.contracts.filter((c) => (!S.filters.project || c.project === S.filters.project) && (!S.filters.person || c.name === S.filters.person) && (!st || c.status === st));
    if (q) rows = rows.filter((c) => [c.id, c.project, c.name, c.section, c.note, c.side].some((v) => v && String(v).toLowerCase().includes(q)));
    rows.sort((a, b) => (b.restUsd || 0) - (a.restUsd || 0));
    $('#c-count').textContent = `${rows.length} · остаток ${fUsd(d3.sum(rows.filter((c) => c.side === 'Исполнитель'), (c) => c.restUsd || 0))} исполнителям, ${fUsd(d3.sum(rows.filter((c) => c.side === 'Заказчик'), (c) => c.restUsd || 0))} от заказчиков`;
    rows.forEach((c) => {
      const tr = el('tr'); const pay = el('td'); if (c.status === 'Открыт') { const b = el('button', 'btn sm', c.side === 'Заказчик' ? 'Поступление' : 'Оплатить'); b.type = 'button'; b.addEventListener('click', () => openOp({ contract: c })); pay.append(b); }
      const stt = el('td'); stt.append(el('span', 'pill ' + (c.status === 'Открыт' ? 'warn' : 'ok'), c.status || '—'));
      tr.append(el('td', 'num', c.id), el('td', null, c.project || ''), el('td', null, c.side || ''), el('td', null, c.name || ''), el('td', null, c.section || ''), el('td', null, c.cur || ''), el('td', 'r num', fNum(c.amount)), el('td', 'r num', fNum(c.paid)), el('td', 'r num', fNum(c.rest)), el('td', 'r num', fUsd(c.restUsd)), stt, pay);
      tb.append(tr);
    });
    if (!rows.length) emptyRow(tb, 12, 'Договоров нет.');
  }

  // ---------- modal helpers
  function modal(title, build) {
    const root = $('#modal-root'); const ov = el('div', 'overlay'); const m = el('div', 'modal'); m.setAttribute('role', 'dialog'); m.setAttribute('aria-modal', 'true'); m.setAttribute('aria-label', title);
    m.append(el('h3', null, title)); ov.append(m); root.replaceChildren(ov);
    const close = () => { root.replaceChildren(); document.removeEventListener('keydown', esc); };
    const esc = (e) => { if (e.key === 'Escape') close(); }; document.addEventListener('keydown', esc);
    ov.addEventListener('mousedown', (e) => { if (e.target === ov) close(); });
    build(m, close); const f = m.querySelector('input, select, textarea'); if (f) f.focus();
    return close;
  }
  const field = (label, ctl, cls) => { const l = el('label', cls || null); l.append(document.createTextNode(label), ctl); return l; };
  const input = (id, type, value, attrs = {}) => { const i = el('input', 'ctl' + (type === 'number' ? ' num' : '')); i.id = id; i.type = type; if (value != null) i.value = value; Object.entries(attrs).forEach(([k, v]) => i.setAttribute(k, v)); return i; };
  const select = (id, opts, value) => { const s = el('select', 'ctl'); s.id = id; opts.forEach((o) => s.append(typeof o === 'string' ? new Option(o, o) : o)); if (value != null) s.value = value; return s; };

  // ---------- TASK modal (add / edit)
  function openTask(id, preset = {}) {
    if (!S.mcp) return toast('Сервер недоступен.');
    const t = id != null ? (S.d.tasks || []).find((x) => x.id === id) : null;
    if (id != null && !t) return toast('Задача не найдена, обновите страницу.');
    modal(t ? `Задача №${t.id}` : 'Новая задача', (m, close) => {
      const form = el('div', 'form');
      const fTask = el('textarea', 'ctl'); fTask.id = 'm-task'; fTask.value = t?.task || preset.task || ''; fTask.placeholder = 'Что нужно сделать';
      const fP = el('select', 'ctl'); fP.id = 'm-person'; const fPr = el('select', 'ctl'); fPr.id = 'm-project';
      fillTaskSelects(fP, fPr, t?.assignee || preset.assignee || '', t?.project || preset.project || '');
      if (t && t.assignee && ![...fP.options].some((o) => o.value === t.assignee)) { fP.append(new Option(t.assignee, t.assignee)); fP.value = t.assignee; }
      if (t && t.project && ![...fPr.options].some((o) => o.value === t.project)) { fPr.append(new Option(t.project, t.project)); fPr.value = t.project; }
      const fSec = el('select', 'ctl'); fSec.id = 'm-sec';
      const fillSec = (keep) => { const cur = keep != null ? String(keep) : fSec.value; const list = (S.d.sched?.rows || []).filter((x) => x.project === fPr.value && !x.summary && !x.mile); fSec.replaceChildren(new Option(list.length ? '— без раздела —' : '— у проекта нет состава —', ''), ...list.map((x) => new Option(`${x.wbs || ''} ${x.code || ''} ${x.name || ''}`.replace(/\s+/g, ' ').trim(), x.id))); fSec.value = list.some((x) => String(x.id) === cur) ? cur : ''; };
      fillSec(t?.section ?? preset.section ?? ''); fPr.addEventListener('change', () => fillSec(''));
      const tpl = S.d.templates || []; const fType = select('m-type', [new Option('—', ''), ...tpl.map((x) => new Option(x.name, x.name))], t?.type || '');
      const fPrio = select('m-prio', [new Option('1 — срочно', '1'), new Option('2 — обычный', '2'), new Option('3 — когда будет время', '3')], String(t?.priority || 2));
      const fDays = input('m-days', 'number', t?.days ?? preset.days ?? '', { min: 0, step: 1, placeholder: 'назовёт сотрудник' });
      const fStart = input('m-start', 'date', t?.start || iso(today()));
      const fHours = input('m-hours', 'number', t?.hours ?? '', { min: 0, step: 0.5 });
      const fAmount = input('m-amount', 'number', t?.amount ?? '', { min: 0, step: 1000, placeholder: 'для договорников' });
      const fStatus = select('m-status', STATUSES, t?.status || '');
      const fComment = el('textarea', 'ctl'); fComment.id = 'm-comment'; fComment.value = t?.comment || '';
      fType.addEventListener('change', () => { const x = tpl.find((y) => y.name === fType.value); if (!x) return; if (!fDays.value && isNum(x.days)) fDays.value = x.days; if (!fHours.value && isNum(x.hours)) fHours.value = x.hours; autoStatus(); });
      const autoStatus = () => { if (t) return; fStatus.value = fDays.value ? 'В работе' : 'Новая'; };
      fDays.addEventListener('input', autoStatus); if (!t) autoStatus();
      form.append(field('Задача', fTask, 'full'), field('Исполнитель', fP), field('Проект', fPr), field('Раздел состава проекта', fSec), field('Тип', fType), field('Приоритет', fPrio), field('Срок, дней', fDays), field('Дата начала', fStart), field('Оценка часов', fHours), field('Сумма, сум', fAmount), field('Статус', fStatus));
      let fDone, fSrc, fFin, fRew, fMiss;
      if (t) {
        fDone = input('m-done', 'number', isNum(t.done) ? Math.round(t.done * 100) : 0, { min: 0, max: 100, step: 5 });
        fSrc = select('m-src', ['Нет', 'Да'], t.source_ok || 'Нет');
        fFin = input('m-fin', 'date', t.finished || '');
        fRew = input('m-rew', 'number', t.reworks ?? 0, { min: 0, step: 1 });
        fMiss = input('m-miss', 'number', t.missed ?? 0, { min: 0, step: 1 });
        form.append(field('Выполнено, %', fDone), field('Исходник сдан', fSrc), field('Факт. дата сдачи', fFin), field('Доработок', fRew), field('Пропущено отчётов', fMiss));
        const info = el('p', 'note full', `План сдачи: ${fD(t.plan)} · прошло времени: ${fPct(t.elapsed)} · контроль: ${t.control || '—'} · баллы KPI: ${fNum(t.points)}`); form.append(info);
      }
      form.append(field('Комментарий', fComment, 'full'));
      m.append(form);
      if (t && !CLOSED.includes(t.status)) {
        const qa = el('div', 'chips');
        const mk = (label, cls, fn) => { const b = el('button', 'btn sm ' + (cls || ''), label); b.type = 'button'; b.addEventListener('click', fn); return b; };
        qa.append(el('span', 'note', 'Быстро:'),
          mk('Принять работу', '', () => { fStatus.value = 'Принята'; fDone.value = 100; if (!fFin.value) fFin.value = iso(today()); }),
          mk('Вернуть на доработку', '', () => { fStatus.value = 'На доработке'; fRew.value = (Number(fRew.value) || 0) + 1; fFin.value = ''; }),
          mk('Исходник получен', '', () => { fSrc.value = 'Да'; }),
          mk('Есть вопрос', '', () => { fStatus.value = 'Есть вопрос'; }));
        m.append(qa);
      }
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); foot.append(err);
      const cancel = el('button', 'btn ghost', 'Отмена'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const save = el('button', 'btn primary', t ? 'Сохранить' : 'Поставить задачу'); save.type = 'button';
      const more = t ? null : el('button', 'btn', 'Сохранить и ещё');
      foot.append(cancel); if (more) { more.type = 'button'; foot.append(more); } foot.append(save); m.append(foot);
      const collect = () => {
        const v = { task: fTask.value.trim(), assignee: fP.value, project: fPr.value, type: fType.value, priority: Number(fPrio.value), days: fDays.value === '' ? null : Number(fDays.value), start: fStart.value || null, hours: fHours.value === '' ? null : Number(fHours.value), amount: fAmount.value === '' ? null : Number(fAmount.value), status: fStatus.value, comment: fComment.value.trim(), section: fSec.value === '' ? null : Number(fSec.value) };
        if (t) Object.assign(v, { done: Math.max(0, Math.min(100, Number(fDone.value) || 0)) / 100, source_ok: fSrc.value, finished: fFin.value || null, reworks: Number(fRew.value) || 0, missed: Number(fMiss.value) || 0 });
        if (!v.task) return 'Напишите, что нужно сделать.';
        if (!v.assignee) return 'Выберите исполнителя.';
        if (!v.project) return 'Выберите проект.';
        if (v.days != null && (v.days < 0 || !Number.isFinite(v.days))) return 'Срок должен быть числом дней.';
        if (v.status === 'Принята' && !v.finished) v.finished = iso(today());
        return v;
      };
      const go = async (again) => {
        const v = collect(); if (typeof v === 'string') { err.textContent = v; return; }
        err.textContent = ''; [save, more].forEach((b) => b && (b.disabled = true)); save.textContent = 'Сохраняю…';
        try {
          if (t) await updateTask(t, v); else await addTask(v);
          toast(t ? `Задача №${t.id} сохранена` : 'Задача поставлена');
          if (again) { close(); openTask(null, { assignee: v.assignee, project: v.project }); } else close();
          refreshAll();
        } catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); [save, more].forEach((b) => b && (b.disabled = false)); save.textContent = t ? 'Сохранить' : 'Поставить задачу'; }
      };
      save.addEventListener('click', () => go(false)); if (more) more.addEventListener('click', () => go(true));
    });
  }
  const userErr = (text) => { const e = new Error(text); e.userText = text; return e; };
  // the server assigns №, logs the status and notifies the assignee
  async function addTask(v) {
    return apiFetch(API.tasks, { task: v.task, assignee: v.assignee, project: v.project, type: v.type || '', priority: v.priority || 2, days: v.days ?? null, start: v.start || null, hours: v.hours ?? null, amount: v.amount ?? null, status: v.status || '', comment: v.comment || '', section: v.section ?? null, flow: v.flow || (isNum(v.section) ? 'Проект' : 'Нестандартная'), stage: v.stage || '', dept: v.dept || '', tz: v.tz || '' });
  }
  async function updateTask(t, v) {
    return apiFetch(taskUrl(t.id, 'edit'), v);
  }

  // ---------- OPERATION modal
  function openOp(preset = {}) {
    if (!S.mcp) return toast('Сервер недоступен.');
    const L = S.d.lists || { cats: [], methods: ['Наличные', 'Перечисление'] }; const rate = S.d.rate || S.d.home?.rate || null;
    const c0 = preset.contract || null;
    modal('Новая операция', (m, close) => {
      let kind = c0 ? (c0.side === 'Заказчик' ? 'Приход' : 'Расход') : 'Расход';
      let pending = null; let resetConfirm = () => {};
      const seg = el('div', 'seg'); const kinds = ['Приход', 'Расход', 'Перевод'];
      const segBtns = kinds.map((k) => { const b = el('button', null, k); b.type = 'button'; b.addEventListener('click', () => { kind = k; resetConfirm(); sync(true); }); seg.append(b); return b; });
      const projects = (S.d.projects || []).filter((p) => p.status !== 'Закрыт').map((p) => p.name);
      const fDate = input('o-date', 'date', iso(today()));
      const fProj = select('o-proj', [new Option('— проект —', ''), ...projects.map((p) => new Option(p, p))], c0?.project || S.filters.project || '');
      const fTo = select('o-to', [new Option('— куда —', ''), ...projects.map((p) => new Option(p, p))], 'GASTEC');
      const fWho = input('o-who', 'text', c0?.name || '', { list: 'o-who-list', autocomplete: 'off', placeholder: 'кому / от кого' });
      const dl = el('datalist'); dl.id = 'o-who-list'; [...new Set([...(S.d.people || []).map((p) => p.name), ...projects, 'Заказчик'])].forEach((n) => dl.append(new Option(n)));
      const fCat = select('o-cat', [new Option('— категория —', ''), ...L.cats.filter((c) => c !== 'Начальный остаток').map((c) => new Option(c, c))], '');
      const fUzs = input('o-uzs', 'number', '', { step: 1000, placeholder: '0' });
      const fUsdIn = input('o-usd', 'number', '', { step: 1, placeholder: '0' });
      const fMethod = select('o-method', (L.methods.length ? L.methods : ['Наличные', 'Перечисление']), 'Наличные');
      const fContract = select('o-contract', [new Option('— без договора —', '')], '');
      const fOffset = input('o-offset', 'number', '', { min: 0, step: 1 });
      const fNote = input('o-note', 'text', '', { placeholder: 'необязательно' });
      const hint = el('p', 'note full');
      const form = el('div', 'form');
      const lTo = field('Куда (проект)', fTo); const lWho = field('Кто / контрагент', fWho); const lCat = field('Категория', fCat); const lContract = field('Договор', fContract); const lOffset = field('Зачёт по договору (в валюте договора)', fOffset); const lMethod = field('Способ', fMethod);
      form.append(field('Дата', fDate), field('Проект' , fProj), lTo, lWho, lCat, field('Сумма, сум', fUzs), field('Сумма, $', fUsdIn), lMethod, lContract, lOffset, field('Примечание', fNote, 'full'), hint, dl);
      const conf = el('div', 'confirm'); conf.hidden = true;
      m.append(seg, form, conf);
      const contractsFor = () => (S.d.contracts || []).filter((c) => c.status === 'Открыт' && (!fProj.value || c.project === fProj.value) && (!fWho.value.trim() || c.name === fWho.value.trim()));
      const fillContracts = () => { const cur = fContract.value || c0?.id || ''; const list = contractsFor(); fContract.replaceChildren(new Option('— без договора —', ''), ...list.map((c) => new Option(`${c.id} · ${c.name} · ${c.section || ''} · остаток ${fNum(c.rest)} ${c.cur || ''}`, c.id))); fContract.value = list.some((c) => c.id === cur) ? cur : ''; };
      const contract = () => (S.d.contracts || []).find((c) => c.id === fContract.value);
      const calcOffset = () => { const c = contract(); if (!c) { fOffset.value = ''; return; } const uzs = Math.abs(Number(fUzs.value) || 0), usd = Math.abs(Number(fUsdIn.value) || 0); fOffset.value = c.cur === 'USD' ? (usd || (rate ? Math.round(uzs / rate) : '')) : (uzs || (rate ? usd * rate : '')); };
      function sync(kindChanged) {
        segBtns.forEach((b, i) => b.setAttribute('aria-pressed', String(kinds[i] === kind)));
        const tr = kind === 'Перевод'; lTo.hidden = !tr; lWho.hidden = tr; lCat.hidden = tr; lContract.hidden = tr; lOffset.hidden = tr;
        if (kindChanged && !tr) fCat.value = kind === 'Приход' ? 'Оплата заказчика' : (fCat.value && fCat.value !== 'Оплата заказчика' ? fCat.value : 'Оплата исполнителю');
        if (kindChanged && c0) fCat.value = c0.side === 'Заказчик' ? 'Оплата заказчика' : c0.side === 'Налог' ? 'Налоги' : 'Оплата исполнителю';
        const conv = fCat.value === 'Конвертация';
        hint.textContent = tr ? 'Перевод между проектами запишется двумя строками: минус в первом проекте, плюс во втором.' : conv ? 'Конвертация: впишите обе суммы со своими знаками (что ушло — с минусом, что пришло — с плюсом).' : `Суммы пишите без знака: ${kind === 'Расход' ? 'расход запишется с минусом' : 'приход запишется с плюсом'}. Можно заполнить одну или обе валюты.`;
        fillContracts();
      }
      [fProj, fWho].forEach((x) => x.addEventListener('change', () => { fillContracts(); calcOffset(); }));
      fWho.addEventListener('input', () => fillContracts());
      [fUzs, fUsdIn].forEach((x) => x.addEventListener('input', calcOffset)); fContract.addEventListener('change', calcOffset); fCat.addEventListener('change', () => sync(false));
      sync(true); if (c0) { fContract.value = c0.id; }
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); const cancel = el('button', 'btn ghost', 'Отмена'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const next = el('button', 'btn primary', 'Проверить'); next.type = 'button'; foot.append(err, cancel, next); m.append(foot);
      resetConfirm = () => { pending = null; conf.hidden = true; next.textContent = 'Проверить'; };
      const build = () => {
        const date = fDate.value; if (!date) return 'Укажите дату.';
        const proj = fProj.value; if (!proj) return 'Выберите проект.';
        const conv = fCat.value === 'Конвертация';
        let uzs = fUzs.value === '' ? null : Number(fUzs.value), usd = fUsdIn.value === '' ? null : Number(fUsdIn.value);
        if (!uzs && !usd) return 'Впишите сумму в сумах или в долларах.';
        const sign = (x) => (x == null ? null : conv ? x : kind === 'Расход' || kind === 'Перевод' ? -Math.abs(x) : Math.abs(x));
        const d = parseD(date); const by = 'Сайт'; const at = ruDate(new Date()) + ' ' + new Date().toTimeString().slice(0, 5);
        if (kind === 'Перевод') {
          const to = fTo.value; if (!to) return 'Выберите, в какой проект перевод.'; if (to === proj) return 'Проекты перевода совпадают.';
          return { rows: [
            [null, ruDate(d), proj, to, 'Расход', 'Перевод между проектами', sign(uzs) ?? '', sign(usd) ?? '', fMethod.value, '', '', fNote.value, by, at],
            [null, ruDate(d), to, proj, 'Приход', 'Перевод между проектами', uzs != null ? Math.abs(uzs) : '', usd != null ? Math.abs(usd) : '', fMethod.value, '', '', fNote.value, by, at]],
            text: `Перевод ${uzs ? fNum(Math.abs(uzs)) + ' сум ' : ''}${usd ? fUsd(Math.abs(usd)) : ''} из «${proj}» в «${to}» (две строки).` };
        }
        const who = fWho.value.trim(); if (!who) return 'Укажите, кому или от кого.';
        if (!fCat.value) return 'Выберите категорию.';
        const c = contract(); const off = fOffset.value === '' ? '' : Math.abs(Number(fOffset.value));
        if (c && off === '') return 'Укажите сумму зачёта по договору.';
        const type = conv ? 'Расход' : kind;
        return { rows: [[null, ruDate(d), proj, who, type, fCat.value, sign(uzs) ?? '', sign(usd) ?? '', fMethod.value, c ? c.id : '', c ? off : '', fNote.value, by, at]],
          text: `${type} ${uzs ? fNum(sign(uzs)) + ' сум ' : ''}${usd ? (sign(usd) < 0 ? '−' : '') + fUsd(Math.abs(usd)) : ''} · ${proj} · ${who} · ${fCat.value}` + (c ? ` · договор ${c.id}, зачёт ${fNum(off)} ${c.cur}` : '') };
      };
      next.addEventListener('click', async () => {
        if (!pending) {
          const r = build(); if (typeof r === 'string') { err.textContent = r; return; }
          err.textContent = ''; pending = r; conf.hidden = false; conf.replaceChildren(el('div', null, 'Будет записано в «Операции»:'), el('b', null, r.text)); next.textContent = 'Записать'; return;
        }
        next.disabled = true; next.textContent = 'Записываю…';
        try {
          // the rows keep the old sheet column order; the server numbers them and writes them to Finance
          const rows = pending.rows.map((r) => ({ date: fDate.value, project: r[2], who: r[3], type: r[4], cat: r[5], uzs: r[6] === '' ? null : r[6], usd: r[7] === '' ? null : r[7], method: r[8], contract: r[9] || null, offset: r[10] === '' ? null : r[10], note: r[11] }));
          await apiFetch(API.ops, { rows });
          toast('Операция записана'); close(); refreshAll();
        } catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); next.disabled = false; next.textContent = 'Записать'; }
      });
      // editing anything after review resets the confirmation
      m.addEventListener('input', () => { if (pending) { pending = null; conf.hidden = true; next.textContent = 'Проверить'; } });
      m.addEventListener('change', (e) => { if (pending && e.target !== next) { pending = null; conf.hidden = true; next.textContent = 'Проверить'; } });
    });
  }

  // ---------- quick add
  $('#q-save').addEventListener('click', async () => {
    const task = $('#q-task').value.trim(), assignee = $('#q-person').value, project = $('#q-project').value, days = $('#q-days').value;
    if (!task) return toast('Напишите, что нужно сделать.'); if (!assignee) return toast('Выберите, кому.'); if (!project) return toast('Выберите проект.');
    const b = $('#q-save'); b.disabled = true; b.textContent = 'Ставлю…';
    try { await addTask({ task, assignee, project, type: '', priority: 2, days: days === '' ? null : Number(days), start: iso(today()), hours: null, amount: null, status: days === '' ? 'Новая' : 'В работе', comment: '', section: null }); toast('Задача поставлена: ' + assignee); $('#q-task').value = ''; $('#q-days').value = ''; refreshAll(); }
    catch (e) { toast(e && e.userText ? e.userText : errText(e)); }
    finally { b.disabled = false; b.textContent = 'Поставить'; }
  });
  $('#q-task').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('#q-save').click(); });

  // ---------- PROJECT PLAN: состав проекта, связи, расчёт сроков, график
  const PF = ['id', 'project', 'wbs', 'code', 'name', 'kind', 'owner', 'dur', 'preds', 'snet', 'as', 'af', 'pct', 'cs', 'cf', 'bs', 'bf', 'client', 'comment', 'inPlan', 'doc', 'pay', 'price', 'cur', 'contract', 'task', 'closed'];
  const LT = { 'ОН': 'ОН', 'НН': 'НН', 'ОО': 'ОО', 'НО': 'НО', FS: 'ОН', SS: 'НН', FF: 'ОО', SF: 'НО' };
  const LT_NAME = { 'ОН': 'окончание → начало', 'НН': 'начало → начало', 'ОО': 'окончание → окончание', 'НО': 'начало → окончание' };
  const dn = (s) => { const [y, m, d] = s.split('-').map(Number); return Math.round(Date.UTC(y, m - 1, d) / DAY); };
  const dIso = (n) => { const d = new Date(n * DAY); return d.getUTCFullYear() + '-' + pad(d.getUTCMonth() + 1) + '-' + pad(d.getUTCDate()); };
  const todayN = () => dn(iso(today()));
  const fN = (n) => (n == null ? '—' : fD(dIso(n)));
  const fNs = (n) => { if (n == null) return '—'; const d = new Date(n * DAY); return pad(d.getUTCDate()) + '.' + pad(d.getUTCMonth() + 1) + '.' + String(d.getUTCFullYear()).slice(2); };
  const wdOf = (n) => (((n + 4) % 7) + 7) % 7; // 0 = воскресенье

  // rows that take part in the schedule: everything not marked «Нет», plus objects that hold such rows
  function planSubset(rows) {
    const inn = rows.filter((r) => r.kind !== 'Объект' && r.inPlan !== 'Нет');
    const objs = rows.filter((r) => r.kind === 'Объект' && str(r.wbs) && inn.some((x) => x.project === r.project && str(x.wbs).startsWith(str(r.wbs) + '.')));
    return [...objs, ...inn];
  }
  function makeCal(values) {
    const off = new Set(), on = new Set(); let week = 5;
    (values || []).forEach((r, i) => {
      if (i === 0) return;
      const d = toDate(r[0]); if (d) (/рабоч/i.test(str(r[2])) ? on : off).add(dn(d));
      if (/Рабочих дней/i.test(str(r[4])) && toNum(r[5]) === 6) week = 6;
    });
    const isWork = (n) => { if (on.has(n)) return true; if (off.has(n)) return false; const w = wdOf(n); return week === 6 ? w !== 0 : w !== 0 && w !== 6; };
    const next = (n) => { let k = 0; while (!isWork(n) && k++ < 400) n++; return n; };
    const prev = (n) => { let k = 0; while (!isWork(n) && k++ < 400) n--; return n; };
    const shift = (n, k) => { n = next(n); if (k > 0) for (let i = 0; i < k; i++) n = next(n + 1); else for (let i = 0; i < -k; i++) n = prev(n - 1); return n; };
    const count = (a, b) => { let c = 0; for (let n = a; n < b; n++) if (isWork(n)) c++; return c; };
    return { isWork, next, prev, shift, count, week, holidays: off.size };
  }
  function parsePreds(s) {
    const links = [], bad = [];
    str(s).split(/[;,]/).map((x) => x.trim()).filter(Boolean).forEach((tok) => {
      const m = tok.replace(/\s+/g, '').match(/^(\d+)([A-Za-zА-Яа-яЁё]{2})?([+\-−–]\d+)?(?:дн?\.?|d)?$/i);
      if (!m) { bad.push(tok); return; }
      const ty = m[2] ? LT[m[2].toUpperCase()] : 'ОН'; if (!ty) { bad.push(tok); return; }
      links.push({ id: Number(m[1]), type: ty, lag: m[3] ? Number(m[3].replace(/[−–]/, '-')) : 0 });
    });
    return { links, bad };
  }
  const fmtLink = (l) => l.id + (l.type !== 'ОН' || l.lag ? l.type : '') + (l.lag ? (l.lag > 0 ? '+' : '') + l.lag : '');
  const wbsCmp = (a, b) => { const x = str(a).split('.').map(Number), y = str(b).split('.').map(Number); for (let i = 0; i < Math.max(x.length, y.length); i++) { const p = x[i] ?? -1, q = y[i] ?? -1; if (p !== q) return (Number.isNaN(p) ? 0 : p) - (Number.isNaN(q) ? 0 : q); } return 0; };

  // Расчёт сроков. Границы (S, E) — начало рабочего дня; E = день после последнего рабочего дня.
  function schedule(rows, cal, tasks) {
    const T = todayN();
    const R = rows.map((r) => ({ ...r, kids: [], errs: [] }));
    const byId = new Map(R.map((r) => [r.id, r]));
    const byProj = d3.group(R, (r) => r.project);
    const projErr = new Map();
    byProj.forEach((list) => {
      list.sort((a, b) => wbsCmp(a.wbs, b.wbs) || a.id - b.id);
      const byW = new Map(list.filter((r) => str(r.wbs)).map((r) => [str(r.wbs), r]));
      list.forEach((r) => { let w = str(r.wbs); r.level = w ? w.split('.').length - 1 : 0; let p = null; while (w.includes('.')) { w = w.slice(0, w.lastIndexOf('.')); if (byW.has(w)) { p = byW.get(w); break; } } r.parent = p; if (p) p.kids.push(r); });
    });
    R.forEach((r) => {
      r.summary = r.kids.length > 0; r.mile = !r.summary && (r.kind === 'Веха' || r.dur === 0);
      r.d = r.summary || r.mile ? 0 : Math.max(1, Math.round(isNum(r.dur) ? r.dur : 1));
      const p = parsePreds(r.preds); r.links = p.links; if (p.bad.length) r.errs.push('не понял связь «' + p.bad.join('», «') + '»');
    });
    const anc = (r) => { const a = []; let p = r.parent; while (p) { a.push(p); p = p.parent; } return a; };
    const inside = (a, b) => { let p = a.parent; while (p) { if (p === b) return true; p = p.parent; } return false; };
    R.forEach((r) => { r.links = r.links.filter((l) => { const p = byId.get(l.id); if (!p) { r.errs.push(`нет раздела с ID ${l.id}`); return false; } if (p === r || inside(r, p) || inside(p, r)) { r.errs.push(`связь ${l.id} ведёт на свой же этап`); return false; } return true; }); });
    const pStart = new Map();
    byProj.forEach((list, proj) => { const c = list.flatMap((r) => [r.snet, r.as]).filter(Boolean).map(dn); pStart.set(proj, cal.next(c.length ? Math.min(...c) : T)); });
    const leaves = R.filter((r) => !r.summary);
    const sums = R.filter((r) => r.summary).sort((a, b) => b.level - a.level);
    const rollup = () => sums.forEach((s) => { const ks = s.kids.filter((k) => k.S != null); if (!ks.length) return; s.S = Math.min(...ks.map((k) => k.S)); s.E = Math.max(...ks.map((k) => k.E)); });
    let changed = true, pass = 0; const maxPass = R.length + 6;
    while (changed && pass < maxPass) {
      changed = false; pass++;
      leaves.forEach((r) => {
        const bounds = [{ b: pStart.get(r.project), f: false }];
        [r, ...anc(r)].forEach((x) => {
          if (x.snet) bounds.push({ b: cal.next(dn(x.snet)), f: false });
          x.links.forEach((l) => {
            const p = byId.get(l.id); if (p.S == null) return;
            if (l.type === 'ОН') bounds.push({ b: cal.shift(p.E, l.lag), f: true });
            else if (l.type === 'НН') bounds.push({ b: cal.shift(p.S, l.lag), f: false });
            else if (l.type === 'ОО') bounds.push({ b: cal.shift(cal.shift(p.E, l.lag), -r.d), f: true });
            else bounds.push({ b: cal.shift(cal.shift(p.S, l.lag), -r.d), f: true });
          });
        });
        const lb = Math.max(...bounds.map((x) => x.b));
        let S0 = cal.next(lb), E0; const fin = bounds.some((x) => x.f && x.b === lb);
        if (r.as) S0 = cal.next(dn(r.as));
        if (r.af) { if (r.mile) { S0 = E0 = cal.next(dn(r.af)); } else { E0 = cal.next(dn(r.af) + 1); if (!r.as) S0 = cal.shift(E0, -r.d); } }
        else E0 = r.mile ? S0 : cal.shift(S0, r.d);
        if (E0 < S0) E0 = S0;
        if (r.S !== S0 || r.E !== E0) { r.S = S0; r.E = E0; changed = true; }
        r.fin = fin && !r.af && !r.as;
      });
      rollup();
    }
    if (changed) byProj.forEach((list, proj) => { if (list.some((r) => r.links.length)) projErr.set(proj, 'Связи замкнуты в кольцо: раздел зависит сам от себя через другие. Проверьте колонку «Связи».'); });
    // даты для показа
    R.forEach((r) => {
      if (r.S == null) return;
      if (r.mile) { r.Sd = r.Fd = r.fin ? cal.prev(r.S - 1) : r.S; }
      else { r.Sd = r.S; r.Fd = Math.max(r.S, cal.prev(r.E - 1)); }
      r.wdays = r.mile ? 0 : cal.count(r.S, r.E);
    });
    // выполнение: из задач, привязанных к разделу, иначе вручную
    leaves.forEach((r) => {
      const ts = (tasks || []).filter((t) => t.section === r.id && t.status !== 'Отменена'); r.tasks = ts;
      if (ts.length) { const w = ts.map((t) => t.hours || 1); r.p = d3.sum(ts, (t, i) => w[i] * (t.status === 'Принята' ? 1 : Math.min(1, Math.max(0, t.done || 0)))) / d3.sum(w); r.pSrc = 'tasks'; }
      else { r.p = r.af ? 1 : isNum(r.pct) ? Math.min(1, Math.max(0, r.pct)) : 0; r.pSrc = 'manual'; }
      r.w = r.mile ? 0 : r.d;
    });
    sums.forEach((s) => { s.w = d3.sum(s.kids, (k) => k.w); s.p = s.w ? d3.sum(s.kids, (k) => k.p * k.w) / s.w : d3.mean(s.kids, (k) => k.p) || 0; s.tasks = []; });
    R.forEach((r) => {
      if (r.Sd == null) return;
      if (r.p >= 0.999) r.state = 'done';
      else if (r.Fd < T) r.state = 'late';
      else if (r.Sd <= T && !r.mile) { const exp = cal.count(r.S, Math.min(T + 1, r.E)) / Math.max(1, cal.count(r.S, r.E)); r.state = exp - r.p > 0.15 ? 'behind' : 'work'; }
      else r.state = 'plan';
      if (r.bf) { const b = dn(r.bf); r.varD = r.Fd > b ? cal.count(b + 1, r.Fd + 1) : -cal.count(r.Fd + 1, b + 1); }
    });
    // этапы после проектирования (смета, оформление, печать) — хвост после полосы раздела
    leaves.forEach((r) => {
      if (r.mile || !str(r.code) || r.S == null || r.kind === 'Объект') return;
      const rest = stagesFor(r).slice(1); let cur = r.E;
      r.tails = rest.map((st) => { const d = Math.max(1, st.days || 1); const s0 = cal.next(cur); const e0 = cal.shift(cur, d); cur = e0; const tk = (tasks || []).filter((t) => t.section === r.id && t.stage === st.name && t.status !== 'Отменена').sort((a, b) => b.id - a.id)[0]; return { st: st.name, Sd: s0, Fd: Math.max(s0, cal.prev(e0 - 1)), done: tk ? (tk.status === 'Принята' ? 1 : tk.done || 0) : 0 }; });
      r.TFd = r.tails.length ? r.tails[r.tails.length - 1].Fd : r.Fd;
    });
    sums.forEach((s) => { const ks = s.kids.filter((k) => k.Fd != null); if (ks.length) s.TFd = Math.max(...ks.map((k) => k.TFd ?? k.Fd)); });
    // критический путь (обратный проход по разделам без вложенных)
    const leavesOf = (s) => (s.summary ? s.kids.flatMap(leavesOf) : [s]);
    byProj.forEach((list) => {
      const lv = list.filter((r) => !r.summary && r.S != null); if (!lv.length) return;
      const end = Math.max(...lv.map((r) => r.E)); lv.forEach((r) => { r.LE = end; });
      const flat = [];
      lv.forEach((s) => [s, ...anc(s)].forEach((x) => x.links.forEach((l) => leavesOf(byId.get(l.id)).forEach((pp) => { if (pp.project === s.project && pp.S != null && pp !== s) flat.push({ p: pp, s, l }); }))));
      let ch = true, k = 0;
      while (ch && k++ < lv.length + 6) {
        ch = false;
        flat.forEach(({ p, s, l }) => {
          const LS = cal.shift(s.LE, -s.d); let le;
          if (l.type === 'ОН') le = cal.shift(LS, -l.lag);
          else if (l.type === 'НН') le = cal.shift(cal.shift(LS, -l.lag), p.d);
          else if (l.type === 'ОО') le = cal.shift(s.LE, -l.lag);
          else le = cal.shift(cal.shift(s.LE, -l.lag), p.d);
          if (le < p.LE) { p.LE = le; ch = true; }
        });
      }
      lv.forEach((r) => { r.slack = r.LE > r.E ? cal.count(r.E, r.LE) : 0; r.crit = r.p < 0.999 && r.slack <= 0; });
    });
    sums.forEach((s) => { s.crit = leavesOf(s).some((x) => x.crit); });
    const order = [...byProj.values()].flat();
    return { rows: order, byId, projErr };
  }

  // ---------- render tab
  function planLegend() {
    const it = [['В работе / по плану', 'var(--ink)'], ['Отстаёт', 'var(--warn)'], ['Просрочен', 'var(--bad)'], ['Выполнен', 'var(--ok)'], ['Этап', 'var(--fg)']];
    const out = it.map(([n, c]) => { const s = el('span'); const sw = el('i', 'sw'); sw.style.background = c; s.append(sw, document.createTextNode(n)); return s; });
    const m = el('span'); const d = el('i', 'sw dia'); m.append(d, document.createTextNode('Веха')); out.push(m);
    if (S.pl.base) { const s = el('span'); const sw = el('i', 'sw'); sw.style.background = 'var(--muted-bar)'; sw.style.height = '4px'; s.append(sw, document.createTextNode('Базовый план')); out.push(s); }
    if (S.pl.crit) { const s = el('span'); const sw = el('i', 'sw'); sw.style.border = '2px solid var(--bad)'; s.append(sw, document.createTextNode('Критический путь')); out.push(s); }
    if (S.pl.tails) Object.entries(STAGE_CLR).forEach(([n, c]) => { const s = el('span'); const sw = el('i', 'sw'); sw.style.background = c; s.append(sw, document.createTextNode(n)); out.push(s); });
    return out;
  }
  function projStats(rows) {
    const cal = S.d.cal; const lv = rows.filter((r) => !r.summary && r.Sd != null);
    if (!lv.length) return null;
    const s = d3.min(lv, (r) => r.Sd), f = d3.max(lv, (r) => r.Fd);
    const w = d3.sum(lv, (r) => r.w); const p = w ? d3.sum(lv, (r) => r.w * r.p) / w : d3.mean(lv, (r) => r.p) || 0;
    const bfs = lv.filter((r) => r.bf).map((r) => dn(r.bf)); const bf = bfs.length ? Math.max(...bfs) : null;
    const varD = bf != null ? (f > bf ? cal.count(bf + 1, f + 1) : -cal.count(f + 1, bf + 1)) : null;
    const tf = S.pl.tails ? d3.max(lv, (r) => r.TFd ?? r.Fd) : null;
    return { s, f, tf, days: cal.count(s, f + 1), p, bf, varD, late: lv.filter((r) => r.state === 'late').length, behind: lv.filter((r) => r.state === 'behind').length, crit: lv.filter((r) => r.crit).length, n: lv.filter((r) => !r.mile).length };
  }
  function planProjects() {
    const planRows = S.d.plan || [];
    const all = [...new Set([...planRows.map((r) => r.project), ...(S.d.projects || []).filter((p) => p.status !== 'Закрыт').map((p) => p.name)])];
    if (isMgr()) return all.filter(inMyProjects);
    const me = viewer().person; const mine = new Set((S.d.tasks || []).filter((t) => t.assignee === me).map((t) => t.project));
    return all.filter((p) => mine.has(p) || (viewer().projects || []).includes(p));
  }
  function renderPlan() {
    const sel = $('#pl-project'); const planRows = S.d.plan || []; const projs = planProjects();
    if (!S.pl.project || !projs.includes(S.pl.project)) S.pl.project = (S.filters.project && projs.includes(S.filters.project)) ? S.filters.project : (planRows[0]?.project || projs[0] || '');
    if (document.activeElement !== sel) { const cnt = d3.rollup(planRows, (v) => v.length, (r) => r.project); sel.replaceChildren(...projs.map((p) => new Option(cnt.get(p) ? `${p} · ${cnt.get(p)}` : p, p))); sel.value = S.pl.project; }
    $$('#pl-zoom button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.z === S.pl.zoom)));
    $('#pl-owners').checked = S.pl.owners; $('#pl-crit').checked = S.pl.crit; $('#pl-basechk').checked = S.pl.base; $('#pl-links').checked = S.pl.links;
    $('#pl-legend').replaceChildren(...planLegend());
    const box = $('#pl-chart'), sum = $('#pl-sum'), errs = $('#pl-errs');
    if (!S.d.sched) { sum.replaceChildren(); errs.replaceChildren(); if (status('plan') === 'error') failIn(box, 'plan'); else skel(box, 240); return; }
    const rows = S.d.sched.rows.filter((r) => r.project === S.pl.project);
    ['#pl-base', '#pl-xlsx', '#pl-pdf'].forEach((s) => { $(s).hidden = !isMgr() || !rows.length || (s !== '#pl-base' && !S.dl); });
    ['#pl-add', '#pl-tpl'].forEach((s) => { $(s).hidden = !isMgr(); });
    $('#pl-tails').checked = S.pl.tails;
    errs.replaceChildren();
    if ((S.d.planMissing || []).length) { const b = el('div', 'banner'); b.append(el('span', null, 'На листе «Состав проекта» не найдены колонки: ' + S.d.planMissing.join(', ') + '. Верните заголовки, иначе расчёт неполный.')); errs.append(b); }
    const compN = (S.d.plan || []).filter((r) => r.project === S.pl.project && r.kind === 'Раздел' && r.inPlan === 'Нет').length;
    if (!rows.length && compN) {
      sum.replaceChildren();
      const e = el('div', 'pl-empty'); e.append(el('h3', null, `Состав «${S.pl.project}» готов, но ещё не в графике`), el('p', 'note', `${compN} ${plural(compN, 'раздел', 'раздела', 'разделов')} ждут переноса. При переносе разделы получат длительности и типовые связи, сроки рассчитаются.`));
      const b1 = el('button', 'btn primary', 'Перенести в график'); b1.type = 'button'; b1.addEventListener('click', () => openTransfer(S.pl.project)); const b2 = el('button', 'btn', 'Открыть состав'); b2.type = 'button'; b2.addEventListener('click', () => goTab('comp'));
      const bb = el('div', 'chips'); bb.append(b1, b2); e.append(bb); box.replaceChildren(e); return;
    }
    if (!rows.length) {
      sum.replaceChildren();
      const e = el('div', 'pl-empty'); e.append(el('h3', null, `В проекте «${S.pl.project || '—'}» пока нет состава`), el('p', 'note', 'Начните с типового состава проектной документации (исходные данные, ТХ, ГП, АР, КЖ, КМ, ЭС, ОВ, ВК, АТХ, ПОС, смета, экспертиза) со связями между разделами. Потом поправьте сроки и связи под этот объект. Или добавьте разделы по одному.'));
      const bb = el('div', 'chips'); const b1 = el('button', 'btn primary', 'Типовой состав'); b1.type = 'button'; b1.addEventListener('click', () => openTemplate(S.pl.project)); const b2 = el('button', 'btn', '+ Раздел'); b2.type = 'button'; b2.addEventListener('click', () => openPlan(null, { project: S.pl.project })); bb.append(b1, b2); e.append(bb);
      box.replaceChildren(e); return;
    }
    const st = projStats(rows);
    if (st) {
      const item = (k, v, cls) => { const s = el('span', 'pl-kv'); s.append(el('span', null, k + ' '), el('b', cls || null, v)); return s; };
      const items = [item('Начало', fN(st.s)), item('Окончание', fN(st.f)), item('Длительность', `${fNum(st.days)} раб. дн.`), item('Выполнено', fPct(st.p))];
      if (st.bf != null) items.push(item('По базовому плану', fN(st.bf)), item('Отклонение', st.varD > 0 ? `+${st.varD} раб. дн.` : st.varD < 0 ? `${st.varD} раб. дн.` : 'нет', st.varD > 0 ? 'bad' : st.varD < 0 ? 'ok' : null));
      if (st.tf != null && st.tf > st.f) items.splice(2, 0, item('Выдача с оформлением и печатью', fN(st.tf)));
      items.push(item('Разделов', fNum(st.n)));
      if (st.late) items.push(item('Просрочено', fNum(st.late), 'bad'));
      if (st.behind) items.push(item('Отстают', fNum(st.behind), 'warn'));
      if (S.pl.crit) items.push(item('На критическом пути', fNum(st.crit)));
      sum.replaceChildren(...items);
    }
    const pe = S.d.sched.projErr.get(S.pl.project); const bad = rows.filter((r) => r.errs.length);
    if (pe || bad.length) {
      const b = el('div', 'banner bad'); const ul = el('div', 'pl-errlist');
      if (pe) ul.append(el('div', null, pe));
      bad.forEach((r) => { const a = el('button', 'linkbtn', `ID ${r.id} ${r.code || ''} ${r.name || ''}`.replace(/\s+/g, ' ')); a.type = 'button'; a.addEventListener('click', () => openPlan(r.id)); const d = el('div'); d.append(a, document.createTextNode(': ' + r.errs.join('; '))); ul.append(d); });
      b.append(ul); errs.append(b);
    }
    drawPlan(box, rows);
  }

  // point lists for dependency arrows; a = {x, y, dir}, b = {x, y, arr}
  function linkPts(a, b, rowH) {
    const ax = a.x + a.dir * 7, tx = b.x - b.arr * 7;
    if (a.dir !== b.arr) { const xm = a.dir < 0 ? Math.min(ax, tx) : Math.max(ax, tx); return [[a.x, a.y], [xm, a.y], [xm, b.y], [b.x, b.y]]; }
    if ((tx - ax) * a.dir >= 0) return [[a.x, a.y], [tx, a.y], [tx, b.y], [b.x, b.y]];
    const my = b.y - Math.sign(b.y - a.y || 1) * rowH / 2;
    return [[a.x, a.y], [ax, a.y], [ax, my], [tx, my], [tx, b.y], [b.x, b.y]];
  }
  const LINK_SIDES = { 'ОН': ['e', 1, 's', 1], 'НН': ['s', -1, 's', 1], 'ОО': ['e', 1, 'e', -1], 'НО': ['s', -1, 'e', -1] };
  const anchorX = (r, side, x, pxDay) => { if (r.mile) { const c = x(r.Fd) + pxDay / 2; return side === 's' ? c - 6 : c + 6; } return side === 's' ? x(r.Sd) : x(r.Fd + 1); };
  const planColor = (r) => (r.summary ? 'var(--fg)' : r.state === 'done' ? 'var(--ok)' : r.state === 'late' ? 'var(--bad)' : r.state === 'behind' ? 'var(--warn)' : 'var(--ink)');
  const stateText = { done: 'выполнен', late: 'просрочен', behind: 'отстаёт от графика', work: 'в работе по графику', plan: 'ещё не начат' };

  function drawPlan(box, rows) {
    const W = box.clientWidth; if (!W) return;
    const cal = S.d.cal; const T = todayN(); const narrow = W < 760;
    const COLS = narrow ? [['name', 'Раздел', 0, 'start']] : [['id', 'ID', 34, 'end'], ['wbs', 'WBS', 44, 'start'], ['name', 'Наименование', 0, 'start'], ['dur', 'Дн.', 38, 'end'], ['Sd', 'Начало', 66, 'start'], ['Fd', 'Оконч.', 66, 'start'], ['preds', 'Связи', 86, 'start'], ['p', '%', 42, 'end']];
    const fixed = d3.sum(COLS, (c) => c[2]);
    const nameW = narrow ? Math.round(Math.min(190, W * 0.46)) : Math.max(170, Math.min(340, Math.round(W * 0.58) - fixed));
    COLS.forEach((c) => { if (c[0] === 'name') c[2] = nameW; });
    const labelW = fixed + nameW; let cx = 0; const colX = COLS.map((c) => { const v = cx; cx += c[2]; return v; });
    const rowH = narrow ? 36 : 28, axisH = 46;
    const pxDay = { day: 24, week: 7, month: 2.2 }[S.pl.zoom] || 7;
    const lv = rows.filter((r) => r.Sd != null); if (!lv.length) { box.replaceChildren(el('div', 'empty', 'Не удалось рассчитать сроки.')); return; }
    let d0 = d3.min(lv, (r) => Math.min(r.Sd, r.bs ? dn(r.bs) : Infinity)), d1 = d3.max(lv, (r) => Math.max((S.pl.tails ? r.TFd ?? r.Fd : r.Fd) + 1, r.bf ? dn(r.bf) + 1 : 0));
    if (T >= d0 - 60 && T <= d1 + 60) { d0 = Math.min(d0, T); d1 = Math.max(d1, T + 1); }
    d0 -= 3; d1 += 8;
    const viewW = W - labelW; const tlW = Math.max(viewW, Math.round((d1 - d0) * pxDay + 14));
    const x = (n) => 6 + (n - d0) * pxDay;
    const H = axisH + rows.length * rowH + 6;
    const L = d3.create('svg').attr('width', labelW).attr('height', H).attr('viewBox', `0 0 ${labelW} ${H}`).attr('font-family', 'var(--f-ui)');
    const R = d3.create('svg').attr('width', tlW).attr('height', H).attr('viewBox', `0 0 ${tlW} ${H}`).attr('font-family', 'var(--f-ui)');
    const idx = new Map(rows.map((r, i) => [r.id, i])); const yOf = (i) => axisH + i * rowH;
    // background: summary stripes, non-working days, row lines
    rows.forEach((r, i) => { if (r.summary) [L, R].forEach((s, k) => s.append('rect').attr('x', 0).attr('y', yOf(i)).attr('width', k ? tlW : labelW).attr('height', rowH).attr('fill', 'var(--panel-2)').attr('fill-opacity', k ? 0.55 : 1)); });
    if (pxDay >= 5) { const g = R.append('g'); for (let n = d0; n < d1; n++) if (!cal.isWork(n)) g.append('rect').attr('x', x(n)).attr('y', axisH).attr('width', pxDay).attr('height', H - axisH).attr('fill', 'var(--grid)').attr('fill-opacity', 0.7); }
    [L, R].forEach((s, k) => { const g = s.append('g'); rows.forEach((r, i) => g.append('line').attr('x1', 0).attr('x2', k ? tlW : labelW).attr('y1', yOf(i + 1) - 0.5).attr('y2', yOf(i + 1) - 0.5).attr('stroke', 'var(--grid)')); s.append('line').attr('x1', 0).attr('x2', k ? tlW : labelW).attr('y1', axisH - 0.5).attr('y2', axisH - 0.5).attr('stroke', 'var(--line)'); });
    // axis
    const lab = R.append('g').attr('font-size', 11).attr('fill', 'var(--muted)');
    const grid = R.append('g');
    const D = (n) => new Date(n * DAY);
    for (let n = d0; n < d1; n++) {
      const dt = D(n); const first = dt.getUTCDate() === 1;
      if (S.pl.zoom === 'month') {
        if (first) { grid.append('line').attr('x1', x(n)).attr('x2', x(n)).attr('y1', 22).attr('y2', H).attr('stroke', dt.getUTCMonth() === 0 ? 'var(--line)' : 'var(--grid)'); lab.append('text').attr('x', x(n) + 3).attr('y', 38).text(MONTHS[dt.getUTCMonth()].slice(0, 3)); }
        if ((first && dt.getUTCMonth() === 0) || n === d0) lab.append('text').attr('x', Math.max(x(n), 6) + 3).attr('y', 14).attr('fill', 'var(--fg)').text(dt.getUTCFullYear());
      } else {
        if (first || n === d0) { if (first) grid.append('line').attr('x1', x(n)).attr('x2', x(n)).attr('y1', 0).attr('y2', H).attr('stroke', 'var(--line)'); const room = (S.pl.zoom === 'day' ? 31 : 30) * pxDay; if (x(n) < tlW - 60) lab.append('text').attr('x', Math.max(x(n), 6) + 4).attr('y', 14).attr('fill', 'var(--fg)').text(room > 90 || first ? MONTHS[dt.getUTCMonth()] + ' ' + dt.getUTCFullYear() : ''); }
        if (S.pl.zoom === 'day') { if (!first) grid.append('line').attr('x1', x(n)).attr('x2', x(n)).attr('y1', 24).attr('y2', axisH).attr('stroke', 'var(--grid)'); lab.append('text').attr('x', x(n) + pxDay / 2).attr('y', 38).attr('text-anchor', 'middle').attr('font-family', 'var(--f-num)').attr('font-size', 10).attr('fill', cal.isWork(n) ? 'var(--muted)' : 'var(--faint)').text(dt.getUTCDate()); }
        else if (wdOf(n) === 1) { grid.append('line').attr('x1', x(n)).attr('x2', x(n)).attr('y1', 24).attr('y2', H).attr('stroke', 'var(--grid)'); lab.append('text').attr('x', x(n) + 3).attr('y', 38).attr('font-family', 'var(--f-num)').attr('font-size', 10).text(fDs(new Date(dt.getUTCFullYear(), dt.getUTCMonth(), dt.getUTCDate()))); }
      }
    }
    // left header
    const lh = L.append('g').attr('font-size', 11).attr('fill', 'var(--muted)');
    COLS.forEach((c, i) => lh.append('text').attr('x', c[3] === 'end' ? colX[i] + c[2] - 6 : colX[i] + 6).attr('y', axisH - 12).attr('text-anchor', c[3]).text(c[1]));
    // tooltip
    const tip = el('div', 'tip'); tip.hidden = true;
    const showTip = (r) => (ev) => {
      const lines = [el('div', 't1', `ID ${r.id} · WBS ${r.wbs || '—'}${r.summary ? ' · этап' : r.mile ? ' · веха' : ''}`), el('div', null, `${r.code ? r.code + ' — ' : ''}${r.name || ''}`)];
      lines.push(el('div', null, r.mile ? `Дата: ${fN(r.Fd)}` : `${fN(r.Sd)} → ${fN(r.Fd)} · ${fNum(r.wdays)} раб. дн.`));
      if (!r.mile) lines.push(el('div', null, `Выполнено ${fPct(r.p)}${r.summary ? '' : r.pSrc === 'tasks' ? ` по ${r.tasks.length} ${plural(r.tasks.length, 'задаче', 'задачам', 'задачам')}` : ''} · ${stateText[r.state] || ''}`));
      if (r.links.length) lines.push(el('div', null, 'После: ' + r.links.map((l) => { const p = S.d.sched.byId.get(l.id); return `${p?.code || 'ID ' + l.id} (${LT_NAME[l.type]}${l.lag ? (l.lag > 0 ? ' +' : ' ') + l.lag + ' дн.' : ''})`; }).join(', ')));
      if (r.doc) lines.push(el('div', 'mono', r.doc));
      if (r.owner && S.pl.owners) lines.push(el('div', null, 'Исполнитель: ' + r.owner));
      if (!r.summary && isNum(r.slack) && r.p < 0.999) lines.push(el('div', null, r.slack > 0 ? `Резерв ${r.slack} раб. дн.` : 'На критическом пути: задержка сдвинет окончание проекта'));
      if (isNum(r.varD) && r.varD !== 0) lines.push(el('div', null, `К базовому плану: ${r.varD > 0 ? '+' : ''}${r.varD} раб. дн.`));
      tip.replaceChildren(...lines); placeTip(tip, box, ev);
    };
    const hideTip = () => { tip.hidden = true; };
    // left cells
    rows.forEach((r, i) => {
      const y0 = yOf(i); const g = L.append('g').attr('transform', `translate(0,${y0})`).style('cursor', 'pointer');
      COLS.forEach(([k, , w, anchor], ci) => {
        const tx = anchor === 'end' ? colX[ci] + w - 6 : colX[ci] + 6; const ty = narrow ? 15 : rowH / 2 + 4;
        if (k === 'name') {
          const ind = Math.min(r.level, 6) * 12;
          const t = g.append('text').attr('x', colX[ci] + 6 + ind).attr('y', ty).attr('font-size', 12).attr('fill', 'var(--fg)').attr('font-weight', r.summary ? 600 : 400).text((r.mile ? '◆ ' : '') + (r.code ? r.code + '  ' : '') + (r.name || '—'));
          fit(t, w - 10 - ind);
          if (narrow) fit(g.append('text').attr('x', colX[ci] + 6 + ind).attr('y', 30).attr('font-size', 10).attr('fill', 'var(--muted)').text(r.mile ? fNs(r.Fd) : `${fNs(r.Sd)} – ${fNs(r.Fd)} · ${fPct(r.p)}`), w - 10 - ind);
          return;
        }
        let v = ''; let fill = 'var(--muted)'; let mono = true;
        if (k === 'id') v = r.id; else if (k === 'wbs') v = r.wbs || ''; else if (k === 'dur') { v = r.mile ? '0' : fNum(r.wdays); fill = 'var(--fg)'; }
        else if (k === 'Sd' || k === 'Fd') { v = fNs(r[k]); fill = 'var(--fg)'; }
        else if (k === 'preds') { v = r.links.map(fmtLink).join('; ') || (r.errs.length ? '!' : ''); if (r.errs.length) fill = 'var(--bad)'; }
        else if (k === 'p') { v = r.mile ? (r.state === 'done' ? '✓' : '') : fPct(r.p); fill = r.state === 'late' ? 'var(--bad)' : r.state === 'behind' ? 'var(--warn)' : r.state === 'done' ? 'var(--ok)' : 'var(--fg)'; }
        const t = g.append('text').attr('x', tx).attr('y', ty).attr('text-anchor', anchor).attr('font-size', 11).attr('fill', fill).attr('font-weight', r.summary && k !== 'id' ? 600 : 400).text(v);
        if (mono) t.attr('font-family', 'var(--f-num)');
        if (k === 'preds') fit(t, w - 8);
      });
      g.append('rect').attr('width', labelW).attr('height', rowH).attr('fill', 'transparent').on('mousemove', showTip(r)).on('mouseleave', hideTip).on('click', () => openPlan(r.id));
    });
    // dependency arrows
    if (S.pl.links) {
      const lg = R.append('g').attr('fill', 'none');
      rows.forEach((s, si) => s.links.forEach((l) => {
        const pi = idx.get(l.id); if (pi == null) return; const p = rows[pi]; if (p.Sd == null || s.Sd == null) return;
        const [ps, pd, ss, sa] = LINK_SIDES[l.type];
        const pts = linkPts({ x: anchorX(p, ps, x, pxDay), y: yOf(pi) + rowH / 2, dir: pd }, { x: anchorX(s, ss, x, pxDay), y: yOf(si) + rowH / 2, arr: sa }, rowH);
        const crit = S.pl.crit && p.crit && s.crit; const col = crit ? 'var(--bad)' : 'var(--muted)';
        lg.append('path').attr('d', 'M' + pts.map((q) => q.join(',')).join('L')).attr('stroke', col).attr('stroke-width', crit ? 1.4 : 1).attr('stroke-opacity', crit ? 0.9 : 0.75);
        const [bx, by] = pts[pts.length - 1];
        lg.append('path').attr('d', `M${bx},${by}L${bx - sa * 5},${by - 3.5}L${bx - sa * 5},${by + 3.5}Z`).attr('fill', col);
      }));
    }
    // bars
    rows.forEach((r, i) => {
      if (r.Sd == null) return;
      const g = R.append('g').attr('transform', `translate(0,${yOf(i)})`).style('cursor', 'pointer');
      const hasBase = S.pl.base && r.bs && r.bf;
      const cy = hasBase ? rowH / 2 - 2 : rowH / 2; const color = planColor(r);
      if (hasBase) {
        const b0 = dn(r.bs), b1 = dn(r.bf);
        if (r.mile) { const c = x(b1) + pxDay / 2; g.append('path').attr('d', `M${c},${cy + 4}L${c + 4},${cy + 8}L${c},${cy + 12}L${c - 4},${cy + 8}Z`).attr('fill', 'var(--muted-bar)'); }
        else g.append('rect').attr('x', x(b0)).attr('y', cy + 7).attr('width', Math.max(2, x(b1 + 1) - x(b0))).attr('height', 4).attr('rx', 1).attr('fill', 'var(--muted-bar)');
      }
      if (r.mile) {
        const c = x(r.Fd) + pxDay / 2;
        g.append('path').attr('d', `M${c},${cy - 7}L${c + 7},${cy}L${c},${cy + 7}L${c - 7},${cy}Z`).attr('fill', r.state === 'done' ? 'var(--ok)' : r.state === 'late' ? 'var(--bad)' : 'var(--fg)').attr('stroke', S.pl.crit && r.crit ? 'var(--bad)' : 'none').attr('stroke-width', 2);
        g.append('text').attr('x', c + 11).attr('y', cy + 4).attr('font-size', 11).attr('font-family', 'var(--f-num)').attr('fill', 'var(--fg)').text(fNs(r.Fd));
      } else if (r.summary) {
        const x0 = x(r.Sd), x1 = x((S.pl.tails ? r.TFd ?? r.Fd : r.Fd) + 1);
        g.append('rect').attr('x', x0).attr('y', cy - 4).attr('width', Math.max(2, x1 - x0)).attr('height', 6).attr('fill', 'var(--fg)');
        g.append('path').attr('d', `M${x0},${cy + 2}L${x0 + 5},${cy + 2}L${x0},${cy + 7}Z M${x1},${cy + 2}L${x1 - 5},${cy + 2}L${x1},${cy + 7}Z`).attr('fill', 'var(--fg)');
        if (r.p > 0) g.append('rect').attr('x', x0).attr('y', cy - 3).attr('width', Math.max(0, (x1 - x0) * r.p)).attr('height', 4).attr('fill', 'var(--ok)');
        g.append('text').attr('x', x1 + 8).attr('y', cy + 3).attr('font-size', 10).attr('font-family', 'var(--f-num)').attr('fill', 'var(--muted)').text(fPct(r.p));
      } else {
        const x0 = x(r.Sd), x1 = Math.max(x(r.Fd + 1), x0 + 3), w = x1 - x0; const bh = 13;
        g.append('rect').attr('x', x0).attr('y', cy - bh / 2).attr('width', w).attr('height', bh).attr('rx', 3).attr('fill', color).attr('fill-opacity', 0.22).attr('stroke', S.pl.crit && r.crit ? 'var(--bad)' : color).attr('stroke-width', S.pl.crit && r.crit ? 2 : 1).attr('stroke-opacity', S.pl.crit && r.crit ? 1 : 0.6);
        if (r.p > 0) g.append('rect').attr('x', x0).attr('y', cy - bh / 2).attr('width', Math.max(2, w * r.p)).attr('height', bh).attr('rx', 3).attr('fill', color);
        let xl = x1;
        if (S.pl.tails && r.tails) r.tails.forEach((tl) => { const a = x(tl.Sd), b = Math.max(x(tl.Fd + 1), a + 3); g.append('rect').attr('x', a).attr('y', cy - 4).attr('width', b - a).attr('height', 8).attr('rx', 2).attr('fill', STAGE_CLR[tl.st]).attr('fill-opacity', tl.done >= 0.999 ? 0.95 : 0.3 + 0.6 * tl.done).append('title').text(`${tl.st}: ${fN(tl.Sd)} → ${fN(tl.Fd)}`); if (b - a > 12) g.append('text').attr('x', (a + b) / 2).attr('y', cy + 3).attr('text-anchor', 'middle').attr('font-size', 8).attr('font-weight', 600).attr('fill', 'var(--fg)').attr('pointer-events', 'none').text(tl.st[0]); xl = b; });
        const label = [r.code || '', S.pl.owners ? r.owner || '' : ''].filter(Boolean).join(' · ');
        if (label) fit(g.append('text').attr('x', xl + 6).attr('y', cy + 4).attr('font-size', 11).attr('fill', 'var(--muted)').text(label), Math.max(30, tlW - xl - 12));
      }
      g.append('rect').attr('x', 0).attr('width', tlW).attr('height', rowH).attr('fill', 'transparent').on('mousemove', showTip(r)).on('mouseleave', hideTip).on('click', () => openPlan(r.id));
    });
    if (T >= d0 && T < d1) { const tx = x(T) + pxDay / 2; R.append('line').attr('x1', tx).attr('x2', tx).attr('y1', axisH - 4).attr('y2', H).attr('stroke', 'var(--bad)').attr('stroke-width', 1.5).attr('stroke-dasharray', '4 3').style('pointer-events', 'none'); R.append('text').attr('x', tx + 4).attr('y', axisH - 4).attr('font-size', 10).attr('fill', 'var(--bad)').text('сегодня'); }
    const prev = box.querySelector('.gr') ? box.querySelector('.gr').scrollLeft : null;
    const wrap = el('div', 'gwrap'); const left = el('div', 'gl'); left.style.width = labelW + 'px'; const right = el('div', 'gr');
    left.append(L.node()); right.append(R.node()); wrap.append(left, right); box.replaceChildren(wrap, tip);
    right.addEventListener('scroll', hideTip);
    if (tlW > viewW) right.scrollLeft = prev != null && S.pl.keepScroll ? prev : Math.max(0, x(Math.max(d0, Math.min(T, d1)) - 7));
    S.pl.keepScroll = true;
  }

  // ---------- writing the plan (apps/pult/plan.py)
  function cellOut(k, v) {
    if (v == null || v === '') return null;
    if (['snet', 'as', 'af', 'cs', 'cf', 'bs', 'bf', 'closed'].includes(k)) return typeof v === 'number' ? dIso(v) : v;
    return v;
  }
  // Reads the rows fresh, applies `mutate`, recalculates the dates and sends everything back.
  // The server writes only the projects whose rows changed and refuses if someone saved in between.
  async function savePlan(mutate) {
    const fresh = await apiFetch(API.plan);
    let rows = fresh.rows.map((r) => ({ ...r }));
    const ctx = { nextId: fresh.nextId };
    rows = mutate(rows, ctx) || rows;
    new Set(rows.map((r) => r.project)).forEach((p) => { const rule = (ctx.rules && ctx.rules.get(p)) || S.d.ciph?.get(p); if (rule) assignCiphers(rows, p, false, rule); });
    const sch = schedule(planSubset(rows), S.d.cal, S.d.tasks || []);
    const out = rows.map((r) => { const x = sch.byId.get(r.id); const o = { id: r.id, project: r.project }; PF.slice(2).forEach((k) => { o[k] = cellOut(k, k === 'cs' ? x?.Sd : k === 'cf' ? x?.Fd : r[k]); }); return o; });
    await apiFetch(API.plan, { rows: out, version: fresh.version });
  }
  function nextWbs(rows, parentWbs) {
    const pw = str(parentWbs);
    const kids = rows.map((r) => str(r.wbs)).filter((w) => (pw ? w.startsWith(pw + '.') && w.split('.').length === pw.split('.').length + 1 : w && !w.includes('.')));
    const n = (d3.max(kids, (w) => Number(w.split('.').pop())) || 0) + 1;
    return pw ? pw + '.' + n : String(n);
  }

  // ---------- section modal
  function openPlan(id, preset = {}) {
    if (!isMgr()) { const r0 = (S.d.plan || []).find((x) => x.id === id); if (r0 && isSection(r0)) openSecCard(id); return; }
    if (!S.mcp) return toast('Сервер недоступен.');
    if (!S.d.sched) return toast('Состав проекта ещё загружается.');
    const raw = id != null ? (S.d.plan || []).find((x) => x.id === id) : null;
    if (id != null && !raw) return toast('Раздел не найден, обновите страницу.');
    const r = raw ? (S.d.sched.byId.get(id) || { ...raw, out: true, errs: [], links: parsePreds(raw.preds).links, mile: raw.kind === 'Веха', d: raw.dur, p: raw.pct || 0, pSrc: 'manual', tasks: (S.d.tasks || []).filter((t) => t.section === raw.id), summary: (S.d.plan || []).some((x) => x.project === raw.project && str(raw.wbs) && str(x.wbs).startsWith(str(raw.wbs) + '.')) }) : null;
    const proj = r?.project || preset.project || S.pl.project; if (!proj) return toast('Выберите проект.');
    const same = (S.d.plan || []).filter((x) => x.project === proj);
    modal(r ? `${r.summary ? 'Этап' : r.mile ? 'Веха' : 'Раздел'} ${r.code || ''} · ID ${r.id}`.replace(/\s+/g, ' ') : `Новый раздел · ${proj}`, (m, close) => {
      const form = el('div', 'form');
      const fName = input('pm-name', 'text', r?.name || preset.name || '', { placeholder: 'Например: Архитектурные решения', autocomplete: 'off' });
      const fCode = input('pm-code', 'text', r?.code || '', { placeholder: 'АР', autocomplete: 'off' });
      const fWbs = input('pm-wbs', 'text', r?.wbs || nextWbs(same, preset.parentWbs), { placeholder: '3.2', autocomplete: 'off' });
      const fDoc = input('pm-doc', 'text', r?.doc || '', { placeholder: 'присвоится по правилам проекта', autocomplete: 'off' }); fDoc.classList.add('mono');
      const kind0 = r ? (r.kind === 'Объект' ? 'Объект' : r.summary ? 'Этап' : r.mile ? 'Веха' : (r.kind || 'Раздел')) : (preset.kind || 'Раздел');
      const fKind = select('pm-kind', ['Раздел', 'Этап', 'Веха', 'Объект'], kind0);
      const fIn = select('pm-in', [new Option('Да', 'Да'), new Option('Нет, только в составе', 'Нет')], r?.inPlan === 'Нет' ? 'Нет' : 'Да');
      const fOwner = input('pm-owner', 'text', r?.owner || '', { list: 'pm-people', autocomplete: 'off', placeholder: 'кто делает раздел' });
      const dl = el('datalist'); dl.id = 'pm-people'; (S.d.people || []).filter((p) => !/^(Заказчик|Партнёр)$/.test(p.role || '')).forEach((p) => dl.append(new Option(p.name)));
      const fDur = input('pm-dur', 'number', r ? (r.summary ? '' : (r.mile ? 0 : (r.dur ?? r.d))) : 10, { min: 0, step: 1 });
      const fPreds = input('pm-preds', 'text', r?.preds || preset.preds || '', { placeholder: 'например: 3; 5НН+5', autocomplete: 'off' });
      const fSnet = input('pm-snet', 'date', r?.snet || preset.snet || '');
      const fAs = input('pm-as', 'date', r?.as || ''); const fAf = input('pm-af', 'date', r?.af || '');
      const fPctIn = input('pm-pct', 'number', isNum(r?.pct) ? Math.round(r.pct * 100) : '', { min: 0, max: 100, step: 5, placeholder: '0' });
      const fClient = select('pm-client', [new Option('Да, показывать', 'Да'), new Option('Нет, только для нас', 'Нет')], r?.client === 'Нет' ? 'Нет' : 'Да');
      const fComment = el('textarea', 'ctl'); fComment.id = 'pm-comment'; fComment.value = r?.comment || '';
      const fPay = select('pm-pay', [new Option('авто — по типу оплаты исполнителя', ''), new Option('по договору', 'Договор'), new Option('в окладе (отдельно не платим)', 'Оклад')], r?.pay || '');
      const fPrice = input('pm-price', 'number', isNum(r?.price) ? r.price : '', { min: 0, step: 50, placeholder: 'для договора' });
      const fCur = select('pm-cur', ['USD', 'сум'], r?.cur === 'сум' ? 'сум' : 'USD');
      const fCon = select('pm-con', [new Option('автоматически (договор «Состав проекта»)', '')], '');
      const payNote = el('p', 'note full');
      const fillCon = () => {
        const nm = conNameOf(S.d.people || [], fOwner.value.trim()); const cur = fCon.value || r?.contract || '';
        const list = (S.d.contracts || []).filter((c) => c.project === proj && c.side === 'Исполнитель' && (str(c.name) === nm || c.id === cur));
        fCon.replaceChildren(new Option('автоматически (договор «Состав проекта»)', ''), ...list.map((c) => new Option(`${c.id} · ${c.name} · ${c.section || ''} · ${fMoney(c.amount, curOf(c))}${c.src === AUTO_SRC ? ' · из состава' : ''}${c.status === 'Закрыт' ? ' · закрыт' : ''}`, c.id)));
        fCon.value = list.some((c) => c.id === cur) ? cur : '';
        const auto = payOf({ owner: fOwner.value.trim(), pay: fPay.value }, S.d.people || []);
        payNote.textContent = !fOwner.value.trim() ? 'Без исполнителя задача и договор не создаются.' : auto === 'Оклад' ? 'Раздел в окладе: задача ставится, договор не создаётся, в финансах не считается.' : 'Раздел по договору: задача ставится, стоимость входит в договор с исполнителем и в долг исполнителям в финансах.';
      };
      fOwner.addEventListener('input', fillCon); fPay.addEventListener('change', fillCon);
      const lDur = field('Длительность, раб. дн.', fDur); const lPct = field('Выполнено, % (если нет задач)', fPctIn);
      form.append(field('Наименование', fName, 'full'), field('Шифр документа (оставьте пустым — присвоится сам)', fDoc, 'full'), field('Дисциплина (АР, КЖ…)', fCode), field('WBS (номер в структуре)', fWbs), field('Тип', fKind), lDur, field('Исполнитель', fOwner), field('Показывать заказчику', fClient), field('В графике', fIn));
      // links
      const lk = el('div', 'full pl-links'); lk.append(field('Связи (предшественники)', fPreds));
      const pk = el('div', 'picker');
      const others = same.filter((x) => x.id !== r?.id);
      const pSel = select('pm-psel', [new Option('— выберите раздел —', ''), ...others.map((x) => new Option(`${x.id} · ${x.wbs || ''} ${x.code ? x.code + ' ' : ''}${x.name || ''}`.replace(/\s+/g, ' '), x.id))]);
      const pType = select('pm-ptype', Object.entries(LT_NAME).map(([k, v]) => new Option(`${k}: ${v}`, k)), 'ОН');
      const pLag = input('pm-plag', 'number', '0', { step: 1 });
      const pAdd = el('button', 'btn', 'Добавить связь'); pAdd.type = 'button';
      pAdd.addEventListener('click', () => { if (!pSel.value) { err.textContent = 'Выберите раздел, от которого зависит этот.'; return; } const s = fmtLink({ id: Number(pSel.value), type: pType.value, lag: Number(pLag.value) || 0 }); fPreds.value = [fPreds.value.trim().replace(/;$/, ''), s].filter(Boolean).join('; '); pSel.value = ''; pLag.value = '0'; err.textContent = ''; });
      pk.append(field('Зависит от', pSel), field('Тип связи', pType), field('Лаг, дн.', pLag), pAdd);
      lk.append(pk, el('p', 'note', 'ОН — начать после окончания; НН — начать после начала (параллельно со сдвигом); ОО — закончить не раньше окончания; НО — закончить не раньше начала. Лаг в рабочих днях, можно с минусом: «5ОН-3» значит начать за 3 дня до окончания раздела 5.'));
      form.append(lk);
      form.append(field('Оплата раздела', fPay), field('Стоимость', fPrice), field('Валюта', fCur), field('Договор', fCon), payNote);
      fillCon();
      form.append(field('Начать не раньше', fSnet), field('Факт. начало', fAs), field('Факт. окончание', fAf), lPct, field('Комментарий', fComment, 'full'), dl);
      const kindNote = el('p', 'note full'); form.append(kindNote);
      const syncKind = () => {
        const k = fKind.value === 'Объект' ? 'Этап' : fKind.value; fDur.disabled = k !== 'Раздел'; if (k === 'Веха') fDur.value = 0; if (k === 'Раздел' && (fDur.value === '' || fDur.value === '0')) fDur.value = 10;
        lPct.hidden = k === 'Этап' || (r && r.pSrc === 'tasks');
        kindNote.textContent = fKind.value === 'Объект' ? 'Объект — здание или сооружение. Его разделы имеют WBS вида 2.1, 2.2; сроки объекта считаются по ним.' : k === 'Этап' ? 'Сроки и процент этапа считаются по вложенным разделам: у этапа с WBS 3 вложенные — 3.1, 3.2… Связи этапа действуют на все его разделы.' : k === 'Веха' ? 'Веха — контрольная точка без длительности: выдача тома, экспертиза, подписание акта.' : r && r.pSrc === 'tasks' ? `Процент считается по ${r.tasks.length} ${plural(r.tasks.length, 'задаче', 'задачам', 'задачам')} сотрудников, привязанным к разделу.` : 'Процент можно вписать вручную или привязать к разделу задачи сотрудников: тогда он посчитается сам.';
      };
      fKind.addEventListener('change', syncKind); syncKind();
      m.append(form);
      if (r) {
        const info = el('div', 'confirm');
        if (r.out) info.append(el('div', null, 'Этот раздел пока только в составе проекта. Поставьте «В графике: Да» или перенесите состав кнопкой на вкладке «Состав проекта».'));
        else info.append(el('div', null, r.mile ? `Расчётная дата: ${fN(r.Fd)}` : `Расчёт: ${fN(r.Sd)} → ${fN(r.Fd)}, ${fNum(r.wdays)} раб. дн. · выполнено ${fPct(r.p)} · ${stateText[r.state] || ''}`));
        if (!r.summary && isNum(r.slack) && r.p < 0.999) info.append(el('div', null, r.slack > 0 ? `Резерв: ${r.slack} раб. дн. до сдвига окончания проекта.` : 'Критический путь: любая задержка сдвинет окончание проекта.'));
        if (r.bs || r.bf) info.append(el('div', null, `Базовый план: ${fD(r.bs)} → ${fD(r.bf)}` + (isNum(r.varD) && r.varD ? `, отклонение ${r.varD > 0 ? '+' : ''}${r.varD} раб. дн.` : '')));
        if (r.errs.length) { const e = el('div', null, 'Ошибки: ' + r.errs.join('; ')); e.style.color = 'var(--bad)'; info.append(e); }
        const lt = isNum(r.task) ? (S.d.tasks || []).find((t) => t.id === r.task) : null; const lc = r.contract ? (S.d.contracts || []).find((c) => c.id === r.contract) : null;
        if (lt) info.append(el('div', null, `Задача №${lt.id}: ${lt.assignee || '—'} · ${lt.status || '—'} · ${fPct(lt.done)}`));
        if (lc) info.append(el('div', null, `Договор ${lc.id}: ${fMoney(lc.amount, curOf(lc))}, оплачено ${fMoney(lc.paid || 0, curOf(lc))}, остаток ${fMoney(lc.rest || 0, curOf(lc))} · ${lc.status || ''}`));
        m.append(info);
        if (!r.summary && !r.mile) {
          const tl = el('div', 'pl-tasks'); tl.append(el('div', 'note', r.tasks.length ? 'Задачи по разделу:' : 'Задач по разделу пока нет.'));
          r.tasks.forEach((t) => { const b = el('button', 'linkbtn', `№${t.id} ${t.task || ''} · ${t.assignee || ''} · ${t.status || ''} · ${fPct(t.done)}`); b.type = 'button'; b.addEventListener('click', () => { close(); openTask(t.id); }); tl.append(b); });
          const add = el('button', 'btn sm', '+ задача по разделу'); add.type = 'button';
          add.addEventListener('click', () => { close(); openTask(null, { project: proj, section: r.id, assignee: personBy(r.owner) ? r.owner : '', task: `${r.code ? r.code + ' — ' : ''}${r.name || ''}` }); });
          tl.append(add); m.append(tl);
        }
      }
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); foot.append(err);
      let delArmed = false;
      if (r) {
        const del = el('button', 'btn ghost', 'Удалить'); del.type = 'button'; del.style.color = 'var(--bad)';
        const sub = r.summary ? same.filter((x) => str(x.wbs).startsWith(str(r.wbs) + '.')).length : 0;
        del.addEventListener('click', async () => {
          if (!delArmed) { delArmed = true; del.textContent = sub ? `Удалить вместе с ${sub} вложенными?` : 'Точно удалить?'; return; }
          del.disabled = true; del.textContent = 'Удаляю…';
          try {
            await savePlan((rows) => {
              const w = str(r.wbs); const kill = new Set(rows.filter((x) => x.project === proj && (x.id === r.id || (w && str(x.wbs).startsWith(w + '.')))).map((x) => x.id));
              const keep = rows.filter((x) => !kill.has(x.id));
              keep.forEach((x) => { if (!x.preds) return; const p = parsePreds(x.preds); if (p.links.some((l) => kill.has(l.id))) x.preds = [...p.links.filter((l) => !kill.has(l.id)).map(fmtLink), ...p.bad].join('; '); });
              return keep;
            });
            toast('Удалено, сроки пересчитаны'); close(); refreshAll();
          } catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); del.disabled = false; del.textContent = 'Удалить'; delArmed = false; }
        });
        foot.append(del);
        const sib = el('button', 'btn', '+ вложенный'); sib.type = 'button'; sib.title = 'Добавить раздел внутрь этого (сделает его этапом)';
        sib.addEventListener('click', () => { close(); openPlan(null, { project: proj, parentWbs: r.wbs, preds: '' }); });
        foot.append(sib);
      }
      const cancel = el('button', 'btn ghost', 'Отмена'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const save = el('button', 'btn primary', r ? 'Сохранить и пересчитать' : 'Добавить'); save.type = 'button';
      foot.append(cancel, save); m.append(foot);
      const collect = () => {
        const v = { pay: fPay.value, price: fPrice.value === '' ? null : Math.max(0, Number(fPrice.value)), cur: fCur.value, contract: fCon.value, doc: fDoc.value.trim().toUpperCase(), name: fName.value.trim(), code: fCode.value.trim(), wbs: fWbs.value.trim().replace(/\.$/, ''), kind: fKind.value, owner: fOwner.value.trim(), inPlan: fIn.value, dur: fKind.value === 'Этап' || fKind.value === 'Объект' ? null : fKind.value === 'Веха' ? 0 : (fDur.value === '' ? null : Number(fDur.value)), preds: fPreds.value.trim().replace(/;\s*$/, ''), snet: fSnet.value || null, as: fAs.value || null, af: fAf.value || null, pct: fPctIn.value === '' ? null : Math.max(0, Math.min(100, Number(fPctIn.value))) / 100, client: fClient.value, comment: fComment.value.trim() };
        if (!v.name) return 'Напишите наименование.';
        if (!/^\d+(\.\d+)*$/.test(v.wbs)) return 'WBS — номер вида 3 или 3.2 (этап 3, раздел 2 в нём).';
        if (same.some((x) => x.id !== r?.id && str(x.wbs) === v.wbs)) return `WBS ${v.wbs} уже занят в этом проекте.`;
        if (v.kind === 'Раздел' && !(v.dur >= 1)) return 'Длительность раздела — от 1 рабочего дня.';
        const p = parsePreds(v.preds); if (p.bad.length) return 'Не понял связь: ' + p.bad.join(', ') + '. Пример: 3; 5НН+5; 7ОО';
        const ids = new Set(same.map((x) => x.id)); const miss = p.links.filter((l) => !ids.has(l.id) && !S.d.sched.byId.has(l.id)); if (miss.length) return 'Нет разделов с ID: ' + miss.map((l) => l.id).join(', ');
        if (r && p.links.some((l) => l.id === r.id)) return 'Раздел не может зависеть сам от себя.';
        if (v.af && v.as && v.af < v.as) return 'Факт. окончание раньше факт. начала.';
        v.preds = p.links.map(fmtLink).join('; ');
        return v;
      };
      save.addEventListener('click', async () => {
        const v = collect(); if (typeof v === 'string') { err.textContent = v; return; }
        err.textContent = ''; save.disabled = true; save.textContent = 'Пересчитываю…';
        try {
          await savePlan((rows, ctx) => {
            let o = r ? rows.find((x) => x.id === r.id) : null;
            if (r && !o) throw userErr('Этот раздел уже удалён. Обновите страницу.');
            if (rows.some((x) => x.project === proj && x !== o && str(x.wbs) === v.wbs)) throw userErr(`WBS ${v.wbs} уже занят в этом проекте.`);
            if (!o) { o = { id: ctx.nextId++, project: proj, inPlan: 'Да' }; rows.push(o); }
            Object.assign(o, v); return rows;
          });
          toast(r ? 'Сохранено, сроки пересчитаны' : 'Раздел добавлен'); S.pl.project = proj; close(); refreshAll();
        } catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); save.disabled = false; save.textContent = r ? 'Сохранить и пересчитать' : 'Добавить'; }
      });
    });
  }

  // ---------- typical composition template (key, WBS, шифр, наименование, тип, дней, связи по ключам)
  const TEMPLATE = [
    ['s', '1', '', 'Старт проекта (договор, аванс)', 'Веха', 0, ''],
    ['e1', '2', '', 'Исходные данные и изыскания', 'Этап', null, ''],
    ['ид', '2.1', 'ИД', 'Сбор исходных данных, техническое задание', 'Раздел', 10, 's'],
    ['ии', '2.2', 'ИИ', 'Инженерные изыскания (геодезия, геология)', 'Раздел', 20, 'ид НН+5'],
    ['e2', '3', '', 'Основные проектные решения', 'Этап', null, ''],
    ['тх', '3.1', 'ТХ', 'Технологические решения', 'Раздел', 25, 'ид'],
    ['гп', '3.2', 'ГП', 'Генеральный план', 'Раздел', 15, 'ии ОН-5; тх НН+5'],
    ['ар', '3.3', 'АР', 'Архитектурные решения', 'Раздел', 25, 'тх НН+10'],
    ['кж', '3.4', 'КЖ', 'Конструкции железобетонные', 'Раздел', 30, 'ар НН+10; ии'],
    ['км', '3.5', 'КМ', 'Конструкции металлические', 'Раздел', 25, 'ар НН+10'],
    ['e3', '4', '', 'Инженерные системы', 'Этап', null, ''],
    ['эс', '4.1', 'ЭС', 'Электроснабжение и силовое электрооборудование', 'Раздел', 25, 'тх НН+10'],
    ['эо', '4.2', 'ЭО', 'Электроосвещение', 'Раздел', 15, 'ар НН+10'],
    ['ов', '4.3', 'ОВ', 'Отопление, вентиляция и кондиционирование', 'Раздел', 20, 'ар НН+10; тх НН+10'],
    ['вк', '4.4', 'ВК', 'Водоснабжение и канализация', 'Раздел', 20, 'ар НН+10'],
    ['атх', '4.5', 'АТХ', 'Автоматизация технологических процессов', 'Раздел', 25, 'тх ОН-10; эс НН+5'],
    ['сс', '4.6', 'СС', 'Сети связи', 'Раздел', 15, 'ар НН+10'],
    ['e4', '5', '', 'Сводные разделы и выдача', 'Этап', null, ''],
    ['пос', '5.1', 'ПОС', 'Проект организации строительства', 'Раздел', 15, 'гп; кж ОН-10'],
    ['оос', '5.2', 'ООС', 'Охрана окружающей среды, пожарная безопасность', 'Раздел', 15, 'тх; гп'],
    ['сд', '5.3', 'СД', 'Сметная документация', 'Раздел', 20, 'кж ОН-10; км ОН-10; эс ОН-10; ов ОН-10; вк ОН-10; атх ОН-10'],
    ['вд', '5.4', '', 'Выдача проекта заказчику', 'Веха', 0, 'сд; пос; оос; эо; сс'],
    ['эк', '5.5', 'ЭК', 'Экспертиза и снятие замечаний', 'Раздел', 30, 'вд'],
    ['ут', '5.6', '', 'Проект утверждён', 'Веха', 0, 'эк'],
  ];
  // The template uses Russian codes (АР, КЖ…); the platform's disciplines may be in Latin (AR, KR…).
  // Use the platform's code when it has the same discipline, so the matrix and ciphers don't split in two.
  const CODE_ALIASES = { 'АР': ['AR'], 'КЖ': ['KJ', 'KZH', 'KR'], 'КР': ['KR'], 'КМ': ['KM'], 'ЭС': ['ES', 'EL'], 'ЭО': ['EO'], 'ОВ': ['OV', 'HVAC'], 'ВК': ['VK'], 'ТХ': ['TX', 'TH'], 'ГП': ['GP'], 'АТХ': ['ATX', 'ATH'], 'СС': ['SS'], 'ПОС': ['POS'], 'ООС': ['OOS'], 'СД': ['SD'], 'ИД': ['ID'], 'ИИ': ['II'], 'ЭК': ['EK'] };
  function platformCode(code) {
    if (!code) return code;
    const have = new Set((S.d.disc || []).map((d) => d.code));
    if (have.has(code)) return code;
    return (CODE_ALIASES[code] || []).find((c) => have.has(c)) || code;
  }
  function openTemplate(proj) {
    if (!S.mcp) return toast('Сервер недоступен.');
    if (!proj) return toast('Выберите проект.');
    modal(`Типовой состав · ${proj}`, (m, close) => {
      const T0 = S.d.cal.next(todayN());
      const fStart = input('tp-start', 'date', dIso(T0));
      const form = el('div', 'form'); form.append(field('Дата начала проекта', fStart), el('p', 'note', 'Отметьте разделы, которые есть в этом проекте. Длительности и связи типовые — после создания поправьте их под объект.'));
      const list = el('div', 'tp-list full'); const boxes = new Map();
      TEMPLATE.forEach(([key, wbs, code, name, kind, dur, preds]) => {
        const l = el('label', 'tp-item' + (kind === 'Этап' ? ' tp-phase' : '')); l.style.paddingLeft = (wbs.split('.').length - 1) * 18 + 'px';
        const c = el('input'); c.type = 'checkbox'; c.checked = true; c.id = 'tp-' + key; boxes.set(key, c);
        const txt = `${code ? code + ' — ' : ''}${name}` + (kind === 'Раздел' ? ` · ${dur} дн.` : kind === 'Веха' ? ' · веха' : '');
        l.append(c, el('span', null, txt));
        if (preds) l.append(el('span', 'note mono', ' после: ' + preds.split(';').map((s) => { const [k, rest = ''] = s.trim().split(/\s+/); const t = TEMPLATE.find((x) => x[0] === k); return (t && (t[2] || t[3].split(' ')[0])) + rest; }).join(', ')));
        if (kind === 'Этап') c.addEventListener('change', () => TEMPLATE.filter((t) => t[1].startsWith(wbs + '.')).forEach((t) => { boxes.get(t[0]).checked = c.checked; }));
        list.append(l);
      });
      form.append(list); m.append(form);
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); const cancel = el('button', 'btn ghost', 'Отмена'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const go = el('button', 'btn primary', 'Создать состав'); go.type = 'button'; foot.append(err, cancel, go); m.append(foot);
      go.addEventListener('click', async () => {
        const start = fStart.value; if (!start) { err.textContent = 'Укажите дату начала.'; return; }
        const chosen = TEMPLATE.filter((t) => boxes.get(t[0]).checked);
        // a phase stays only if some of its sections stay
        const keep = chosen.filter((t) => t[4] !== 'Этап' || chosen.some((c) => c[1].startsWith(t[1] + '.')));
        if (!keep.length) { err.textContent = 'Отметьте хотя бы один раздел.'; return; }
        go.disabled = true; go.textContent = 'Создаю…';
        try {
          await savePlan((rows, ctx) => {
            const off = d3.max(rows.filter((x) => x.project === proj), (x) => Number(str(x.wbs).split('.')[0]) || 0) || 0;
            const tops = [...new Set(keep.map((t) => t[1].split('.')[0]))]; const topMap = new Map(tops.map((t, i) => [t, String(off + i + 1)]));
            const subMap = new Map(); // renumber sections inside each phase without gaps
            const idOf = new Map(keep.map((t) => [t[0], ctx.nextId++]));
            const hasStart = idOf.has('s');
            keep.forEach(([key, wbs, code, name, kind, dur, preds]) => {
              const segs = wbs.split('.'); let w = topMap.get(segs[0]);
              if (segs.length > 1) { const n = (subMap.get(w) || 0) + 1; subMap.set(w, n); w = w + '.' + n; }
              const links = preds ? preds.split(';').map((s) => s.trim()).filter(Boolean).map((tok) => { const [k, rest = ''] = tok.split(/\s+/); return idOf.has(k) ? idOf.get(k) + rest : null; }).filter(Boolean).join('; ') : '';
              rows.push({ id: idOf.get(key), project: proj, wbs: w, code: platformCode(code), name, kind, owner: '', dur: kind === 'Этап' ? null : dur, preds: links, snet: key === 's' || (!hasStart && !links && kind !== 'Этап') ? start : null, client: 'Да', pct: null, comment: '', inPlan: 'Да' });
            });
            return rows;
          });
          toast('Типовой состав создан, сроки рассчитаны'); S.pl.project = proj; close(); refreshAll();
        } catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); go.disabled = false; go.textContent = 'Создать состав'; }
      });
    });
  }

  // ---------- baseline
  let baseArmed = null;
  async function saveBaseline(btn) {
    const proj = S.pl.project; if (!proj) return;
    if (!baseArmed) { baseArmed = setTimeout(() => { baseArmed = null; btn.textContent = 'Сохранить базовый план'; }, 5000); btn.textContent = 'Перезаписать базовый план? Нажмите ещё раз'; return; }
    clearTimeout(baseArmed); baseArmed = null; btn.disabled = true; btn.textContent = 'Сохраняю…';
    try {
      const cur = new Map(S.d.sched.rows.filter((r) => r.project === proj).map((r) => [r.id, r]));
      await savePlan((rows) => { rows.forEach((x) => { const c = cur.get(x.id); if (x.project === proj && c && c.Sd != null) { x.bs = dIso(c.Sd); x.bf = dIso(c.Fd); } }); return rows; });
      toast('Базовый план сохранён: с ним будут сравниваться сроки'); refreshAll();
    } catch (e) { toast(e && e.userText ? e.userText : errText(e)); }
    finally { btn.disabled = false; btn.textContent = 'Сохранить базовый план'; }
  }

  // ---------- exports for the client (Excel and PDF)
  const libs = {};
  const loadScript = (src, glob) => {
    if (window[glob]) return Promise.resolve(window[glob]);
    if (!libs[src]) libs[src] = new Promise((res, rej) => { const s = document.createElement('script'); s.src = src; s.onload = () => (window[glob] ? res(window[glob]) : rej(new Error('библиотека не загрузилась'))); s.onerror = () => { libs[src] = null; rej(new Error('библиотека не загрузилась, проверьте интернет')); }; document.head.append(s); });
    return libs[src];
  };
  function exportData(proj) {
    const all = S.d.sched.rows.filter((r) => r.project === proj && r.Sd != null);
    const vis = new Set(all.filter((r) => !r.summary && r.client !== 'Нет').map((r) => r.id));
    all.filter((r) => r.summary && r.client !== 'Нет').sort((a, b) => b.level - a.level).forEach((s) => { if (s.kids.some((k) => vis.has(k.id))) vis.add(s.id); });
    const rows = all.filter((r) => vis.has(r.id));
    const P = (S.d.projects || []).find((p) => p.name === proj) || {};
    return { rows, st: projStats(all), title: P.full || proj, client: P.client || '', proj };
  }
  async function saveFile(filename, data) {
    if (!S.dl) { toast('Скачивание файлов недоступно в этом окне.'); return; }
    try { await S.dl.save({ filename, data }); toast('Файл готов: ' + filename); }
    catch (e) { if (e && e.code === 'declined') return; if (e && e.code === 'rate_limited') { toast('Подождите: окно сохранения уже открыто.'); return; } toast('Не удалось сохранить файл: ' + ((e && (e.message || e.code)) || 'ошибка')); }
  }
  const fileStamp = () => { const d = today(); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); };
  const safeName = (s) => String(s).replace(/[\\/:*?"<>|]+/g, ' ').trim();

  async function exportXlsx(btn) {
    const proj = S.pl.project; const E = exportData(proj); if (!E.rows.length) return toast('Нечего выгружать.');
    btn.disabled = true; const t0 = btn.textContent; btn.textContent = 'Готовлю…';
    try {
      const X = await loadScript('https://cdnjs.cloudflare.com/ajax/libs/exceljs/4.4.0/exceljs.min.js', 'ExcelJS');
      const cal = S.d.cal; const T = todayN(); const own = S.pl.owners; const TC = own ? 8 : 7;
      const d0 = d3.min(E.rows, (r) => r.Sd), d1 = d3.max(E.rows, (r) => (S.pl.tails ? r.TFd ?? r.Fd : r.Fd)) + 1;
      const TAILC = { 'Смета': 'FFD9CCF5', 'Оформление': 'FFC8EDEA', 'Печать': 'FFFBDCC4' };
      const span = d1 - d0; const mode = span <= 70 ? 'day' : span <= 600 ? 'week' : 'month';
      const units = [];
      if (mode === 'day') for (let n = d0; n < d1; n++) units.push({ s: n, e: n + 1 });
      else if (mode === 'week') { let n = d0 - ((wdOf(d0) + 6) % 7); for (; n < d1; n += 7) units.push({ s: n, e: n + 7 }); }
      else { let d = new Date(d0 * DAY); d = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1) / DAY; while (d < d1) { const dt = new Date(d * DAY); const nx = Date.UTC(dt.getUTCFullYear(), dt.getUTCMonth() + 1, 1) / DAY; units.push({ s: d, e: nx }); d = nx; } }
      const wb = new X.Workbook(); wb.creator = 'GASTEC PROJECT'; wb.created = new Date();
      const ws = wb.addWorksheet('Календарный график', { views: [{ state: 'frozen', xSplit: TC, ySplit: 7, showGridLines: false }] });
      ws.pageSetup = { paperSize: 8, orientation: 'landscape', fitToPage: true, fitToWidth: 1, fitToHeight: 0, printTitlesRow: '6:7', margins: { left: 0.3, right: 0.3, top: 0.4, bottom: 0.4, header: 0.2, footer: 0.2 } };
      ws.headerFooter = { oddFooter: '&L&8ООО «GASTEC PROJECT» · Календарный график · ' + proj.replace(/&/g, '&&') + '&R&8Лист &P из &N' };
      const NC = TC + units.length; const uw = mode === 'day' ? 3.4 : mode === 'week' ? 5.2 : 7;
      ws.columns = [{ width: 7 }, { width: 8 }, { width: own ? 40 : 46 }, ...(own ? [{ width: 20 }] : []), { width: 9 }, { width: 11.5 }, { width: 11.5 }, { width: 8 }, ...units.map(() => ({ width: uw }))];
      const C = { ink: 'FF4F7FE0', inkD: 'FF1D4FD8', ok: 'FF1D8A52', fg: 'FF17202C', line: 'FFCCD2DC', head: 'FFDBE5FB', shade: 'FFF0F2F5', bad: 'FFC8322B', faint: 'FF8A94A3' };
      const thin = { style: 'thin', color: { argb: C.line } }; const box = { top: thin, left: thin, bottom: thin, right: thin };
      const fill = (argb) => ({ type: 'pattern', pattern: 'solid', fgColor: { argb } });
      const F = (o = {}) => ({ name: 'Arial', size: 9, ...o });
      ws.mergeCells(1, 1, 1, NC); Object.assign(ws.getCell(1, 1), { value: 'КАЛЕНДАРНЫЙ ГРАФИК ВЫПОЛНЕНИЯ ПРОЕКТНЫХ РАБОТ', font: F({ size: 14, bold: true }), alignment: { horizontal: 'left', vertical: 'middle' } }); ws.getRow(1).height = 24;
      const meta = [`Объект: ${E.title}`, `Заказчик: ${E.client || '—'}     Исполнитель: ООО «GASTEC PROJECT»`, `Начало: ${fN(E.st.s)}     Окончание: ${fN(E.st.f)}     Продолжительность: ${E.st.days} раб. дн.     Выполнено на ${fD(iso(today()))}: ${fPct(E.st.p)}`];
      meta.forEach((t, i) => { ws.mergeCells(2 + i, 1, 2 + i, NC); Object.assign(ws.getCell(2 + i, 1), { value: t, font: F({ size: 10 }) }); });
      const hdr = ['№', 'Шифр', 'Наименование работ', ...(own ? ['Исполнитель'] : []), 'Дл., раб. дн.', 'Начало', 'Окончание', 'Вып., %'];
      hdr.forEach((h, i) => { ws.mergeCells(6, i + 1, 7, i + 1); Object.assign(ws.getCell(6, i + 1), { value: h, font: F({ bold: true }), alignment: { horizontal: 'center', vertical: 'middle', wrapText: true }, fill: fill(C.head), border: box }); });
      // timeline header: top tier groups, bottom tier unit labels
      const top = []; units.forEach((u, i) => { const d = new Date(u.s * DAY); const key = mode === 'month' ? d.getUTCFullYear() : d.getUTCFullYear() + '-' + d.getUTCMonth(); const lab = mode === 'month' ? String(d.getUTCFullYear()) : MONTHS[d.getUTCMonth()] + ' ' + d.getUTCFullYear(); if (!top.length || top[top.length - 1].key !== key) top.push({ key, lab, a: i, b: i }); else top[top.length - 1].b = i; });
      top.forEach((g) => { if (g.b > g.a) ws.mergeCells(6, TC + 1 + g.a, 6, TC + 1 + g.b); Object.assign(ws.getCell(6, TC + 1 + g.a), { value: g.lab, font: F({ bold: true }), alignment: { horizontal: 'center', vertical: 'middle' }, fill: fill(C.head), border: box }); });
      units.forEach((u, i) => { const d = new Date(u.s * DAY); const c = ws.getCell(7, TC + 1 + i); c.value = mode === 'day' ? d.getUTCDate() : mode === 'week' ? pad(d.getUTCDate()) + '.' + pad(d.getUTCMonth() + 1) : MONTHS[d.getUTCMonth()].slice(0, 3); c.font = F({ size: 7, color: { argb: mode === 'day' && !cal.isWork(u.s) ? C.faint : C.fg } }); c.alignment = { horizontal: 'center', vertical: 'middle', textRotation: mode === 'week' ? 90 : 0 }; c.fill = fill(T >= u.s && T < u.e ? 'FFF9DEDC' : C.head); c.border = box; });
      ws.getRow(6).height = 16; ws.getRow(7).height = mode === 'week' ? 34 : 16;
      E.rows.forEach((r, i) => {
        const rn = 8 + i; const row = ws.getRow(rn); row.height = 16;
        const vals = [r.wbs || '', r.code || '', '   '.repeat(Math.min(r.level, 5)) + (r.name || ''), ...(own ? [r.owner || ''] : []), r.mile ? 0 : r.wdays, new Date(r.Sd * DAY), new Date(r.Fd * DAY), r.mile ? null : r.p];
        vals.forEach((v, ci) => { const c = row.getCell(ci + 1); c.value = v; c.font = F({ bold: r.summary }); c.border = box; c.alignment = { vertical: 'middle', horizontal: ci === 2 || (own && ci === 3) ? 'left' : 'center', wrapText: false }; const off = own ? 1 : 0; if (ci === 4 + off || ci === 5 + off) c.numFmt = 'dd.mm.yyyy'; if (ci === 6 + off) c.numFmt = '0%'; if (r.summary) c.fill = fill(C.shade); });
        const a = r.Sd, b = r.Fd + 1; const doneUntil = a + (b - a) * (r.p || 0);
        units.forEach((u, k) => {
          const c = row.getCell(TC + 1 + k); c.border = { left: { style: 'hair', color: { argb: C.line } }, right: { style: 'hair', color: { argb: C.line } }, bottom: thin, top: thin };
          if (r.mile) { if (r.Fd >= u.s && r.Fd < u.e) { c.value = '◆'; c.font = F({ size: 10, bold: true, color: { argb: r.state === 'done' ? C.ok : C.fg } }); c.alignment = { horizontal: 'center', vertical: 'middle' }; } return; }
          const over = a < u.e && b > u.s;
          const tl = S.pl.tails && !over && r.tails ? r.tails.find((x) => x.Sd < u.e && x.Fd + 1 > u.s) : null;
          if (tl) c.fill = fill(TAILC[tl.st]);
          if (over) c.fill = fill(r.summary ? C.fg : (u.e <= doneUntil + 0.001 ? (r.state === 'done' ? C.ok : C.inkD) : C.ink));
          else if (mode === 'day' && !cal.isWork(u.s)) c.fill = fill(C.shade);
          if (T >= u.s && T < u.e && !over) c.border = { ...c.border, left: { style: 'thin', color: { argb: C.bad } }, right: { style: 'thin', color: { argb: C.bad } } };
        });
      });
      let rn = 8 + E.rows.length + 1;
      ws.mergeCells(rn, 1, rn, NC); Object.assign(ws.getCell(rn, 1), { value: `Сроки в рабочих днях (${cal.week}-дневная неделя, с учётом праздников). Тёмная часть полосы — выполненный объём, ◆ — контрольная точка${S.pl.tails ? '; после полосы — смета (сиреневый), оформление (бирюзовый), печать (оранжевый)' : ''}${mode === 'week' ? ', колонка — неделя с понедельника' : ''}.`, font: F({ size: 8, italic: true, color: { argb: 'FF5D6878' } }) });
      rn += 2; ws.getCell(rn, 3).value = 'Главный инженер проекта  ____________________'; ws.getCell(rn, 3).font = F({ size: 10 });
      ws.mergeCells(rn, TC + 1, rn, Math.max(TC + 1, NC)); ws.getCell(rn, TC + 1).value = 'Согласовано: Заказчик  ____________________'; ws.getCell(rn, TC + 1).font = F({ size: 10 });
      const buf = await wb.xlsx.writeBuffer();
      await saveFile(`Календарный график ${safeName(proj)} ${fileStamp()}.xlsx`, new Blob([buf]));
    } catch (e) { toast('Excel не собрался: ' + (e.message || e)); }
    finally { btn.disabled = false; btn.textContent = t0; }
  }

  async function exportPdf(btn) {
    const proj = S.pl.project; const E = exportData(proj); if (!E.rows.length) return toast('Нечего выгружать.');
    btn.disabled = true; const t0 = btn.textContent; btn.textContent = 'Готовлю…';
    try {
      const lib = await loadScript('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js', 'jspdf');
      try { await document.fonts.ready; } catch (e) { /* fonts optional */ }
      const cal = S.d.cal; const T = todayN();
      const PW = 1190.55, PHt = 841.89, M = 28, k = 2.4, rowH = 15, titleH = 64, headH = 30, footH = 30;
      const per = Math.floor((PHt - 2 * M - titleH - headH - footH) / rowH);
      const pages = []; for (let i = 0; i < E.rows.length; i += per) pages.push(E.rows.slice(i, i + per));
      const cols = [['wbs', '№', 32, 'center'], ['code', 'Шифр', 40, 'center'], ['name', 'Наименование работ', S.pl.owners ? 160 : 244, 'left'], ...(S.pl.owners ? [['owner', 'Исполнитель', 84, 'left']] : []), ['dur', 'Раб. дн.', 38, 'center'], ['Sd', 'Начало', 52, 'center'], ['Fd', 'Окончание', 52, 'center'], ['p', 'Вып.', 34, 'center']];
      const tblW = d3.sum(cols, (c) => c[2]); const tlX = M + tblW, tlW = PW - M - tlX;
      let d0 = d3.min(E.rows, (r) => Math.min(r.Sd, S.pl.base && r.bs ? dn(r.bs) : Infinity)), d1 = d3.max(E.rows, (r) => Math.max((S.pl.tails ? r.TFd ?? r.Fd : r.Fd) + 1, S.pl.base && r.bf ? dn(r.bf) + 1 : 0));
      const TAILP = { 'Смета': '#7c4dcc', 'Оформление': '#0f8f8a', 'Печать': '#c05621' };
      d0 -= 2; d1 += 3; const pxDay = tlW / (d1 - d0); const X = (n) => tlX + (n - d0) * pxDay;
      const FONT = '"Golos Text", Arial, sans-serif', MONO = '"JetBrains Mono", Menlo, monospace';
      const P = { ink: '#4f7fe0', inkD: '#1d4fd8', inkL: '#dbe5fb', ok: '#1d8a52', warn: '#b26a00', bad: '#c8322b', fg: '#17202c', muted: '#5d6878', line: '#c9d0db', grid: '#e9ecf1', shade: '#f2f4f7', base: '#a4adba' };
      const pdf = new lib.jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a3', compress: true });
      const colorOf = (r) => (r.state === 'done' ? P.ok : r.state === 'late' ? P.bad : r.state === 'behind' ? P.warn : P.ink);
      const fitTxt = (ctx, s, w) => { if (ctx.measureText(s).width <= w) return s; while (s.length > 2 && ctx.measureText(s + '…').width > w) s = s.slice(0, -1); return s + '…'; };
      pages.forEach((rows, pi) => {
        const cv = document.createElement('canvas'); cv.width = Math.round(PW * k); cv.height = Math.round(PHt * k);
        const c = cv.getContext('2d'); c.scale(k, k); c.fillStyle = '#fff'; c.fillRect(0, 0, PW, PHt); c.textBaseline = 'middle';
        // title block
        c.fillStyle = P.fg; c.font = `700 17px ${FONT}`; c.fillText('КАЛЕНДАРНЫЙ ГРАФИК ВЫПОЛНЕНИЯ ПРОЕКТНЫХ РАБОТ', M, M + 10);
        c.font = `500 11px ${FONT}`; c.fillText(fitTxt(c, `Объект: ${E.title}`, PW - 2 * M - 260), M, M + 32);
        c.fillStyle = P.muted; c.font = `400 10px ${FONT}`;
        c.fillText(`Заказчик: ${E.client || '—'}   ·   Исполнитель: ООО «GASTEC PROJECT»   ·   Начало ${fN(E.st.s)}   ·   Окончание ${fN(E.st.f)}   ·   ${E.st.days} раб. дн.   ·   Выполнено на ${fD(iso(today()))}: ${fPct(E.st.p)}`, M, M + 50);
        c.textAlign = 'right'; c.fillStyle = P.fg; c.font = `600 11px ${FONT}`; c.fillText('ООО «GASTEC PROJECT»', PW - M, M + 10); c.font = `400 9px ${FONT}`; c.fillStyle = P.muted; c.fillText(`Проект: ${proj}`, PW - M, M + 26); c.textAlign = 'left';
        const top = M + titleH; const bodyTop = top + headH; const bodyH = rows.length * rowH;
        // table header
        c.fillStyle = P.inkL; c.fillRect(M, top, PW - 2 * M, headH);
        let cx = M; c.fillStyle = P.fg; c.font = `600 8.5px ${FONT}`;
        cols.forEach(([, h, w]) => { c.textAlign = 'center'; c.fillText(h, cx + w / 2, top + headH / 2); cx += w; });
        // timeline header
        c.save(); c.beginPath(); c.rect(tlX, top, tlW, headH + bodyH); c.clip();
        for (let n = d0; n < d1; n++) {
          const dt = new Date(n * DAY); const first = dt.getUTCDate() === 1;
          if (pxDay >= 2.5 && !cal.isWork(n)) { c.fillStyle = P.shade; c.fillRect(X(n), bodyTop, pxDay, bodyH); }
          if (first || n === d0) {
            if (first) { c.strokeStyle = P.line; c.lineWidth = 0.8; c.beginPath(); c.moveTo(X(n), top); c.lineTo(X(n), bodyTop + bodyH); c.stroke(); }
            const room = 30 * pxDay; c.fillStyle = P.fg; c.textAlign = 'left'; c.font = `600 8px ${FONT}`;
            const lab = room > 70 ? MONTHS[dt.getUTCMonth()] + ' ' + dt.getUTCFullYear() : room > 26 ? MONTHS[dt.getUTCMonth()].slice(0, 3) + ' ' + String(dt.getUTCFullYear()).slice(2) : '';
            if (lab) c.fillText(lab, Math.max(X(n), tlX) + 3, top + 8);
          }
          c.font = `400 6.5px ${MONO}`; c.fillStyle = P.muted; c.textAlign = 'center';
          if (pxDay >= 9) c.fillText(String(dt.getUTCDate()), X(n) + pxDay / 2, top + 22);
          else if (wdOf(n) === 1 && pxDay * 7 >= 22) { c.fillText(pad(dt.getUTCDate()) + '.' + pad(dt.getUTCMonth() + 1), X(n) + 3.5 * pxDay, top + 22); c.strokeStyle = P.grid; c.lineWidth = 0.5; c.beginPath(); c.moveTo(X(n), top + 15); c.lineTo(X(n), bodyTop + bodyH); c.stroke(); }
        }
        c.restore();
        // rows
        const idx = new Map(rows.map((r, i) => [r.id, i])); const yc = (i) => bodyTop + i * rowH + rowH / 2;
        rows.forEach((r, i) => {
          const y = bodyTop + i * rowH;
          if (r.summary) { c.fillStyle = P.shade; c.fillRect(M, y, tblW, rowH); }
          c.strokeStyle = P.grid; c.lineWidth = 0.5; c.beginPath(); c.moveTo(M, y + rowH); c.lineTo(PW - M, y + rowH); c.stroke();
          let x0 = M;
          cols.forEach(([kk, , w, al]) => {
            let v = ''; c.font = `${r.summary ? 600 : 400} 8px ${FONT}`; c.fillStyle = P.fg;
            if (kk === 'wbs') v = r.wbs || ''; else if (kk === 'code') v = r.code || '';
            else if (kk === 'name') v = (r.mile ? '◆ ' : '') + (r.name || '');
            else if (kk === 'owner') v = r.owner || '';
            else if (kk === 'dur') v = r.mile ? '0' : String(r.wdays);
            else if (kk === 'Sd') v = fNs(r.Sd); else if (kk === 'Fd') v = fNs(r.Fd);
            else if (kk === 'p') { v = r.mile ? (r.state === 'done' ? '✓' : '') : fPct(r.p); }
            const pad0 = kk === 'name' ? 4 + Math.min(r.level, 5) * 9 : 0;
            c.textAlign = al; const tx = al === 'left' ? x0 + pad0 : x0 + w / 2;
            c.fillText(fitTxt(c, v, w - 6 - pad0), tx, y + rowH / 2 + 0.5); x0 += w;
          });
        });
        // column lines
        c.strokeStyle = P.line; c.lineWidth = 0.6; let lx = M; [0, ...cols.map((cc) => cc[2])].forEach((w) => { lx += w; c.beginPath(); c.moveTo(lx, top); c.lineTo(lx, bodyTop + bodyH); c.stroke(); });
        c.beginPath(); c.moveTo(M, top); c.lineTo(M, bodyTop + bodyH); c.stroke();
        c.strokeRect(M, top, PW - 2 * M, headH + bodyH);
        c.beginPath(); c.moveTo(M, bodyTop); c.lineTo(PW - M, bodyTop); c.stroke();
        // links
        c.save(); c.beginPath(); c.rect(tlX, bodyTop, tlW, bodyH); c.clip();
        if (S.pl.links) rows.forEach((s, si) => s.links.forEach((l) => {
          const pi2 = idx.get(l.id); if (pi2 == null) return; const p = rows[pi2]; const [ps, pd, ss, sa] = LINK_SIDES[l.type];
          const ax = (r, side) => (r.mile ? (side === 's' ? X(r.Fd) + pxDay / 2 - 4 : X(r.Fd) + pxDay / 2 + 4) : side === 's' ? X(r.Sd) : X(r.Fd + 1));
          const pts = linkPts({ x: ax(p, ps), y: yc(pi2), dir: pd }, { x: ax(s, ss), y: yc(si), arr: sa }, rowH);
          c.strokeStyle = '#8a94a3'; c.lineWidth = 0.6; c.beginPath(); pts.forEach((q, j) => (j ? c.lineTo(q[0], q[1]) : c.moveTo(q[0], q[1]))); c.stroke();
          const [bx, by] = pts[pts.length - 1]; c.fillStyle = '#8a94a3'; c.beginPath(); c.moveTo(bx, by); c.lineTo(bx - sa * 3.5, by - 2.4); c.lineTo(bx - sa * 3.5, by + 2.4); c.closePath(); c.fill();
        }));
        // bars
        rows.forEach((r, i) => {
          const cy = yc(i) - (S.pl.base && r.bf ? 1.5 : 0);
          if (S.pl.base && r.bs && r.bf && !r.mile) { c.fillStyle = P.base; c.fillRect(X(dn(r.bs)), cy + 4, Math.max(1, X(dn(r.bf) + 1) - X(dn(r.bs))), 2.2); }
          if (r.mile) { const m = X(r.Fd) + pxDay / 2; c.fillStyle = r.state === 'done' ? P.ok : P.fg; c.beginPath(); c.moveTo(m, cy - 5); c.lineTo(m + 5, cy); c.lineTo(m, cy + 5); c.lineTo(m - 5, cy); c.closePath(); c.fill(); c.font = `500 7px ${MONO}`; c.textAlign = 'left'; c.fillStyle = P.fg; c.fillText(fNs(r.Fd), m + 8, cy); return; }
          const x0 = X(r.Sd), x1 = Math.max(X(r.Fd + 1), x0 + 1.5), w = x1 - x0;
          if (r.summary) { c.fillStyle = P.fg; c.fillRect(x0, cy - 3, w, 4); c.beginPath(); c.moveTo(x0, cy + 1); c.lineTo(x0 + 3.5, cy + 1); c.lineTo(x0, cy + 4.5); c.closePath(); c.moveTo(x1, cy + 1); c.lineTo(x1 - 3.5, cy + 1); c.lineTo(x1, cy + 4.5); c.closePath(); c.fill(); return; }
          const col = colorOf(r);
          c.fillStyle = col; c.globalAlpha = 0.25; c.fillRect(x0, cy - 4.5, w, 9); c.globalAlpha = 1;
          if (r.p > 0) c.fillRect(x0, cy - 4.5, Math.max(1, w * r.p), 9);
          c.strokeStyle = col; c.lineWidth = 0.6; c.strokeRect(x0, cy - 4.5, w, 9);
          let xe = x1; if (S.pl.tails && r.tails) r.tails.forEach((tl) => { const a = X(tl.Sd), b = Math.max(X(tl.Fd + 1), a + 1.5); c.fillStyle = TAILP[tl.st]; c.globalAlpha = tl.done >= 0.999 ? 0.9 : 0.35; c.fillRect(a, cy - 3, b - a, 6); c.globalAlpha = 1; xe = b; });
          if (r.code && tlX + tlW - xe > 30) { c.font = `500 7px ${FONT}`; c.fillStyle = P.muted; c.textAlign = 'left'; c.fillText(r.code, xe + 3, cy); }
        });
        if (T >= d0 && T < d1) { const tx = X(T) + pxDay / 2; c.strokeStyle = P.bad; c.lineWidth = 0.9; c.setLineDash([3, 2]); c.beginPath(); c.moveTo(tx, bodyTop); c.lineTo(tx, bodyTop + bodyH); c.stroke(); c.setLineDash([]); }
        c.restore();
        if (T >= d0 && T < d1) { c.fillStyle = P.bad; c.font = `600 7px ${FONT}`; c.textAlign = 'center'; c.fillText('сегодня ' + fNs(T), X(T) + pxDay / 2, bodyTop + bodyH + 7); }
        // footer
        const fy = PHt - M - 6; c.font = `400 8px ${FONT}`; c.fillStyle = P.muted; c.textAlign = 'left';
        let lgx = M; const leg = (draw, label) => { draw(lgx, fy); lgx += 16; c.fillStyle = P.muted; c.textAlign = 'left'; c.fillText(label, lgx, fy); lgx += c.measureText(label).width + 16; };
        leg((x, y) => { c.fillStyle = P.ink; c.globalAlpha = 0.25; c.fillRect(x, y - 4, 12, 8); c.globalAlpha = 1; }, 'план');
        leg((x, y) => { c.fillStyle = P.ink; c.fillRect(x, y - 4, 12, 8); }, 'выполнено');
        leg((x, y) => { c.fillStyle = P.fg; c.fillRect(x, y - 2, 12, 4); }, 'этап');
        leg((x, y) => { c.fillStyle = P.fg; c.beginPath(); c.moveTo(x + 6, y - 5); c.lineTo(x + 11, y); c.lineTo(x + 6, y + 5); c.lineTo(x + 1, y); c.fill(); }, 'контрольная точка');
        if (S.pl.base) leg((x, y) => { c.fillStyle = P.base; c.fillRect(x, y - 1, 12, 2.2); }, 'базовый план');
        leg((x, y) => { c.fillStyle = P.bad; c.globalAlpha = 0.25; c.fillRect(x, y - 4, 12, 8); c.globalAlpha = 1; }, 'просрочено');
        c.fillText(`Сроки в рабочих днях (${cal.week}-дневная неделя, с учётом праздников)`, lgx + 10, fy);
        c.textAlign = 'right'; c.fillText(`Лист ${pi + 1} из ${pages.length} · сформировано ${fD(iso(today()))}`, PW - M, fy);
        if (pi === pages.length - 1) { c.textAlign = 'left'; c.fillStyle = P.fg; c.font = `400 9px ${FONT}`; const sy = Math.min(bodyTop + bodyH + 26, fy - 22); c.fillText('Главный инженер проекта  ____________________', M, sy); c.fillText('Согласовано: Заказчик  ____________________', tlX, sy); }
        if (pi) pdf.addPage('a3', 'landscape');
        pdf.addImage(cv.toDataURL('image/jpeg', 0.92), 'JPEG', 0, 0, PW, PHt);
      });
      await saveFile(`Календарный график ${safeName(proj)} ${fileStamp()}.pdf`, pdf.output('blob'));
    } catch (e) { toast('PDF не собрался: ' + (e.message || e)); }
    finally { btn.disabled = false; btn.textContent = t0; }
  }

  // ---------- COMPOSITION: объекты × дисциплины, перенос в график
  const DISC_FALLBACK = TEMPLATE.filter((t) => t[4] === 'Раздел' && t[2] && t[2] !== 'ИД' && t[2] !== 'ЭК').map((t, i) => ({ code: t[2], name: t[3], dur: t[5], links: '', order: i + 1 }));
  const discList = () => (S.d.disc && S.d.disc.length ? S.d.disc : DISC_FALLBACK);
  const parentWbs = (w) => { w = str(w); return w.includes('.') ? w.slice(0, w.lastIndexOf('.')) : ''; };
  const ownerShort = (n) => { const s = str(n); if (!s) return ''; const p = s.split(/\s+/); return p.length > 1 ? p[0] + ' ' + p[1][0] + '.' : s; };
  function compData(proj) {
    const rows = (S.d.plan || []).filter((r) => r.project === proj).sort((a, b) => wbsCmp(a.wbs, b.wbs) || a.id - b.id);
    const order = new Map(discList().map((d, i) => [d.code, i]));
    const objs = rows.filter((r) => str(r.wbs) && !str(r.wbs).includes('.') && (r.kind === 'Объект' || r.kind === 'Этап'));
    const groups = objs.map((o) => ({ o, kids: rows.filter((x) => parentWbs(x.wbs) === str(o.wbs) && x.kind !== 'Веха' && x.kind !== 'Объект').sort((a, b) => (order.get(a.code) ?? 999) - (order.get(b.code) ?? 999) || wbsCmp(a.wbs, b.wbs)) }));
    const extra = [...new Set(groups.flatMap((g) => g.kids.map((k) => k.code)).filter((c) => c && !order.has(c)))];
    return { rows, groups, cols: [...discList().map((d) => ({ code: d.code, name: d.name, dur: d.dur, lib: true })), ...extra.map((c) => ({ code: c, name: c, lib: false }))] };
  }
  const nextObjCode = (rows) => { const n = d3.max(rows.filter((r) => r.kind === 'Объект'), (r) => Number(str(r.code).replace(/\D/g, '')) || 0) || 0; return 'BL' + pad(n + 1); };
  function removeIds(rows, kill) {
    const keep = rows.filter((x) => !kill.has(x.id));
    keep.forEach((x) => { if (!x.preds) return; const p = parsePreds(x.preds); if (p.links.some((l) => kill.has(l.id))) x.preds = [...p.links.filter((l) => !kill.has(l.id)).map(fmtLink), ...p.bad].join('; '); });
    return keep;
  }
  function projSelect(sel) {
    const planRows = S.d.plan || []; const projs = planProjects();
    if (!S.pl.project || !projs.includes(S.pl.project)) S.pl.project = (S.filters.project && projs.includes(S.filters.project)) ? S.filters.project : (planRows[0]?.project || projs[0] || '');
    if (document.activeElement !== sel) { const cnt = d3.rollup(planRows, (v) => v.length, (r) => r.project); sel.replaceChildren(...projs.map((p) => new Option(cnt.get(p) ? `${p} · ${cnt.get(p)}` : p, p))); sel.value = S.pl.project; }
  }

  function renderComp() {
    projSelect($('#cp-project'));
    $('#cp-owners').checked = S.pl.owners;
    const box = $('#cp-matrix'); const proj = S.pl.project;
    if (!S.d.plan) { if (status('plan') === 'error') failIn(box, 'plan'); else skel(box, 200); return; }
    const C = compData(proj);
    const pending = C.rows.filter((r) => r.kind === 'Раздел' && r.inPlan === 'Нет').length;
    $('#cp-move').textContent = pending ? `Перенести в график · ${pending}` : 'Перенести в график';
    $('#cp-move').disabled = !pending; $('#cp-move').classList.toggle('primary', !!pending);
    const SP = liveSync(proj); const sn = SP ? SP.count + (SP.count ? 0 : SP.secChanges.length) : 0;
    $('#cp-sync').textContent = sn ? `Задачи и договоры · ${sn}` : 'Задачи и договоры'; $('#cp-sync').classList.toggle('primary', !!sn && !pending);
    ['#cp-xlsx', '#cp-pdf'].forEach((s) => { $(s).hidden = !C.groups.length || !S.dl; });
    const nSec = d3.sum(C.groups, (g) => g.kids.length);
    $('#cp-count').textContent = C.groups.length ? `${C.groups.length} ${plural(C.groups.length, 'объект', 'объекта', 'объектов')} · ${nSec} ${plural(nSec, 'раздел', 'раздела', 'разделов')}${pending ? ` · ${pending} ещё не в графике` : ''}` : '';
    if (!C.groups.length) {
      const e = el('div', 'pl-empty');
      e.append(el('h3', null, `Состав проекта «${proj || '—'}» пока пуст`), el('p', 'note', 'Добавьте объекты (здания и сооружения: офис, столовая, КПП, склад…) и отметьте у каждого дисциплины: АР, КЖ, ОВ, ЭС… Для каждой дисциплины можно указать исполнителя. Когда состав готов, перенесите его в график: сроки и типовые связи расставятся сами.'));
      const b = el('button', 'btn primary', '+ Объекты'); b.type = 'button'; b.addEventListener('click', () => openObject(null));
      const bi = el('button', 'btn', 'Взять из объектов платформы'); bi.type = 'button'; bi.addEventListener('click', (ev) => importPlatformObjects(ev.currentTarget));
      const bb = el('div', 'chips'); bb.append(b, bi); e.append(bb);
      box.replaceChildren(e); $('#cp-list').replaceChildren(); $('#cp-rule').replaceChildren(); return;
    }
    const tbl = el('table', 'cp-table'); const thead = el('thead'); const hr = el('tr');
    const th0 = el('th', 'cp-obj', 'Объект'); hr.append(th0);
    C.cols.forEach((c) => { const th = el('th', 'cp-col'); th.title = c.name; th.append(el('span', null, c.code)); hr.append(th); });
    const thAdd = el('th', 'cp-col'); const ba = el('button', 'btn ghost sm', '+'); ba.type = 'button'; ba.title = 'Добавить дисциплину в справочник'; ba.addEventListener('click', () => openDisc()); thAdd.append(ba); hr.append(thAdd);
    thead.append(hr); tbl.append(thead);
    const tb = el('tbody');
    C.groups.forEach((g) => {
      const tr = el('tr'); const td0 = el('th', 'cp-obj'); td0.scope = 'row';
      const ob = el('button', 'cp-objbtn'); ob.type = 'button'; ob.addEventListener('click', () => openObject(g.o));
      ob.append(el('span', 'cp-objname', g.o.name || '—'), el('span', 'cp-objmeta', [g.o.code ? 'шифр ' + g.o.code : '', `${g.kids.length} ${plural(g.kids.length, 'раздел', 'раздела', 'разделов')}`, g.o.client === 'Нет' ? 'скрыт от заказчика' : ''].filter(Boolean).join(' · ')));
      td0.append(ob); tr.append(td0);
      C.cols.forEach((c) => {
        const td = el('td', 'cp-cell'); const secs = g.kids.filter((k) => k.code === c.code);
        if (secs.length) {
          const s = secs[0]; const sch = S.d.sched?.byId.get(s.id);
          const ss = secState(s); const b = el('button', 'cp-chip ' + (s.inPlan === 'Нет' ? 'out' : 'in') + ' st-' + ss.col); b.type = 'button';
          b.title = `${s.doc ? s.doc + '\n' : ''}${s.code} — ${s.name || ''}${s.owner ? '\nИсполнитель: ' + s.owner + ' · ' + (payOf(s, S.d.people || []) === 'Оклад' ? 'оклад' : 'договор' + (isNum(s.price) ? ' ' + fMoney(s.price, curOf(s)) : ', нет цены')) : ''}${s.inPlan === 'Нет' ? '\nЕщё не в графике' : sch && sch.Sd != null ? `\nВ графике: ${fN(sch.Sd)} → ${fN(sch.Fd)}, ${fPct(sch.p)}` : ''}`;
          b.textContent = S.pl.owners ? (ownerShort(s.owner) || '✓') : '✓';
          if (secs.length > 1) b.append(el('sup', null, '×' + secs.length));
          b.addEventListener('click', () => openPlan(s.id)); td.append(b);
        } else {
          const b = el('button', 'cp-add'); b.type = 'button'; b.textContent = S.cp.busy.has(g.o.id + '|' + c.code) ? '…' : '+'; b.title = `Добавить ${c.code} в «${g.o.name}»`;
          b.addEventListener('click', () => addCell(g.o, c, b)); td.append(b);
        }
        tr.append(td);
      });
      tr.append(el('td', 'cp-cell')); tb.append(tr);
    });
    const fr = el('tr', 'cp-foot'); fr.append(el('th', 'cp-obj', 'Всего'));
    C.cols.forEach((c) => { const n = d3.sum(C.groups, (g) => g.kids.filter((k) => k.code === c.code).length); fr.append(el('td', 'cp-cell num', n ? String(n) : '')); });
    fr.append(el('td')); tb.append(fr); tbl.append(tb);
    const other = C.rows.filter((r) => !str(r.wbs).includes('.') && r.kind !== 'Объект' && r.kind !== 'Этап');
    box.replaceChildren(tbl);
    renderCompList(C);
    $('#cp-other').textContent = other.length ? `Вне объектов: ${other.map((r) => r.name).join(', ')} — видны и меняются на вкладке «График проекта».` : '';
  }

  // objects/pod-objects and disciplines from the platform's project wizard; repeat runs add only new ones
  async function importPlatformObjects(btn) {
    const proj = S.pl.project; if (!proj) return toast('Выберите проект.');
    const t0 = btn.textContent; btn.disabled = true; btn.textContent = 'Переношу…';
    try {
      const { added: a } = await apiFetch(API.planImport, { project: proj });
      toast(a.objects || a.sections || a.owners ? `Добавлено: объектов ${a.objects}, разделов ${a.sections}` + (a.owners ? `, исполнителей ${a.owners}` : '') : 'Новых объектов и дисциплин в платформе нет.');
      refreshAll();
    } catch (e) { toast(errText(e)); }
    finally { btn.disabled = false; btn.textContent = t0; }
  }
  async function addCell(obj, disc, btn) {
    const key = obj.id + '|' + disc.code; if (S.cp.busy.has(key)) return;
    S.cp.busy.add(key); btn.textContent = '…'; btn.disabled = true;
    try {
      await savePlan((rows, ctx) => {
        const o = rows.find((x) => x.id === obj.id); if (!o) throw userErr('Объект уже удалён. Обновите страницу.');
        const pr = rows.filter((x) => x.project === o.project);
        if (pr.some((x) => parentWbs(x.wbs) === str(o.wbs) && x.code === disc.code)) return rows;
        rows.push({ id: ctx.nextId++, project: o.project, wbs: nextWbs(pr, o.wbs), code: disc.code, name: disc.name, kind: 'Раздел', owner: '', dur: isNum(disc.dur) ? disc.dur : null, preds: '', client: 'Да', inPlan: 'Нет', comment: '' });
        return rows;
      });
      toast(`${disc.code} добавлен в «${obj.name}»`); refreshAll();
    } catch (e) { toast(e && e.userText ? e.userText : errText(e)); }
    finally { S.cp.busy.delete(key); }
  }

  // object editor: name(s), code, disciplines with executors
  function openObject(obj) {
    if (!S.mcp) return toast('Сервер недоступен.');
    const proj = obj?.project || S.pl.project; if (!proj) return toast('Выберите проект.');
    const C = compData(proj); const g = obj ? C.groups.find((x) => x.o.id === obj.id) : null; const kids = g ? g.kids : [];
    modal(obj ? `Объект «${obj.name}»` : `Новые объекты · ${proj}`, (m, close) => {
      const form = el('div', 'form');
      const fName = obj ? input('ob-name', 'text', obj.name || '', { autocomplete: 'off' }) : el('textarea', 'ctl');
      if (!obj) { fName.id = 'ob-name'; fName.placeholder = 'Офис\nСтоловая\nКПП'; fName.rows = 3; }
      const fCode = input('ob-code', 'text', obj?.code || '', { placeholder: obj ? 'например CS01' : 'по порядку: ' + nextObjCode(C.rows), autocomplete: 'off' }); fCode.classList.add('mono');
      const fClient = select('ob-client', [new Option('Да, показывать', 'Да'), new Option('Нет, только для нас', 'Нет')], obj?.client === 'Нет' ? 'Нет' : 'Да');
      form.append(field(obj ? 'Наименование объекта' : 'Объекты — каждый с новой строки', fName, 'full'), field('Код объекта в шифре (2 буквы + 2 цифры)', fCode), field('Показывать заказчику', fClient));
      const dl = el('datalist'); dl.id = 'ob-people'; (S.d.people || []).filter((p) => !/^(Заказчик|Партнёр)$/.test(p.role || '')).forEach((p) => dl.append(new Option(p.name)));
      // bulk executor
      const bulk = el('div', 'picker full'); const fBulk = input('ob-bulk', 'text', '', { list: 'ob-people', autocomplete: 'off', placeholder: 'один исполнитель на все отмеченные' });
      const bBulk = el('button', 'btn', 'Назначить отмеченным'); bBulk.type = 'button';
      bulk.style.gridTemplateColumns = 'minmax(0,1fr) auto'; bulk.append(field('Исполнитель сразу на все', fBulk), bBulk);
      form.append(bulk, dl);
      const cur0 = kids.find((k) => isNum(k.price))?.cur === 'сум' ? 'сум' : 'USD';
      const fOCur = select('ob-cur', ['USD', 'сум'], cur0); form.append(field('Валюта стоимостей', fOCur));
      const list = el('div', 'tp-list full ob-list'); const lines = new Map();
      C.cols.forEach((c) => {
        const ex = kids.find((k) => k.code === c.code);
        const row = el('div', 'ob-row'); const cb = el('input'); cb.type = 'checkbox'; cb.id = 'ob-c-' + c.code; cb.checked = !!ex;
        const lab = el('label', 'ob-lab'); lab.htmlFor = cb.id; lab.append(el('b', null, c.code), document.createTextNode(' ' + c.name));
        const own = input('ob-o-' + c.code, 'text', ex?.owner || '', { list: 'ob-people', autocomplete: 'off', placeholder: 'исполнитель' });
        const pr = input('ob-p-' + c.code, 'number', isNum(ex?.price) ? ex.price : '', { min: 0, step: 50, placeholder: 'стоимость' });
        const st = el('span', 'note');
        const hint = () => { const o = own.value.trim(); const pay = o ? payOf({ owner: o, pay: ex?.pay }, S.d.people || []) : ''; st.textContent = [ex ? (ex.inPlan === 'Нет' ? 'в составе' : 'в графике') : '', pay === 'Оклад' ? 'оклад' : pay === 'Договор' ? 'договор' : ''].filter(Boolean).join(' · '); pr.disabled = pay === 'Оклад'; };
        own.addEventListener('input', () => { if (own.value.trim()) cb.checked = true; hint(); }); pr.addEventListener('input', () => { if (pr.value) cb.checked = true; }); hint();
        row.append(cb, lab, own, pr, st); list.append(row); lines.set(c.code, { c, cb, own, pr, ex });
      });
      const ctl = el('div', 'chips full'); const all = el('button', 'btn sm', 'Отметить все'); all.type = 'button'; const none = el('button', 'btn sm', 'Снять все'); none.type = 'button';
      all.addEventListener('click', () => lines.forEach((l) => { l.cb.checked = true; })); none.addEventListener('click', () => lines.forEach((l) => { l.cb.checked = false; }));
      ctl.append(el('span', 'note', 'Дисциплины объекта'), all, none);
      bBulk.addEventListener('click', () => { const v = fBulk.value.trim(); lines.forEach((l) => { if (l.cb.checked) { l.own.value = v; l.own.dispatchEvent(new Event('input')); } }); });
      form.append(ctl, list); m.append(form);
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); foot.append(err);
      let delArmed = false, saveArmed = false;
      if (obj) {
        const del = el('button', 'btn ghost', 'Удалить объект'); del.type = 'button'; del.style.color = 'var(--bad)';
        del.addEventListener('click', async () => {
          const n = C.rows.filter((x) => str(x.wbs).startsWith(str(obj.wbs) + '.')).length;
          if (!delArmed) { delArmed = true; del.textContent = n ? `Удалить вместе с ${n} разделами?` : 'Точно удалить?'; return; }
          del.disabled = true; del.textContent = 'Удаляю…';
          try { await savePlan((rows) => removeIds(rows, new Set(rows.filter((x) => x.project === proj && (x.id === obj.id || str(x.wbs).startsWith(str(obj.wbs) + '.'))).map((x) => x.id)))); toast('Объект удалён'); close(); refreshAll(); }
          catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); del.disabled = false; del.textContent = 'Удалить объект'; delArmed = false; }
        });
        foot.append(del);
      }
      const cancel = el('button', 'btn ghost', 'Отмена'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const save = el('button', 'btn primary', obj ? 'Сохранить' : 'Создать'); save.type = 'button'; foot.append(cancel, save); m.append(foot);
      m.addEventListener('change', (e) => { if (saveArmed && e.target !== save) { saveArmed = false; save.textContent = 'Сохранить'; } });
      save.addEventListener('click', async () => {
        const names = obj ? [fName.value.trim()] : fName.value.split('\n').map((s) => s.trim()).filter(Boolean);
        if (!names.length || !names[0]) { err.textContent = 'Напишите наименование объекта.'; return; }
        const chosen = [...lines.values()].filter((l) => l.cb.checked);
        const removed = [...lines.values()].filter((l) => !l.cb.checked && l.ex);
        const removedPlan = removed.filter((l) => l.ex.inPlan !== 'Нет');
        if (removed.length && !saveArmed) { saveArmed = true; err.textContent = `Будут удалены: ${removed.map((l) => l.c.code).join(', ')}` + (removedPlan.length ? ' (и из графика)' : '') + '.'; save.textContent = 'Удалить и сохранить'; return; }
        err.textContent = ''; save.disabled = true; save.textContent = 'Сохраняю…';
        try {
          await savePlan((rows, ctx) => {
            const pr = () => rows.filter((x) => x.project === proj);
            const targets = [];
            if (obj) {
              const o = rows.find((x) => x.id === obj.id); if (!o) throw userErr('Объект уже удалён. Обновите страницу.');
              const nc = fCode.value.trim().toUpperCase(); if (nc !== str(o.code)) rows.filter((x) => x.project === proj && str(x.wbs).startsWith(str(o.wbs) + '.')).forEach((x) => { x.doc = ''; });
              Object.assign(o, { name: names[0], code: nc, client: fClient.value }); targets.push(o);
            } else {
              let codeN = Number(nextObjCode(pr()).slice(2)); const given = fCode.value.trim();
              names.forEach((n, i) => { const o = { id: ctx.nextId++, project: proj, wbs: nextWbs(pr(), ''), code: names.length === 1 && given ? given.toUpperCase() : 'BL' + pad(codeN++), name: n, kind: 'Объект', owner: '', dur: null, preds: '', client: fClient.value, inPlan: 'Нет', comment: '' }; rows.push(o); targets.push(o); });
            }
            targets.forEach((o) => {
              chosen.forEach((l) => {
                const ex = rows.find((x) => x.project === proj && parentWbs(x.wbs) === str(o.wbs) && x.code === l.c.code);
                const price = l.pr.value === '' ? null : Math.max(0, Number(l.pr.value));
                if (ex) { ex.owner = l.own.value.trim(); ex.price = price; if (price != null) ex.cur = fOCur.value; return; }
                rows.push({ id: ctx.nextId++, project: proj, wbs: nextWbs(pr(), o.wbs), code: l.c.code, name: l.c.name, kind: 'Раздел', owner: l.own.value.trim(), dur: isNum(l.c.dur) ? l.c.dur : null, preds: '', client: 'Да', inPlan: 'Нет', comment: '', price, cur: price != null ? fOCur.value : '' });
              });
            });
            if (obj && removed.length) return removeIds(rows, new Set(removed.map((l) => l.ex.id)));
            return rows;
          });
          toast(obj ? 'Объект сохранён' : `Создано: ${names.length} ${plural(names.length, 'объект', 'объекта', 'объектов')}`); close(); refreshAll();
        } catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); save.disabled = false; save.textContent = obj ? 'Сохранить' : 'Создать'; saveArmed = false; }
      });
    });
  }

  // new discipline in the library sheet
  function openDisc() {
    if (!S.mcp) return toast('Сервер недоступен.');
    modal('Новая дисциплина', (m, close) => {
      const form = el('div', 'form');
      const fCode = input('ds-code', 'text', '', { placeholder: 'например: ГСН', autocomplete: 'off' });
      const fName = input('ds-name', 'text', '', { placeholder: 'Газоснабжение', autocomplete: 'off' });
      const fDur = input('ds-dur', 'number', 15, { min: 1, step: 1 });
      const fLinks = input('ds-links', 'text', '', { placeholder: 'например: АР НН+10; ТХ', autocomplete: 'off' });
      form.append(field('Шифр', fCode), field('Длительность по умолчанию, раб. дн.', fDur), field('Наименование', fName, 'full'), field('Типовые связи (по шифрам других дисциплин)', fLinks, 'full'), el('p', 'note full', 'Связи применяются при переносе в график внутри одного объекта: «АР НН+10» — начать через 10 рабочих дней после начала АР; «ТХ» — после окончания ТХ.'));
      m.append(form);
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); const cancel = el('button', 'btn ghost', 'Отмена'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const save = el('button', 'btn primary', 'Добавить'); save.type = 'button'; foot.append(err, cancel, save); m.append(foot);
      save.addEventListener('click', async () => {
        const code = fCode.value.trim().toUpperCase(), name = fName.value.trim();
        if (!code || !name) { err.textContent = 'Нужны шифр и наименование.'; return; }
        if (discList().some((d) => d.code === code)) { err.textContent = `Шифр ${code} уже есть.`; return; }
        save.disabled = true; save.textContent = 'Добавляю…';
        try {
          // becomes a platform discipline (accounts.Discipline) with its Pult settings
          await apiFetch(API.disc, { code, name, dur: Number(fDur.value) || 10, links: fLinks.value.trim() });
          toast('Дисциплина добавлена'); close(); refreshAll();
        } catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); save.disabled = false; save.textContent = 'Добавить'; }
      });
    });
  }

  // transfer composition into the schedule
  function openTransfer(proj) {
    if (!S.mcp) return toast('Сервер недоступен.');
    const C = compData(proj);
    const groups = C.groups.map((g) => ({ o: g.o, pend: g.kids.filter((k) => k.inPlan === 'Нет') })).filter((g) => g.pend.length);
    if (!groups.length) return toast('Всё из состава уже в графике.');
    modal(`Перенести состав в график · ${proj}`, (m, close) => {
      const form = el('div', 'form');
      const fStart = input('tr-start', 'date', dIso(S.d.cal.next(todayN())));
      const fMode = select('tr-mode', [new Option('параллельно, с одной даты', 'par'), new Option('со сдвигом: следующий через N дней после начала предыдущего', 'lag'), new Option('последовательно: следующий после окончания предыдущего', 'seq')], 'par');
      const fLag = input('tr-lag', 'number', 10, { min: 0, step: 1 }); const lLag = field('Сдвиг, раб. дн.', fLag);
      const fLinks = el('input'); fLinks.type = 'checkbox'; fLinks.id = 'tr-links'; fLinks.checked = true;
      const lLinks = el('label', 'tp-item full'); lLinks.append(fLinks, el('span', null, 'Расставить типовые связи между дисциплинами внутри объекта (из листа «Дисциплины»)'));
      form.append(field('Начало работ', fStart), field('Объекты выполняются', fMode), lLag, lLinks);
      const list = el('div', 'tp-list full'); const boxes = new Map();
      groups.forEach((g) => {
        const l = el('label', 'tp-item'); const c = el('input'); c.type = 'checkbox'; c.checked = true; c.id = 'tr-o-' + g.o.id; boxes.set(g.o.id, c);
        l.append(c, el('b', null, g.o.name || '—'), el('span', 'note', g.pend.map((k) => k.code + (k.owner && S.pl.owners ? ' (' + ownerShort(k.owner) + ')' : '')).join(', ')));
        list.append(l);
      });
      form.append(el('p', 'note full', 'Что переносим (порядок объектов — как в составе):'), list,
        el('p', 'note full', 'Разделы получат длительность из справочника дисциплин и связи. После переноса всё можно поправить на вкладке «График проекта»; когда график согласован — сохраните базовый план.'));
      const sync = () => { lLag.hidden = fMode.value !== 'lag'; }; fMode.addEventListener('change', sync); sync();
      m.append(form);
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); const cancel = el('button', 'btn ghost', 'Отмена'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const go = el('button', 'btn primary', 'Перенести'); go.type = 'button'; foot.append(err, cancel, go); m.append(foot);
      go.addEventListener('click', async () => {
        const start = fStart.value; const chosenIds = groups.filter((g) => boxes.get(g.o.id).checked).map((g) => g.o.id);
        if (!chosenIds.length) { err.textContent = 'Отметьте хотя бы один объект.'; return; }
        go.disabled = true; go.textContent = 'Переношу…';
        const lib = new Map(discList().map((d) => [d.code, d])); const mode = fMode.value, lag = Math.max(0, Number(fLag.value) || 0);
        try {
          await savePlan((rows) => {
            const pr = rows.filter((x) => x.project === proj);
            const objs = chosenIds.map((id) => rows.find((x) => x.id === id)).filter(Boolean).sort((a, b) => wbsCmp(a.wbs, b.wbs));
            const kidsOf = (o) => pr.filter((x) => parentWbs(x.wbs) === str(o.wbs) && x.kind !== 'Объект');
            objs.forEach((o, i) => {
              const ks = kidsOf(o); const moving = ks.filter((k) => k.inPlan === 'Нет' && k.kind !== 'Веха');
              moving.forEach((k) => { k.inPlan = 'Да'; if (!isNum(k.dur) || k.dur < 1) k.dur = isNum(lib.get(k.code)?.dur) ? lib.get(k.code).dur : 10; });
              o.inPlan = 'Да';
              if (fLinks.checked) moving.forEach((k) => {
                if (str(k.preds)) return; const spec = str(lib.get(k.code)?.links); if (!spec) return;
                const out = spec.split(';').map((s) => s.trim()).filter(Boolean).map((tok) => {
                  const [code, rest = ''] = tok.split(/\s+/); let p = ks.find((x) => x.code === code && x.inPlan !== 'Нет');
                  if (!p) { const cands = pr.filter((x) => x.code === code && x.inPlan !== 'Нет'); if (cands.length === 1) p = cands[0]; }
                  return p ? p.id + rest.replace(/\s+/g, '') : null;
                }).filter(Boolean);
                k.preds = out.join('; ');
              });
              if (!str(o.preds)) {
                const prev = objs[i - 1];
                if (prev && mode === 'seq') o.preds = String(prev.id);
                else if (prev && mode === 'lag') o.preds = `${prev.id}НН+${lag}`;
                else if (start && !o.snet) o.snet = start;
              }
            });
            return rows;
          });
          toast('Состав перенесён в график, сроки рассчитаны'); close(); refreshAll(); goTab('plan');
        } catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); go.disabled = false; go.textContent = 'Перенести'; }
      });
    });
  }

  // ---------- composition exports (ведомость состава)
  function compExportRows(proj) {
    const C = compData(proj); const out = [];
    C.groups.filter((g) => g.o.client !== 'Нет').forEach((g, i) => {
      out.push({ obj: true, n: String(i + 1), code: g.o.code || '', name: g.o.name || '', owner: '', note: g.o.comment || '' });
      g.kids.filter((k) => k.client !== 'Нет').forEach((k, j) => out.push({ obj: false, n: `${i + 1}.${j + 1}`, code: k.doc || [g.o.code, k.code].filter(Boolean).join('-'), name: (k.code ? k.code + '. ' : '') + (k.name || ''), owner: k.owner || '', note: k.comment || '' }));
    });
    const P = (S.d.projects || []).find((p) => p.name === proj) || {};
    return { rows: out, title: P.full || proj, client: P.client || '' };
  }
  async function exportCompXlsx(btn) {
    const proj = S.pl.project; const E = compExportRows(proj); if (!E.rows.length) return toast('Нечего выгружать.');
    btn.disabled = true; const t0 = btn.textContent; btn.textContent = 'Готовлю…';
    try {
      const X = await loadScript('https://cdnjs.cloudflare.com/ajax/libs/exceljs/4.4.0/exceljs.min.js', 'ExcelJS');
      const own = S.pl.owners;
      const cols = [['n', '№ п/п', 7], ['code', 'Обозначение', 36], ['name', 'Наименование', own ? 44 : 58], ...(own ? [['owner', 'Исполнитель', 24]] : []), ['note', 'Примечание', 22]];
      const wb = new X.Workbook(); wb.creator = 'GASTEC PROJECT';
      const ws = wb.addWorksheet('Состав проекта', { views: [{ state: 'frozen', ySplit: 6, showGridLines: false }] });
      ws.pageSetup = { paperSize: 9, orientation: 'portrait', fitToPage: true, fitToWidth: 1, fitToHeight: 0, printTitlesRow: '6:6', margins: { left: 0.5, right: 0.3, top: 0.5, bottom: 0.5, header: 0.2, footer: 0.2 } };
      ws.headerFooter = { oddFooter: '&L&8ООО «GASTEC PROJECT» · Состав проекта · ' + proj.replace(/&/g, '&&') + '&R&8Лист &P из &N' };
      ws.columns = cols.map((c) => ({ width: c[2] }));
      const NC = cols.length; const F = (o = {}) => ({ name: 'Arial', size: 10, ...o });
      const thin = { style: 'thin', color: { argb: 'FF9AA3B0' } }; const box = { top: thin, left: thin, bottom: thin, right: thin };
      ws.mergeCells(1, 1, 1, NC); Object.assign(ws.getCell(1, 1), { value: 'СОСТАВ ПРОЕКТНОЙ ДОКУМЕНТАЦИИ', font: F({ size: 14, bold: true }), alignment: { horizontal: 'center' } }); ws.getRow(1).height = 24;
      [`Объект: ${E.title}`, `Заказчик: ${E.client || '—'}`, `Генеральный проектировщик: ООО «GASTEC PROJECT»     Дата: ${fD(iso(today()))}`].forEach((t, i) => { ws.mergeCells(2 + i, 1, 2 + i, NC); Object.assign(ws.getCell(2 + i, 1), { value: t, font: F() }); });
      cols.forEach((c, i) => Object.assign(ws.getCell(6, i + 1), { value: c[1], font: F({ bold: true }), alignment: { horizontal: 'center', vertical: 'middle', wrapText: true }, fill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFDBE5FB' } }, border: box }));
      ws.getRow(6).height = 22;
      E.rows.forEach((r, i) => {
        const row = ws.getRow(7 + i);
        cols.forEach(([k], ci) => { const c = row.getCell(ci + 1); c.value = r.obj && k === 'name' ? r.name : r[k]; c.font = F({ bold: r.obj }); c.border = box; c.alignment = { vertical: 'middle', horizontal: k === 'name' || k === 'note' || k === 'owner' ? 'left' : 'center', wrapText: true }; if (r.obj) c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF0F2F5' } }; });
      });
      const rn = 7 + E.rows.length + 2; ws.getCell(rn, 3).value = 'Главный инженер проекта  ____________________'; ws.getCell(rn, 3).font = F();
      const buf = await wb.xlsx.writeBuffer();
      await saveFile(`Состав проекта ${safeName(proj)} ${fileStamp()}.xlsx`, new Blob([buf]));
    } catch (e) { toast('Excel не собрался: ' + (e.message || e)); }
    finally { btn.disabled = false; btn.textContent = t0; }
  }
  async function exportCompPdf(btn) {
    const proj = S.pl.project; const E = compExportRows(proj); if (!E.rows.length) return toast('Нечего выгружать.');
    btn.disabled = true; const t0 = btn.textContent; btn.textContent = 'Готовлю…';
    try {
      const lib = await loadScript('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js', 'jspdf');
      try { await document.fonts.ready; } catch (e) { /* optional */ }
      const PW = 595.28, PHt = 841.89, M = 40, k = 3; const own = S.pl.owners;
      const FONT = '"Golos Text", Arial, sans-serif';
      const cols = [['n', '№ п/п', 30, 'center'], ['code', 'Обозначение', 150, 'left'], ['name', 'Наименование', 0, 'left'], ...(own ? [['owner', 'Исполнитель', 104, 'left']] : []), ['note', 'Примечание', 74, 'left']];
      const fixedW = d3.sum(cols, (c) => c[2]); cols.forEach((c) => { if (c[0] === 'name') c[2] = PW - 2 * M - fixedW; });
      const meas = document.createElement('canvas').getContext('2d');
      const wrap = (txt, w, font) => { meas.font = font; const words = str(txt).split(/\s+/); const lines = []; let cur = ''; words.forEach((wd) => { const t = cur ? cur + ' ' + wd : wd; if (meas.measureText(t).width <= w || !cur) cur = t; else { lines.push(cur); cur = wd; } }); if (cur) lines.push(cur); return lines.length ? lines.slice(0, 3) : ['']; };
      const lineH = 11, headH = 24, titleH = 92, footH = 24;
      const MONO = '"JetBrains Mono", Menlo, monospace'; const cfont = (r, kk) => (kk === 'code' ? `${r.obj ? 600 : 400} 6.6px ${MONO}` : `${r.obj ? 600 : 400} 8.5px ${FONT}`);
      const prepared = E.rows.map((r) => { const font = cfont(r, 'name'); const cells = cols.map(([kk, , w]) => wrap(r[kk], w - 8, cfont(r, kk))); const h = Math.max(...cells.map((c) => c.length)) * lineH + 6; return { r, font, cells, h }; });
      const pages = []; let cur = [], used = 0;
      prepared.forEach((p) => { const avail = PHt - 2 * M - headH - footH - (pages.length ? 20 : titleH); if (used + p.h > avail && cur.length) { pages.push(cur); cur = []; used = 0; } cur.push(p); used += p.h; });
      if (cur.length) pages.push(cur);
      const pdf = new lib.jsPDF({ orientation: 'portrait', unit: 'pt', format: 'a4', compress: true });
      pages.forEach((rows, pi) => {
        const cv = document.createElement('canvas'); cv.width = Math.round(PW * k); cv.height = Math.round(PHt * k);
        const c = cv.getContext('2d'); c.scale(k, k); c.fillStyle = '#fff'; c.fillRect(0, 0, PW, PHt); c.textBaseline = 'middle'; c.fillStyle = '#17202c';
        let y = M;
        if (pi === 0) {
          c.textAlign = 'center'; c.font = `700 14px ${FONT}`; c.fillText('СОСТАВ ПРОЕКТНОЙ ДОКУМЕНТАЦИИ', PW / 2, y + 8);
          c.textAlign = 'left'; c.font = `400 9.5px ${FONT}`;
          [`Объект: ${E.title}`, `Заказчик: ${E.client || '—'}`, `Генеральный проектировщик: ООО «GASTEC PROJECT»`, `Дата: ${fD(iso(today()))}`].forEach((t, i) => c.fillText(t, M, y + 32 + i * 14));
          y += titleH;
        } else y += 20;
        c.fillStyle = '#dbe5fb'; c.fillRect(M, y, PW - 2 * M, headH); c.fillStyle = '#17202c'; c.font = `600 8.5px ${FONT}`;
        let x = M; cols.forEach(([, h, w]) => { c.textAlign = 'center'; c.fillText(h, x + w / 2, y + headH / 2); x += w; });
        const top = y; y += headH;
        rows.forEach((p) => {
          if (p.r.obj) { c.fillStyle = '#f0f2f5'; c.fillRect(M, y, PW - 2 * M, p.h); }
          c.fillStyle = '#17202c'; c.font = p.font; let xx = M;
          cols.forEach(([kk, , w, al], ci) => { c.font = cfont(p.r, kk); c.textAlign = al; p.cells[ci].forEach((ln, li) => c.fillText(ln, al === 'center' ? xx + w / 2 : xx + 4, y + 3 + lineH / 2 + li * lineH)); xx += w; });
          c.strokeStyle = '#9aa3b0'; c.lineWidth = 0.5; c.beginPath(); c.moveTo(M, y + p.h); c.lineTo(PW - M, y + p.h); c.stroke(); y += p.h;
        });
        c.strokeStyle = '#9aa3b0'; c.lineWidth = 0.6; c.strokeRect(M, top, PW - 2 * M, y - top); let lx = M; cols.slice(0, -1).forEach(([, , w]) => { lx += w; c.beginPath(); c.moveTo(lx, top); c.lineTo(lx, y); c.stroke(); }); c.beginPath(); c.moveTo(M, top + headH); c.lineTo(PW - M, top + headH); c.stroke();
        if (pi === pages.length - 1) { c.textAlign = 'left'; c.font = `400 9.5px ${FONT}`; c.fillStyle = '#17202c'; c.fillText('Главный инженер проекта  ____________________', M, Math.min(y + 30, PHt - M - footH)); }
        c.font = `400 7.5px ${FONT}`; c.fillStyle = '#5d6878'; c.textAlign = 'left'; c.fillText(`ООО «GASTEC PROJECT» · Состав проекта · ${proj}`, M, PHt - M + 6); c.textAlign = 'right'; c.fillText(`Лист ${pi + 1} из ${pages.length}`, PW - M, PHt - M + 6);
        if (pi) pdf.addPage('a4', 'portrait');
        pdf.addImage(cv.toDataURL('image/jpeg', 0.92), 'JPEG', 0, 0, PW, PHt);
      });
      await saveFile(`Состав проекта ${safeName(proj)} ${fileStamp()}.pdf`, pdf.output('blob'));
    } catch (e) { toast('PDF не собрался: ' + (e.message || e)); }
    finally { btn.disabled = false; btn.textContent = t0; }
  }

  // ---------- CIPHERS: ПРЕФИКС+СТАДИЯ_ПРОЕКТ_ОБЪЕКТ_ДИСЦИПЛИНА_ТИП_00001 (как в MDR: FGCBAS_OXS01_CS01_EL_DWG_00001)
  const areaOf = (code, rule) => { const c = str(code).toUpperCase(); if (!c) return str(rule.common || 'ZZ01').toUpperCase(); return /^\d+$/.test(c) ? 'BL' + c.padStart(2, '0') : c; };
  function cipherBase(r, rows, rule, lib) {
    if (r.kind === 'Объект' || r.kind === 'Этап' || r.kind === 'Веха' || !str(r.code)) return null;
    const d = lib.get(str(r.code)); const lat = str(d?.lat).toUpperCase(); if (!lat) return null;
    const obj = rows.find((x) => x.project === r.project && x.kind === 'Объект' && str(x.wbs) && str(r.wbs).startsWith(str(x.wbs) + '.'));
    const area = obj ? areaOf(obj.code, rule) : str(rule.common || 'ZZ01').toUpperCase();
    return [str(rule.prefix) + str(rule.stage), str(rule.code), area, lat, str(d.dtype) || 'DWG'].map((x) => x.toUpperCase().replace(/\s+/g, '')).join('_');
  }
  function assignCiphers(rows, proj, all, rule) {
    const lib = new Map(discList().map((d) => [d.code, d])); const digits = Math.max(2, Math.min(8, rule.digits || 5));
    const prs = rows.filter((r) => r.project === proj).sort((a, b) => wbsCmp(a.wbs, b.wbs) || a.id - b.id);
    if (all) prs.forEach((r) => { if (cipherBase(r, rows, rule, lib)) r.doc = ''; });
    const max = new Map();
    prs.forEach((r) => { const m = str(r.doc).match(/^(.*)_(\d+)$/); if (m) max.set(m[1], Math.max(max.get(m[1]) || 0, Number(m[2]))); });
    prs.forEach((r) => { if (str(r.doc)) return; const b = cipherBase(r, rows, rule, lib); if (!b) return; const n = (max.get(b) || 0) + 1; max.set(b, n); r.doc = b + '_' + String(n).padStart(digits, '0'); });
    return rows;
  }
  function renderCompList(C) {
    const proj = S.pl.project; const rule = S.d.ciph?.get(proj); const lib = new Map(discList().map((d) => [d.code, d]));
    const rb = $('#cp-rule'); rb.replaceChildren();
    if (!rule) { const b = el('div', 'banner'); b.append(el('span', null, `Для проекта «${proj}» ещё не заданы правила шифра (префикс, стадия, код проекта). Пока их нет, разделы остаются без шифра.`)); const x = el('button', 'btn sm', 'Задать правила'); x.type = 'button'; x.addEventListener('click', () => openCipher(proj)); b.append(x); rb.append(b); }
    else { const p = el('p', 'note'); p.append(document.createTextNode('Шифр: '), el('span', 'mono', `${str(rule.prefix)}${str(rule.stage)}_${str(rule.code)}_объект_дисциплина_тип_${'0'.repeat(Math.max(1, (rule.digits || 5) - 1))}1`), document.createTextNode('. Номер идёт по порядку внутри одинакового начала шифра.')); rb.append(p); }
    const t = $('#cp-list'); const own = S.pl.owners; const people = S.d.people || [];
    const hd = el('thead'); const hr = el('tr'); ['№', 'Обозначение', 'Наименование', 'Объект', ...(own ? ['Исполнитель'] : []), 'Оплата', 'Стоимость', 'Договор', 'Этап', 'В графике'].forEach((h) => hr.append(el('th', null, h))); hd.append(hr);
    const conById = new Map((S.d.contracts || []).map((c) => [c.id, c])); const taskById = new Map((S.d.tasks || []).map((x) => [x.id, x]));
    const tb = el('tbody'); let n = 0, missing = 0;
    C.groups.forEach((g, i) => {
      g.kids.forEach((k, j) => {
        n++; const tr = el('tr', 'click'); tr.addEventListener('click', () => openPlan(k.id));
        const code = el('td', 'mono'); code.textContent = k.doc || '—';
        if (!k.doc) { missing++; code.style.color = 'var(--faint)'; if (rule && !str(lib.get(k.code)?.lat)) code.title = `У дисциплины ${k.code} нет латинского кода (админка: «Discipline configs»)`; }
        tr.append(el('td', 'num', `${i + 1}.${j + 1}`), code, el('td', null, `${k.code ? k.code + '. ' : ''}${k.name || ''}`), el('td', null, `${g.o.name || ''}${g.o.code ? ' (' + g.o.code + ')' : ''}`), ...(own ? [el('td', null, k.owner || '—')] : []));
        const pay = k.owner ? payOf(k, people) : ''; const pc = el('td'); if (pay) pc.append(el('span', 'pill ' + (pay === 'Договор' ? 'warn' : ''), pay === 'Договор' ? 'договор' : 'оклад')); tr.append(pc);
        const prc = el('td', 'num r'); if (pay === 'Договор') { if (isNum(k.price) && k.price > 0) prc.textContent = fMoney(k.price, curOf(k)); else { prc.textContent = 'нет цены'; prc.style.color = 'var(--bad)'; } } tr.append(prc);
        const cc = el('td', 'num'); const con = k.contract ? conById.get(k.contract) : null; if (con) { cc.textContent = `${con.id} · ост. ${fMoney(con.rest || 0, curOf(con))}`; if ((con.rest || 0) < 0) cc.style.color = 'var(--bad)'; } else if (k.contract) cc.textContent = k.contract; tr.append(cc);
        const tc = el('td'); const ks = secState(k); const kc = PK_COLS.find((c) => c.key === ks.col); void taskById;
        if (ks.cur || ks.closed || ks.pending) tc.append(el('span', 'pill ' + (ks.closed ? 'ok' : ks.pending ? 'warn' : 'ink'), `${kc.title}${ks.cur ? ' · ' + (ks.cur.assignee || '—') : ks.pending ? ' · назначить' : ''} · ${Math.round(ks.pct * 100)}%`));
        else if (k.owner) { tc.textContent = 'задача не создана'; tc.style.color = 'var(--faint)'; } tr.append(tc);
        const st = el('td'); st.append(el('span', 'pill ' + (k.inPlan === 'Нет' ? '' : 'ink'), k.inPlan === 'Нет' ? 'нет' : 'да')); tr.append(st); tb.append(tr);
      });
    });
    t.replaceChildren(hd, tb);
    // finance summary of the composition
    const all = C.groups.flatMap((g) => g.kids); const fin = $('#cp-fin'); fin.replaceChildren();
    if (all.length) {
      const byCur = { USD: 0, 'сум': 0 }; let nPay = 0, nSal = 0, nNo = 0, nNoPrice = 0;
      all.forEach((k) => { if (!k.owner) { nNo++; return; } const p = payOf(k, people); if (p === 'Оклад') { nSal++; return; } nPay++; if (isNum(k.price) && k.price > 0) byCur[curOf(k)] += k.price; else nNoPrice++; });
      const cons = [...new Set(all.map((k) => k.contract).filter(Boolean))].map((id) => conById.get(id)).filter(Boolean);
      const usd = (c, v) => (curOf(c) === 'USD' ? v : S.d.rate ? v / S.d.rate : 0);
      const item = (kk, v, cls) => { const x = el('span', 'pl-kv'); x.append(el('span', null, kk + ' '), el('b', cls || null, v)); return x; };
      fin.append(item('По договорам', [byCur.USD ? fUsd(byCur.USD) : '', byCur['сум'] ? fNum(byCur['сум']) + ' сум' : ''].filter(Boolean).join(' + ') || '—'), item('разделов', fNum(nPay)), item('Договоров', fNum(cons.length)), item('оплачено', fUsd(d3.sum(cons, (c) => usd(c, c.paid || 0)))), item('остаток', fUsd(d3.sum(cons, (c) => usd(c, c.rest || 0)))), item('В окладе', fNum(nSal)));
      if (nNo) fin.append(item('Без исполнителя', fNum(nNo), 'warn'));
      if (nNoPrice) fin.append(item('Без стоимости', fNum(nNoPrice), 'bad'));
    }
    $('#cp-list-count').textContent = n ? `${n} ${plural(n, 'документ', 'документа', 'документов')}${missing ? ` · без шифра ${missing}` : ''}` : '';
  }
  function openCipher(proj) {
    if (!S.mcp) return toast('Сервер недоступен.');
    if (!proj) return toast('Выберите проект.');
    const cur = S.d.ciph?.get(proj) || {};
    modal(`Правила шифра · ${proj}`, (m, close) => {
      const form = el('div', 'form');
      const fPre = input('cf-pre', 'text', cur.prefix ?? 'FGC', { autocomplete: 'off' });
      const fStage = input('cf-stage', 'text', cur.stage ?? 'BAS', { list: 'cf-stages', autocomplete: 'off' });
      const dl = el('datalist'); dl.id = 'cf-stages'; ['BAS', 'DET'].forEach((x) => dl.append(new Option(x)));
      const fCode = input('cf-code', 'text', cur.code ?? '', { placeholder: 'например OXS01', autocomplete: 'off' });
      const fDig = input('cf-dig', 'number', cur.digits ?? 5, { min: 2, max: 8, step: 1 });
      const fCom = input('cf-com', 'text', cur.common ?? 'ZZ01', { autocomplete: 'off' });
      [fPre, fStage, fCode, fCom].forEach((x) => x.classList.add('mono'));
      const prev = el('div', 'confirm full mono');
      form.append(field('Префикс (организация / договор)', fPre), field('Стадия: BAS — основной, DET — рабочий', fStage), field('Код проекта', fCode), field('Цифр в порядковом номере', fDig), field('Код для разделов вне объектов', fCom), dl, prev,
        el('p', 'note full', 'Код объекта берётся из объекта (CS01, AS01…; задаётся при клике на имя объекта в составе). Латинский код дисциплины и тип документа (DWG, DES, LST…) — в админке платформы («GASTEC Пульт → Discipline configs»). Шифр присваивается сам каждому новому разделу; уже выданные шифры не меняются, пока вы не нажмёте «Присвоить заново».'));
      m.append(form);
      const rule = () => ({ prefix: fPre.value.trim().toUpperCase(), stage: fStage.value.trim().toUpperCase(), code: fCode.value.trim().toUpperCase(), digits: Math.max(2, Math.min(8, Number(fDig.value) || 5)), common: fCom.value.trim().toUpperCase() || 'ZZ01' });
      const C = compData(proj); const lib = new Map(discList().map((d) => [d.code, d]));
      const sample = C.groups.flatMap((g) => g.kids).find((k) => cipherBase(k, C.rows, rule(), lib));
      const showPrev = () => { const r = rule(); const b = sample ? cipherBase(sample, C.rows, r, lib) : [r.prefix + r.stage, r.code, 'CS01', 'AR', 'DWG'].join('_'); prev.textContent = 'Пример: ' + b + '_' + '1'.padStart(r.digits, '0') + (sample ? `  (${sample.code}, ${sample.name})` : ''); };
      form.addEventListener('input', showPrev); showPrev();
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); const cancel = el('button', 'btn ghost', 'Отмена'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const regen = el('button', 'btn', 'Сохранить и присвоить заново всем'); regen.type = 'button';
      const save = el('button', 'btn primary', 'Сохранить'); save.type = 'button'; foot.append(err, cancel, regen, save); m.append(foot);
      let armed = false;
      const go = async (all) => {
        const r = rule(); if (!r.prefix || !r.stage || !r.code) { err.textContent = 'Нужны префикс, стадия и код проекта.'; return; }
        if (all && !armed) { armed = true; regen.textContent = 'Все шифры проекта будут выданы заново. Нажмите ещё раз'; return; }
        [save, regen].forEach((b) => { b.disabled = true; }); err.textContent = '';
        try {
          await apiFetch(API.ciph, { project: proj, ...r });
          const rules = new Map(S.d.ciph || []); rules.set(proj, r);
          await savePlan((rows, ctx) => { ctx.rules = rules; if (all) assignCiphers(rows, proj, true, r); return rows; });
          toast(all ? 'Шифры присвоены заново' : 'Правила сохранены, новым разделам шифры присвоены'); close(); refreshAll();
        } catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); [save, regen].forEach((b) => { b.disabled = false; }); }
      };
      save.addEventListener('click', () => go(false)); regen.addEventListener('click', () => go(true));
    });
  }

  // ---------- SECTIONS → TASKS → CONTRACTS
  // Каждый раздел с исполнителем = задача исполнителю (связь: «Задача №» в составе и «Раздел (ID)» в задаче).
  // Если раздел оплачивается по договору — он входит в договор «Состав проекта» с этим исполнителем:
  // один договор на (проект, исполнитель, дисциплина, валюта), сумма = сумма стоимостей его разделов.
  // Разделы «в окладе» договоров не создают и в финансах не считаются.
  const SYNC_MARK = 'Из состава проекта';
  const AUTO_SRC = 'Состав проекта';
  const curOf = (s) => (str(s.cur).toLowerCase() === 'сум' ? 'сум' : 'USD');
  const fMoney = (v, cur) => (cur === 'сум' ? fNum(v) + ' сум' : fUsd(v));
  function personIn(people, name) { const n = str(name); if (!n) return null; return people.find((p) => p.name === n) || people.find((p) => str(p.first) === n) || null; }
  function payOf(s, people) {
    if (s.pay === 'Договор' || s.pay === 'Оклад') return s.pay;
    const p = personIn(people, s.owner); if (!p) return 'Договор';
    if (p.pay === 'Договор' || p.pay === 'Оклад') return p.pay;
    return /Штатный/i.test(p.role || '') ? 'Оклад' : 'Договор';
  }
  const conNameOf = (people, owner) => { const p = personIn(people, owner); return p ? str(p.first) : str(owner); };
  const isSection = (r) => r.kind === 'Раздел' || (!r.kind && str(r.code) && str(r.wbs).includes('.'));

  // pure planner: what has to change so that tasks and contracts match the composition
  function planSync(proj, D) {
    const rows = D.plan.filter((r) => r.project === proj);
    const secs = rows.filter(isSection).sort((a, b) => wbsCmp(a.wbs, b.wbs) || a.id - b.id);
    const objOf = (s) => rows.find((x) => x.kind === 'Объект' && str(x.wbs) && str(s.wbs).startsWith(str(x.wbs) + '.'));
    const out = { taskNew: [], taskUpd: [], conNew: [], conUpd: [], sec: new Map(), warn: [], info: [] };
    const tasks = D.tasks || []; const noCons = D.contracts == null; const cons = D.contracts || [];
    let maxTask = d3.max(tasks, (t) => t.id) || 0;
    let maxCon = d3.max(cons, (c) => Number(str(c.id).replace(/\D/g, '')) || 0) || 0;
    const tById = new Map(tasks.map((t) => [t.id, t]));
    const label = (s) => `${s.code || ''} ${s.name || ''}${objOf(s) ? ' · ' + objOf(s).name : ''}`.trim();
    const setSec = (s, k, v) => { const cur = out.sec.get(s.id) || {}; cur[k] = v; out.sec.set(s.id, cur); };
    const want = (s, pay) => {
      const sc = D.sched ? D.sched.get(s.id) : null; const obj = objOf(s);
      const usd = curOf(s) === 'USD';
      let amount = '';
      if (pay === 'Договор' && isNum(s.price) && s.price > 0) amount = usd ? (D.rate ? Math.round(s.price * D.rate) : '') : s.price;
      return { assignee: str(s.owner), project: proj, task: `${s.code ? s.code + ' — ' : ''}${s.name || ''}${obj ? ' · ' + obj.name : ''}`, amount,
        start: '', days: sc && sc.Sd != null ? Math.max(1, sc.Fd - sc.Sd) : '', planned: sc && sc.Sd != null ? dIso(sc.Sd) : '', section: s.id, comment: SYNC_MARK + (s.doc ? ': ' + s.doc : '') };
    };
    // ---- tasks
    secs.forEach((s) => {
      const owner = str(s.owner); const pay = owner ? payOf(s, D.people) : null;
      let t = isNum(s.task) ? tById.get(s.task) : null; if (t && t.section !== s.id) t = null;
      if (t && t.stage && t.stage !== 'Проектирование') t = null;
      if (!t) t = tasks.filter((x) => x.section === s.id && (!x.stage || x.stage === 'Проектирование') && x.status !== 'Отменена').sort((a, b) => b.id - a.id)[0] || null;
      if (!owner) {
        if (t && !CLOSED.includes(t.status)) out.taskUpd.push({ t, set: { status: 'Отменена' }, why: `${label(s)}: исполнитель снят — задача №${t.id} отменяется` });
        setSec(s, 'task', t ? t.id : ''); return;
      }
      const w = want(s, pay);
      if (!t || (t.status === 'Принята' && t.assignee !== owner)) {
        const id = ++maxTask; out.taskNew.push({ id, ...w, status: 'Черновик', s });
        setSec(s, 'task', id); return;
      }
      setSec(s, 'task', t.id);
      if (t.status === 'Отменена') { out.info.push(`${label(s)}: задача №${t.id} отменена вручную, новую не ставлю`); return; }
      if (t.status === 'Принята') return;
      const set = {}; const why = [];
      if (t.assignee !== w.assignee) { set.assignee = w.assignee; why.push(`исполнитель ${t.assignee || '—'} → ${w.assignee}`); }
      if (str(t.task) !== w.task) { set.task = w.task; why.push('название'); }
      const ta = isNum(t.amount) ? t.amount : ''; if (ta !== w.amount) { set.amount = w.amount; why.push(`сумма ${ta === '' ? '—' : fNum(ta)} → ${w.amount === '' ? '—' : fNum(w.amount)}`); }
      const datesFree = t.status === 'Черновик' || t.status === 'Новая';
      if (datesFree && w.days !== '' && t.days !== w.days) { set.days = w.days; why.push(`срок ${t.days ?? '—'} → ${w.days} дн. (по графику)`); }
      else if (!datesFree && w.days !== '' && t.days !== w.days && t.status !== 'На проверке') out.info.push(`${label(s)}: задача №${t.id} уже принята в работу, её срок не меняю — по графику ${w.days} дн.`);
      if (Object.keys(set).length) out.taskUpd.push({ t, set, why: `№${t.id} ${label(s)}: ${why.join(', ')}` });
    });
    const allIds = new Set(D.plan.map((r) => r.id));
    tasks.filter((t) => t.project === proj && isNum(t.section) && !allIds.has(t.section) && (str(t.comment).startsWith(SYNC_MARK) || str(t.comment).startsWith('Этап проекта')) && !CLOSED.includes(t.status))
      .forEach((t) => out.taskUpd.push({ t, set: { status: 'Отменена' }, why: `№${t.id} ${t.task}: раздел удалён из состава — задача отменяется` }));
    // ---- contracts
    if (noCons) { out.info.push('Договоры не проверялись: нет доступа к финансам. Их создаст руководитель или бухгалтер.'); out.secChanges = [...out.sec.entries()].filter(([id, v]) => { const s = rows.find((r) => r.id === id); return s && 'task' in v && str(v.task) !== str(s.task ?? ''); }); out.count = out.taskNew.length + out.taskUpd.length; return out; }
    const groups = new Map();
    secs.forEach((s) => {
      const owner = str(s.owner); const linked = s.contract ? cons.find((c) => c.id === s.contract) : null;
      if (!owner || payOf(s, D.people) !== 'Договор') { if (s.contract && (!linked || linked.src === AUTO_SRC)) setSec(s, 'contract', ''); return; }
      if (linked && linked.src !== AUTO_SRC) { setSec(s, 'contract', linked.id); return; }
      if (!(isNum(s.price) && s.price > 0)) { out.warn.push(`${label(s)} (${owner}): по договору, но не указана стоимость — в договор не включён`); if (s.contract) setSec(s, 'contract', ''); return; }
      const name = conNameOf(D.people, owner); const cur = curOf(s); const code = str(s.code) || '—';
      if (!personIn(D.people, owner)) out.warn.push(`${owner}: нет среди пользователей платформы — договор будет на имя «${name}» без привязки к сотруднику`);
      const key = [name, code, cur].join('|');
      const g = groups.get(key) || { name, code, cur, secs: [], prefer: new Set() }; g.secs.push(s); if (linked) g.prefer.add(linked.id); groups.set(key, g);
    });
    const autoCons = cons.filter((c) => c.project === proj && c.src === AUTO_SRC);
    const used = new Set();
    groups.forEach((g) => {
      const amount = d3.sum(g.secs, (s) => s.price);
      const places = [...new Set(g.secs.map((s) => (objOf(s) ? objOf(s).name : s.name)))];
      const note = `${AUTO_SRC}: ${places.join(', ')}`;
      const fits = (c) => !used.has(c.id) && str(c.name) === g.name && str(c.section) === g.code && curOf(c) === g.cur;
      let c = autoCons.find((x) => g.prefer.has(x.id) && fits(x)) || autoCons.find(fits);
      if (c) {
        used.add(c.id); const set = {}; const why = [];
        if (c.amount !== amount) { set.amount = amount; why.push(`сумма ${fMoney(c.amount, g.cur)} → ${fMoney(amount, g.cur)}`); }
        if (str(c.note) !== note) { set.note = note; why.push('состав: ' + places.join(', ')); }
        if (Object.keys(set).length) out.conUpd.push({ c, set, why: `${c.id} ${g.name} · ${g.code}: ${why.join(', ')}` });
        if (isNum(c.paid) && c.paid > amount) out.warn.push(`${c.id} ${g.name}: уже оплачено ${fMoney(c.paid, g.cur)}, больше новой суммы ${fMoney(amount, g.cur)} — переплата`);
        g.secs.forEach((s) => setSec(s, 'contract', c.id));
      } else {
        const id = 'Д-' + String(++maxCon).padStart(3, '0'); used.add(id);
        out.conNew.push({ id, project: proj, name: g.name, section: g.code, cur: g.cur, amount, note, places });
        g.secs.forEach((s) => setSec(s, 'contract', id));
      }
    });
    autoCons.filter((c) => !used.has(c.id) && (c.amount || 0) !== 0).forEach((c) => {
      out.conUpd.push({ c, set: { amount: 0, note: str(c.note).replace(/ \(разделы сняты\)$/, '') + ' (разделы сняты)' }, why: `${c.id} ${c.name} · ${c.section}: разделов в договоре не осталось, сумма ${fMoney(c.amount, curOf(c))} → 0` });
      if (isNum(c.paid) && c.paid > 0) out.warn.push(`${c.id} ${c.name}: уже оплачено ${fMoney(c.paid, curOf(c))}, а разделов в договоре не осталось — переплата, решите вручную`);
    });
    // which composition rows change their links
    out.secChanges = [...out.sec.entries()].filter(([id, v]) => { const s = rows.find((r) => r.id === id); return s && (('task' in v && str(v.task) !== str(s.task ?? '')) || ('contract' in v && str(v.contract) !== str(s.contract ?? ''))); });
    out.count = out.taskNew.length + out.taskUpd.length + out.conNew.length + out.conUpd.length;
    return out;
  }
  function syncInput(plan, tasks, contracts, people) {
    return { plan, tasks, contracts, people, sched: S.d.sched ? S.d.sched.byId : null, rate: S.d.rate || S.d.home?.rate || null };
  }
  // contracts take part only for viewers with access to finance; others get tasks only
  const liveSync = (proj) => (S.d.plan && S.d.tasks && S.d.people ? planSync(proj, syncInput(S.d.plan, S.d.tasks, S.d.features?.finance ? S.d.contracts || [] : null, S.d.people)) : null);

  // The diff is recalculated on fresh data and sent in one request; the server checks every item
  // belongs to this project, assigns real task numbers / contract IDs and links them back into the plan.
  async function applySync(proj, onStep) {
    onStep('Проверяю свежие данные…');
    await refreshAll();
    const P = liveSync(proj); if (!P) throw userErr('Данные ещё загружаются.');
    onStep('Записываю…');
    await apiFetch(API.sync, {
      project: proj,
      taskNew: P.taskNew.map((t) => ({ id: t.id, assignee: t.assignee, task: t.task, days: t.days, amount: t.amount, section: t.section, comment: t.comment })),
      taskUpd: P.taskUpd.map((u) => ({ id: u.t.id, set: u.set })),
      conNew: P.conNew.map((c) => ({ id: c.id, name: c.name, section: c.section, cur: c.cur, amount: c.amount, note: c.note })),
      conUpd: P.conUpd.map((u) => ({ id: u.c.id, set: u.set })),
      sec: P.secChanges,
    });
    return P;
  }

  function openSync(proj) {
    if (!S.mcp) return toast('Сервер недоступен.');
    const P = liveSync(proj); if (!P) return toast('Данные ещё загружаются.');
    modal(`Задачи и договоры · ${proj}`, (m, close) => {
      const sec = (title, items, cls) => { if (!items.length) return null; const d = el('div', 'sy-sec'); d.append(el('h4', null, `${title} · ${items.length}`)); const ul = el('ul', 'sy-list' + (cls ? ' ' + cls : '')); items.forEach((t) => ul.append(el('li', null, t))); d.append(ul); return d; };
      const parts = [
        sec('Новые задачи (черновики — ждут ТЗ)', P.taskNew.map((t) => `№${t.id} ${t.assignee}: ${t.task}${t.days !== '' ? ` · план ${t.planned ? 'с ' + fD(t.planned) + ', ' : ''}${t.days} дн.` : ' · срок появится после переноса в график'}${t.amount !== '' ? ' · ' + fNum(t.amount) + ' сум' : ''}`)),
        sec('Изменения задач', P.taskUpd.map((u) => u.why)),
        sec('Новые договоры', P.conNew.map((c) => `${c.id} ${c.name} · ${c.section} · ${fMoney(c.amount, c.cur)} · ${c.places.join(', ')}`)),
        sec('Изменения договоров', P.conUpd.map((u) => u.why)),
        sec('Проверьте', P.warn, 'warn'),
        sec('Для сведения', P.info, 'muted'),
      ].filter(Boolean);
      if (!P.count && !P.secChanges.length) parts.unshift(el('p', 'note', 'Всё уже совпадает: у каждого раздела с исполнителем есть задача, договоры соответствуют составу.'));
      const dNew = d3.sum(P.conNew.filter((c) => c.cur === 'USD'), (c) => c.amount) + d3.sum(P.conUpd.filter((u) => 'amount' in u.set && curOf(u.c) === 'USD'), (u) => u.set.amount - (u.c.amount || 0));
      if (P.conNew.length || P.conUpd.some((u) => 'amount' in u.set)) parts.unshift(el('div', 'confirm', `Долг исполнителям по проекту изменится на ${dNew >= 0 ? '+' : '−'}${fUsd(Math.abs(dNew))}` + (P.conNew.some((c) => c.cur === 'сум') || P.conUpd.some((u) => curOf(u.c) === 'сум') ? ' (и суммы в сумах)' : '') + '. Это сразу попадёт в «Сводку» и прогноз прибыли на «Главной».'));
      const body = el('div', 'sy-body'); body.append(...parts); m.append(body);
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); const cancel = el('button', 'btn ghost', 'Закрыть'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const go = el('button', 'btn primary', 'Применить'); go.type = 'button'; go.disabled = !P.count && !P.secChanges.length; foot.append(err, cancel, go); m.append(foot);
      go.addEventListener('click', async () => {
        go.disabled = true; err.textContent = '';
        try { const R = await applySync(proj, (t) => { go.textContent = t; }); toast(`Готово: задач новых ${R.taskNew.length}, изменено ${R.taskUpd.length}; договоров новых ${R.conNew.length}, изменено ${R.conUpd.length}`); close(); refreshAll(); }
        catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); go.disabled = false; go.textContent = 'Применить'; }
      });
    });
  }

  // ---------- KANBAN (стиль «табло»: срезы сверху, шкала выполнения слева, колонки по статусам)
  const KB_COLS = [
    { key: 'new', title: 'Новые', statuses: ['Черновик', 'Новая', 'На согласовании'], drop: 'Новая' },
    { key: 'work', title: 'В работе', statuses: ['В работе', 'Есть вопрос', 'На доработке', 'Согласование'], drop: 'В работе' },
    { key: 'review', title: 'На проверке', statuses: ['На проверке'], drop: 'На проверке' },
    { key: 'done', title: 'Принято', statuses: ['Принята'], drop: 'Принята' },
  ];
  const KB_PRIO = [[1, 'Высокий'], [2, 'Средний'], [3, 'Низкий']];
  const KB_TIME = ['Просрочено', 'Эта неделя', 'Позже', 'Без срока'];
  const kbTime = (t) => { if (!t.plan) return 'Без срока'; if (overdue(t)) return 'Просрочено'; const d = (parseD(t.plan) - today()) / DAY; return d <= 7 ? 'Эта неделя' : 'Позже'; };
  const kbPrio = (t) => (t.priority === 1 || t.priority === 3 ? t.priority : 2);
  const kbShort = (n) => { const p = str(n).split(/\s+/); return p.length > 1 ? `${p[0]} ${p[1][0]}.` : str(n); };
  const kbStatusOf = (t) => (S.kb.over.has(t.id) ? S.kb.over.get(t.id) : t.status);
  const KB_FUNNEL = '<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><path d="M1.5 2h11l-4.2 5.2V12l-2.6 1.5V7.2z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/><path d="M11 9.5l3.5 3.5M14.5 9.5L11 13" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>';

  function kbBase() {
    // all tasks after the page-wide filters, without cancelled ones; accepted only for the last 30 days unless asked
    const lim = new Date(today().getTime() - 30 * DAY);
    return fTasks().filter((t) => { const st = kbStatusOf(t); if (st === 'Отменена' || isProjectTask(t)) return false; if (st === 'Принята' && !S.kb.oldDone && t.finished && parseD(t.finished) < lim) return false; return true; });
  }
  function kbPass(t, skip) {
    const f = S.kb.f;
    if (skip !== 'prio' && f.prio.size && !f.prio.has(kbPrio(t))) return false;
    if (skip !== 'proj' && f.proj.size && !f.proj.has(t.dept || '—')) return false;
    if (skip !== 'time' && f.time.size && !f.time.has(kbTime(t))) return false;
    if (skip !== 'who' && f.who.size && !f.who.has(t.assignee || '—')) return false;
    return true;
  }
  function renderNS() {
    const board = $('#kb-board'), sl = $('#kb-slicers');
    if (!S.d.tasks) { if (status('tasks') === 'error') failIn(board, 'tasks'); else skel(board, 260); return; }
    // drop optimistic overrides once the sheet caught up
    S.kb.over.forEach((st, id) => { const t = S.d.tasks.find((x) => x.id === id); if (!t || t.status === st) S.kb.over.delete(id); });
    const base = kbBase();
    // slicers: options come from the data; an option with no matching cards (given the other slicers) is dimmed, as in Excel
    const groups = [
      ['prio', 'Приоритет', KB_PRIO.map(([v, l]) => [v, l])],
      ['proj', 'Отдел', [...new Set(base.map((t) => t.dept || '—'))].sort((a, b) => a.localeCompare(b, 'ru')).map((p) => [p, p])],
      ['time', 'Срок', KB_TIME.map((x) => [x, x])],
      ['who', 'Исполнитель', [...new Set(base.map((t) => t.assignee || '—'))].sort((a, b) => a.localeCompare(b, 'ru')).map((p) => [p, kbShort(p)])],
    ];
    sl.replaceChildren(...groups.map(([key, title, opts]) => {
      const box = el('div', 'kb-slicer kb-s-' + key); const hd = el('div', 'kb-s-head'); hd.append(el('span', null, title));
      const clr = el('button', 'kb-clear'); clr.type = 'button'; clr.title = 'Сбросить срез'; clr.setAttribute('aria-label', 'Сбросить срез «' + title + '»'); clr.innerHTML = KB_FUNNEL; clr.disabled = !S.kb.f[key].size;
      clr.addEventListener('click', () => { S.kb.f[key].clear(); renderNS(); }); hd.append(clr); box.append(hd);
      const list = el('div', 'kb-opts');
      const avail = new Set(base.filter((t) => kbPass(t, key)).map((t) => (key === 'prio' ? kbPrio(t) : key === 'proj' ? t.dept || '—' : key === 'time' ? kbTime(t) : t.assignee || '—')));
      opts.forEach(([v, lab]) => {
        const b = el('button', 'kb-opt'); b.type = 'button'; b.textContent = lab; b.title = String(v);
        const on = S.kb.f[key].has(v); b.setAttribute('aria-pressed', String(on)); if (!avail.has(v) && !on) b.classList.add('dim');
        b.addEventListener('click', (e) => { const set = S.kb.f[key]; if (e.ctrlKey || e.metaKey || S.kb.multi) { if (set.has(v)) set.delete(v); else set.add(v); } else if (set.size === 1 && set.has(v)) set.clear(); else { set.clear(); set.add(v); } renderNS(); });
        list.append(b);
      });
      box.append(list); return box;
    }));
    $('#kb-multi').setAttribute('aria-pressed', String(S.kb.multi));
    const shown = base.filter((t) => kbPass(t));
    // progress gauge
    const done = shown.filter((t) => kbStatusOf(t) === 'Принята').length; const pct = shown.length ? done / shown.length : 0;
    $('#kb-fill').style.height = Math.round(pct * 100) + '%'; $('#kb-pct').textContent = Math.round(pct * 100) + '%';
    $('#kb-gauge-note').textContent = `${done} из ${shown.length} ${plural(shown.length, 'задачи', 'задач', 'задач')} принято`;
    $('#kb-old').checked = S.kb.oldDone;
    // columns
    board.replaceChildren(...KB_COLS.map((c) => {
      const col = el('section', 'kb-col'); col.dataset.col = c.key;
      const cards = shown.filter((t) => c.statuses.includes(kbStatusOf(t))).sort((a, b) => kbPrio(a) - kbPrio(b) || ((a.plan || '9') < (b.plan || '9') ? -1 : 1));
      const hd = el('div', 'kb-head'); hd.append(el('span', null, c.title), el('span', 'kb-n', String(cards.length))); col.append(hd);
      const list = el('div', 'kb-list'); list.dataset.col = c.key;
      cards.forEach((t) => list.append(kbCard(t)));
      if (!cards.length) list.append(el('div', 'kb-empty', c.key === 'new' ? 'Новых задач нет' : 'Пусто'));
      if (!isBoss()) { col.append(list); return col; }
      list.addEventListener('dragover', (e) => { if (!S.kb.drag) return; e.preventDefault(); e.dataTransfer.dropEffect = 'move'; list.classList.add('over'); });
      list.addEventListener('dragleave', (e) => { if (!list.contains(e.relatedTarget)) list.classList.remove('over'); });
      list.addEventListener('drop', (e) => { e.preventDefault(); list.classList.remove('over'); const id = Number(e.dataTransfer.getData('text/plain')); S.kb.drag = null; const t = (S.d.tasks || []).find((x) => x.id === id); if (t) kbMove(t, c); });
      col.append(list); return col;
    }));
    { const nf0 = S.kb.f.prio.size + S.kb.f.proj.size + S.kb.f.time.size + S.kb.f.who.size; $('#kb-filt').textContent = nf0 ? `Фильтры · ${nf0}` : 'Фильтры'; }
    $('#kb-count').textContent = `${shown.length} ${plural(shown.length, 'задача', 'задачи', 'задач')} · принято ${Math.round(pct * 100)}%` + (S.kb.f.prio.size + S.kb.f.proj.size + S.kb.f.time.size + S.kb.f.who.size ? ' (с фильтрами)' : '');
  }
  function kbCard(t) {
    const st = kbStatusOf(t); const p = kbPrio(t);
    const c = el('article', 'kb-card p' + p); c.draggable = isBoss(); c.tabIndex = 0; c.dataset.id = t.id;
    c.setAttribute('aria-label', `Задача №${t.id}: ${t.task || ''}, ${t.assignee || ''}, ${st}`);
    c.append(el('div', 'kb-t', t.task || '—'), el('div', 'kb-a', t.assignee || '—'));
    const meta = [t.project || '', t.plan ? 'до ' + fD(t.plan).slice(0, 5) : 'без срока'].filter(Boolean).join(' · ');
    c.append(el('div', 'kb-m', meta));
    if (st !== 'Принята' && st !== 'Новая') { const bar = el('div', 'kb-bar'); const f = el('i'); f.style.width = Math.round(Math.max(0, Math.min(1, t.done || 0)) * 100) + '%'; bar.append(f); c.append(bar); }
    const tags = el('div', 'kb-tags');
    const pr = problem(t); if (pr && st !== 'Принята' && pr.key <= 5) tags.append(el('span', 'kb-tag ' + pr.cls, pr.text));
    if (st === 'На доработке') tags.append(el('span', 'kb-tag warn', 'доработка' + (t.reworks > 1 ? ' ×' + t.reworks : '')));
    if (st === 'Есть вопрос' && !(pr && pr.text === 'Есть вопрос')) tags.append(el('span', 'kb-tag warn', 'есть вопрос'));
    if (st === 'Принята' && isNum(t.points)) tags.append(el('span', 'kb-tag', 'KPI ' + fNum(t.points)));
    tags.append(el('span', 'kb-id', '№' + t.id));
    c.append(tags);
    c.addEventListener('dragstart', (e) => { S.kb.drag = t.id; e.dataTransfer.setData('text/plain', String(t.id)); e.dataTransfer.effectAllowed = 'move'; c.classList.add('drag'); });
    c.addEventListener('dragend', () => { S.kb.drag = null; c.classList.remove('drag'); $$('.kb-list.over').forEach((x) => x.classList.remove('over')); });
    c.addEventListener('click', () => openTaskCard(t.id));
    c.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') openTaskCard(t.id);
      if (isBoss() && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) { const i = KB_COLS.findIndex((x) => x.statuses.includes(kbStatusOf(t))); const n = KB_COLS[i + (e.key === 'ArrowRight' ? 1 : -1)]; if (n) kbMove(t, n); }
    });
    return c;
  }
  async function kbMove(t, col) {
    const from = kbStatusOf(t); if (col.statuses.includes(from)) return;
    if (!S.mcp) return toast('Сервер недоступен.');
    // optimistic: show the card in the new column; the server decides the exact status (review → work = доработка)
    S.kb.over.set(t.id, col.key === 'work' && from === 'На проверке' ? 'На доработке' : col.drop); renderNS();
    try {
      const r = await taskAction(t, 'move', { col: col.key });
      S.kb.over.set(t.id, r.status); toast(`№${t.id}: ${from} → ${r.status}`); refreshAll();
    } catch (e) { S.kb.over.delete(t.id); renderNS(); toast(errText(e)); }
  }

  // =====================================================================
  // WORKFLOW: роли, действия, подтверждения ГИПа, этапы раздела, отчёты
  // =====================================================================
  const STAGE_DEF = [
    { name: 'Проектирование', w: 70, days: null, role: 'Специалист', order: 1 },
    { name: 'Смета', w: 10, days: 5, role: 'Сметчик', order: 2 },
    { name: 'Оформление', w: 15, days: 3, role: 'Оформитель', order: 3 },
    { name: 'Печать', w: 5, days: 1, role: 'Печать', order: 4 },
  ];
  const STAGE_COL = { 'Проектирование': 'work', 'Смета': 'smeta', 'Оформление': 'form', 'Печать': 'print' };
  const STAGE_CLR = { 'Смета': 'var(--st-smeta)', 'Оформление': 'var(--st-form)', 'Печать': 'var(--st-print)' };
  const PK_COLS = [
    { key: 'draft', title: 'Черновик', hint: 'ждут ТЗ от ГИПа' },
    { key: 'tz', title: 'ТЗ выдано', hint: 'исполнитель принимает' },
    { key: 'work', title: 'В работе', hint: 'проектирование' },
    { key: 'appr', title: 'Согласование', hint: 'у ГИПа или заказчика' },
    { key: 'smeta', title: 'Смета', hint: 'задание сметчику' },
    { key: 'form', title: 'Оформление', hint: 'оформители' },
    { key: 'print', title: 'Печать', hint: 'распечатка и выдача' },
    { key: 'closed', title: 'Закрыт', hint: 'выдано' },
  ];
  const APPROVER_ST = ['На согласовании', 'Согласование', 'На проверке', 'Есть вопрос'];
  const DEPTS = ['Кадры', 'Админ', 'Бухгалтерия', 'Прочее'];
  const DEPT_ROLE = { 'Кадры': 'Кадры', 'Админ': 'Админ', 'Бухгалтерия': 'Бухгалтер' };
  const ALL_PAGES = ['work', 'home', 'kanban', 'tasks', 'comp', 'plan', 'gantt', 'team', 'kpi', 'money', 'contracts'];
  const ROLE_PAGES = {
    'Руководитель': ALL_PAGES,
    'ГИП': ['work', 'kanban', 'tasks', 'comp', 'plan', 'gantt', 'team', 'kpi'],
    'Бухгалтер': ['work', 'kanban', 'money', 'contracts', 'kpi'],
    'Кадры': ['work', 'kanban', 'kpi'],
    'Админ': ['work', 'kanban', 'kpi'],
  };
  const SPEC_PAGES = ['work', 'kanban', 'plan', 'kpi'];
  const PAGE_NAMES = { work: 'Моя работа', home: 'Главная', kanban: 'Канбан', tasks: 'Задачи', comp: 'Состав проекта', plan: 'График проекта', gantt: 'Ганта задач', team: 'Сотрудники', kpi: 'KPI', money: 'Финансы', contracts: 'Договоры' };
  const PAGE_ALIAS = { 'моя работа': 'work', 'главная': 'home', 'канбан': 'kanban', 'задачи': 'tasks', 'состав': 'comp', 'состав проекта': 'comp', 'график': 'plan', 'график проекта': 'plan', 'ганта': 'gantt', 'ганта задач': 'gantt', 'сотрудники': 'team', 'kpi': 'kpi', 'финансы': 'money', 'договоры': 'contracts' };

  // ---- who is looking
  // the platform maps the logged-in user's role (admin/manager → Руководитель, gip → ГИП, …)
  function resolveMe() {
    if (S.payload) S.me = S.payload.viewer;
  }
  const viewer = () => S.as || S.me || { role: null, unknown: true };
  const isBoss = () => viewer().role === 'Руководитель';
  const isGip = () => viewer().role === 'ГИП';
  const isMgr = () => isBoss() || isGip();
  // the server sends finance data only to admin/manager/finance roles
  const canFinance = () => !!S.d.features?.finance && (isBoss() || viewer().role === 'Бухгалтер');
  const inMyProjects = (p) => { const v = viewer(); return v.role === 'Руководитель' || !(v.projects || []).length || v.projects.includes(p); };
  const isProjectTask = (t) => t.flow === 'Проект' || isNum(t.section);
  const stageOf = (t) => t.stage || 'Проектирование';
  const isMine = (t) => !!viewer().person && t.assignee === viewer().person;
  // the server knows who really approves (task reviewer, creator of a non-standard task…);
  // the role rule is only used while looking "as" someone else
  const canApprove = (t) => (S.as ? isBoss() || (isGip() && isProjectTask(t) && inMyProjects(t.project)) : !!t.canApprove);
  function allowedPages() {
    const v = viewer(); if (v.unknown) return [];
    const on = (p) => !PAGE_FEATURE[p] || !!S.d.features?.[PAGE_FEATURE[p]];
    if (v.pages && v.pages.length) return ['work', ...v.pages.filter((p) => p !== 'work' && on(p))];
    return (ROLE_PAGES[v.role] || SPEC_PAGES).filter(on);
  }
  function actorName() { const me = S.me?.person || (S.me?.owner ? 'Руководитель' : 'Сайт'); return S.as ? `${me} за ${S.as.person || S.as.role}` : me; }

  // ---- configuration from the sheets
  function stageCfg() {
    const rows = S.d.stages || [];
    return STAGE_DEF.map((d) => { const r = rows.find((x) => x.name === d.name); return r ? { ...d, w: isNum(r.w) ? r.w : d.w, days: isNum(r.days) ? r.days : d.days, role: r.role || d.role, order: isNum(r.order) ? r.order : d.order } : d; }).sort((a, b) => a.order - b.order);
  }
  const discNeedsSmeta = (code) => { const d = (S.d.disc || []).find((x) => x.code === str(code)); return !d || str(d.smeta) !== 'Нет'; };
  const stagesFor = (sec) => stageCfg().filter((s) => s.name !== 'Смета' || discNeedsSmeta(sec.code));
  // stage roles (Сметчик, Оформитель, Печать) are set per employee in the admin: «Employee settings»
  const peopleForRole = (role) => (S.d.people || []).filter((p) => p.stageRole === role).map((p) => p.name);
  const allPeopleNames = () => [...new Set([...(S.d.people || []).filter((p) => !/^(Заказчик|Партнёр)$/.test(p.role || '')).map((p) => p.name), ...(S.d.access || []).map((r) => r.person).filter(Boolean)])].sort((a, b) => a.localeCompare(b, 'ru'));

  // ---- daily reports
  const todayIso = () => iso(today());
  const logsOf = (id) => (S.d.progress || []).filter((r) => r.task_id === id);
  const isStatusLog = (r) => str(r.comment).startsWith('▶');
  const reportedToday = (t) => logsOf(t.id).some((r) => r.date === todayIso() && !isStatusLog(r));
  const needsReport = (t) => ACTIVE.includes(t.status) && !!t.start && t.start < todayIso() && S.d.cal.isWork(dn(todayIso()));
  function lastLogText(t, prefix) {
    const l = logsOf(t.id).filter((r) => str(r.comment).startsWith('▶ ' + prefix)).pop(); if (!l) return '';
    return str(l.comment).replace(/^▶ [^:]+:\s*/, '').replace(/\s·\s[^·]+$/, '');
  }
  function missedReports(t, untilIso) {
    if (!t.start) return 0;
    const end = untilIso || t.finished || todayIso(); const logs = logsOf(t.id).slice().sort((a, b) => str(a.date).localeCompare(str(b.date)));
    const rep = new Set(logs.filter((r) => !isStatusLog(r)).map((r) => r.date));
    const sts = logs.filter(isStatusLog).map((r) => ({ d: r.date, s: str(r.comment).slice(2).split(/[:·]/)[0].trim() }));
    let miss = 0; const cal = S.d.cal;
    for (let n = dn(t.start) + 1; n < dn(end); n++) {
      if (!cal.isWork(n)) continue; const di = dIso(n);
      let st = 'В работе'; for (const x of sts) { if (x.d <= di) st = x.s; else break; }
      if (ACTIVE.includes(st) && !rep.has(di)) miss++;
    }
    return miss;
  }
  function daysLeft(t) { if (!t.plan) return null; return Math.round((parseD(t.plan) - today()) / DAY); }

  // ---- section (раздел) state across stages
  function secState(sec, tasks = S.d.tasks || []) {
    const stages = stagesFor(sec);
    const ts = tasks.filter((t) => t.section === sec.id && t.status !== 'Отменена');
    const byStage = {}; ts.forEach((t) => { const s = stageOf(t); if (!byStage[s] || t.id > byStage[s].id) byStage[s] = t; });
    const W = d3.sum(stages, (s) => s.w) || 1;
    const prog = (s) => { const t = byStage[s.name]; if (!t) return 0; if (t.status === 'Принята') return 1; if (['Черновик', 'Новая', 'На согласовании'].includes(t.status)) return 0; return Math.max(0, Math.min(1, t.done || 0)); };
    const res = { stages, byStage, cur: null, col: 'draft', pending: null, closed: false, pct: d3.sum(stages, (s) => s.w * prog(s)) / W };
    if (sec.closed) return { ...res, col: 'closed', closed: true, pct: 1 };
    let li = -1; stages.forEach((s, i) => { if (byStage[s.name]) li = i; });
    if (li < 0) return res;
    const t = byStage[stages[li].name]; const sn = stages[li].name;
    if (t.status !== 'Принята') {
      res.cur = t;
      res.col = sn !== 'Проектирование' ? STAGE_COL[sn] : t.status === 'Черновик' ? 'draft' : ['Новая', 'На согласовании'].includes(t.status) ? 'tz' : t.status === 'Согласование' ? 'appr' : 'work';
      return res;
    }
    const next = stages[li + 1];
    if (!next) return { ...res, col: 'closed', closed: true, pct: 1, last: t };
    return { ...res, col: STAGE_COL[next.name], pending: next.name, last: t };
  }
  const objOfSec = (sec) => (S.d.plan || []).find((x) => x.project === sec.project && x.kind === 'Объект' && str(x.wbs) && str(sec.wbs).startsWith(str(x.wbs) + '.'));
  const secLabel = (sec) => `${sec.code ? sec.code + ' · ' : ''}${sec.name || ''}${objOfSec(sec) ? ' · ' + objOfSec(sec).name : ''}`;
  const projectSections = (proj) => (S.d.plan || []).filter((r) => r.project === proj && isSection(r)).sort((a, b) => wbsCmp(a.wbs, b.wbs) || a.id - b.id);


  // ---- small form dialog that resolves to values or null
  function ask(title, fields, okLabel = 'Готово', intro) {
    return new Promise((resolve) => {
      let done = false;
      const close = modal(title, (m, closeIt) => {
        if (intro) m.append(el('p', 'note', intro));
        const form = el('div', 'form'); const ctl = {};
        fields.forEach((f) => {
          let c;
          if (f.type === 'textarea') { c = el('textarea', 'ctl'); c.value = f.value ?? ''; if (f.placeholder) c.placeholder = f.placeholder; }
          else if (f.type === 'select') { c = select('ask-' + f.k, f.opts, f.value ?? ''); }
          else if (f.type === 'check') { c = el('input'); c.type = 'checkbox'; c.checked = !!f.value; }
          else { c = input('ask-' + f.k, f.type || 'text', f.value ?? '', { autocomplete: 'off', ...(f.attrs || {}) }); }
          c.id = 'ask-' + f.k; ctl[f.k] = c;
          if (f.type === 'check') { const l = el('label', 'tp-item full'); l.append(c, el('span', null, f.label)); form.append(l); }
          else form.append(field(f.label, c, f.full === false ? null : 'full'));
          if (f.help) form.append(el('p', 'note full', f.help));
        });
        m.append(form);
        const foot = el('div', 'modal-foot'); const err = el('span', 'err'); const cancel = el('button', 'btn ghost', 'Отмена'); cancel.type = 'button';
        const ok = el('button', 'btn primary', okLabel); ok.type = 'button'; foot.append(err, cancel, ok); m.append(foot);
        cancel.addEventListener('click', () => { closeIt(); });
        const submit = () => {
          const v = {}; for (const f of fields) { const c = ctl[f.k]; v[f.k] = f.type === 'check' ? c.checked : str(c.value); if (f.req && !v[f.k]) { err.textContent = `Заполните: ${f.label.toLowerCase()}.`; c.focus(); return; } if (f.type === 'number' && v[f.k] !== '' && !(Number(v[f.k]) >= (f.min ?? 0))) { err.textContent = `${f.label}: число от ${f.min ?? 0}.`; return; } }
          done = true; closeIt(); resolve(v);
        };
        ok.addEventListener('click', submit);
        m.addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target.tagName === 'INPUT') submit(); });
      });
      const root = $('#modal-root'); const obs = new MutationObserver(() => { if (!root.children.length) { obs.disconnect(); if (!done) resolve(null); } }); obs.observe(root, { childList: true });
      void close;
    });
  }

  // ---- what can the viewer do with this task
  function actionsFor(t) {
    const out = []; const st = t.status; const mine = isMine(t); const ap = canApprove(t);
    if (mine) {
      if (st === 'Новая') { if (isNum(t.days) && t.days > 0) out.push({ k: 'accept', label: `Принять · ${t.days} дн.`, primary: true }); out.push({ k: 'accept_own', label: isNum(t.days) && t.days > 0 ? 'Мне нужен другой срок' : 'Принять и назвать срок', primary: !(isNum(t.days) && t.days > 0) }); }
      if (st === 'В работе' || st === 'На доработке') out.push({ k: 'submit', label: 'Сдать работу', primary: true }, { k: 'to_appr', label: 'На согласование' }, { k: 'question', label: 'Есть вопрос' });
    }
    if (ap) {
      if (st === 'Черновик') out.push({ k: 'issue_tz', label: 'Выдать ТЗ', primary: true });
      if (st === 'На согласовании') out.push({ k: 'approve_days', label: `Утвердить срок · ${t.days ?? '—'} дн.`, primary: true }, { k: 'change_days', label: 'Другой срок' }, { k: 'reject_days', label: 'Не утверждать' });
      if (st === 'Согласование') { out.push({ k: 'appr_ok', label: 'Согласовано', primary: true }, { k: 'appr_remarks', label: 'Есть замечания' }); if (t.approver !== 'Заказчик') out.push({ k: 'appr_client', label: 'Беру на согласование с заказчиком' }); }
      if (st === 'Есть вопрос') out.push({ k: 'answer', label: 'Ответить', primary: true });
      if (st === 'На проверке') out.push({ k: 'review_ok', label: 'Принять работу', primary: true }, { k: 'review_back', label: 'Вернуть на доработку', danger: true });
    }
    return out;
  }
  function nextStepText(t) {
    const st = t.status; const days = daysLeft(t);
    if (st === 'Черновик') return 'Ждёт ТЗ от ГИПа. Это план: работа ещё не началась.';
    if (st === 'Новая') return isNum(t.days) && t.days > 0 ? `ТЗ выдано. Примите задачу: срок ${t.days} дн. с момента принятия.` : 'ТЗ выдано. Примите задачу и назовите свой срок.';
    if (st === 'На согласовании') return `Вы предложили срок ${t.days ?? '—'} дн. Ждёт подтверждения ГИПа.`;
    if (st === 'Согласование') return t.approver === 'Заказчик' ? 'На согласовании у заказчика (ведёт ГИП). Срок на паузе.' : 'На согласовании у ГИПа. Срок на паузе.';
    if (st === 'Есть вопрос') return 'Вопрос отправлен ГИПу. Работайте дальше, ответ придёт сюда.';
    if (st === 'На проверке') return 'Работа сдана. Ждёт приёмки ГИПом.';
    if (st === 'На доработке') return 'Вернули на доработку. Исправьте и сдайте снова.';
    if (st === 'В работе') return days == null ? 'В работе.' : days < 0 ? `Просрочено на ${-days} дн. Сдайте как можно скорее.` : days === 0 ? 'Сдать сегодня.' : `До сдачи ${days} дн. Каждый день отмечайте процент.`;
    if (st === 'Принята') return 'Принято.';
    return '';
  }

  // The dialogs collect the input; the server checks role and current status,
  // changes the task, writes the history line and notifies the other side.
  const ASK = {
    accept_own: (t) => ask('Сколько дней нужно?', [{ k: 'days', label: 'Срок, дней', type: 'number', value: t.days ?? '', req: true, min: 1, full: false, attrs: { min: 1, step: 1 } }, { k: 'note', label: 'Комментарий (необязательно)', type: 'textarea' }], 'Отправить ГИПу', 'ГИП подтвердит срок. После подтверждения отсчёт начнётся с этого дня.'),
    submit: () => ask('Сдать работу ГИПу', [{ k: 'src', label: 'Исходники (DWG и пр.) переданы', type: 'check', value: true }, { k: 'note', label: 'Комментарий (необязательно)', type: 'textarea', placeholder: 'Что сделано, где лежат файлы' }], 'Сдать'),
    to_appr: () => ask('Что нужно согласовать?', [{ k: 'what', label: 'Что согласовать', type: 'textarea', req: true, placeholder: 'Например: планировка 2 этажа, марка оборудования' }], 'Отправить на согласование', 'Пока идёт согласование, срок стоит на паузе и не идёт вам в минус.'),
    question: () => ask('Вопрос ГИПу', [{ k: 'q', label: 'Вопрос', type: 'textarea', req: true }], 'Отправить'),
    issue_tz: (t) => ask('Выдать ТЗ', [{ k: 'tz', label: 'ТЗ: ссылка на файл или текст задания', type: 'textarea', value: t.tz || '', placeholder: 'https://drive.google.com/…  или кратко, что сделать' }, { k: 'days', label: 'Срок, дней (пусто — исполнитель назовёт сам)', type: 'number', value: t.days ?? '', full: false, attrs: { min: 1, step: 1 } }], 'Выдать ТЗ', `Исполнитель: ${t.assignee || '—'}. Он увидит задачу в «Моей работе» и примет её.`),
    change_days: (t) => ask('Утвердить другой срок', [{ k: 'days', label: 'Срок, дней', type: 'number', value: t.days ?? '', req: true, min: 1, full: false, attrs: { min: 1, step: 1 } }], 'Утвердить'),
    reject_days: () => ask('Срок не утверждён', [{ k: 'why', label: 'Почему (исполнитель увидит)', type: 'textarea', req: true }], 'Вернуть исполнителю'),
    appr_remarks: () => ask('Замечания по согласованию', [{ k: 'why', label: 'Замечания (исполнитель увидит)', type: 'textarea', req: true }], 'Вернуть в работу'),
    answer: (t) => ask('Ответ исполнителю', [{ k: 'a', label: 'Ответ', type: 'textarea', req: true }], 'Ответить', 'Вопрос: ' + (lastLogText(t, 'Есть вопрос') || '—')),
    review_back: () => ask('Вернуть на доработку', [{ k: 'why', label: 'Что исправить (исполнитель увидит)', type: 'textarea', req: true }], 'Вернуть', 'Доработка учитывается в KPI исполнителя.'),
  };
  async function runAction(t, k) {
    if (!S.mcp) return toast('Сервер недоступен.');
    let params = {};
    if (ASK[k]) { params = await ASK[k](t); if (!params) return; }
    try {
      const r = await taskAction(t, k, params);
      toast(`№${t.id}: ${r.status}`);
      await refreshAll();
      if (k === 'review_ok' && isNum(t.section)) afterAccept(t);
    } catch (e) { toast(errText(e)); refreshAll(); }
  }

  // after a stage is accepted: next stage or close the section
  function afterAccept(t) {
    const sec = (S.d.plan || []).find((r) => r.id === t.section); if (!sec) return;
    const stages = stagesFor(sec); const i = stages.findIndex((s) => s.name === stageOf(t)); const rest = stages.slice(i + 1);
    if (!rest.length) { closeSection(sec, 'все этапы приняты'); return; }
    openHandoff(sec, rest, t);
  }
  async function closeSection(sec, why) {
    try { await savePlan((rows) => { const r = rows.find((x) => x.id === sec.id); if (r) r.closed = todayIso(); return rows; }); toast(`Раздел ${sec.code || ''} закрыт: ${why}`); refreshAll(); }
    catch (e) { toast(e && e.userText ? e.userText : errText(e)); }
  }
  function openHandoff(sec, rest, prevTask) {
    const st = secState(sec); const obj = objOfSec(sec);
    modal(`Следующий этап · ${secLabel(sec)}`, (m, close) => {
      m.append(el('p', 'note', prevTask ? `«${stageOf(prevTask)}» принят. Кому передать дальше?` : 'Назначьте следующий этап.'));
      const form = el('div', 'form');
      const opts = [...rest.map((s) => new Option(`${s.name} (${s.role.toLowerCase()})`, s.name)), new Option('Закрыть раздел — дальше этапов не нужно', '__close')];
      const fStage = select('ho-stage', opts, rest[0].name);
      const fWho = el('select', 'ctl'); fWho.id = 'ho-who';
      const fDays = input('ho-days', 'number', '', { min: 1, step: 1 });
      const fNote = el('textarea', 'ctl'); fNote.id = 'ho-note'; fNote.placeholder = 'Что передаётся, где файлы (необязательно)';
      const lWho = field('Исполнитель', fWho), lDays = field('Срок, дней', fDays), lNote = field('Задание', fNote, 'full');
      form.append(field('Этап', fStage, 'full'), lWho, lDays, lNote); m.append(form);
      const fill = () => {
        const sName = fStage.value; const closing = sName === '__close'; [lWho, lDays, lNote].forEach((x) => { x.hidden = closing; }); if (closing) return;
        const cfg = rest.find((s) => s.name === sName); const byRole = peopleForRole(cfg.role);
        // who did this stage for the same object before
        const prev = (S.d.tasks || []).filter((x) => stageOf(x) === sName && x.project === sec.project && x.status !== 'Отменена' && isNum(x.section) && (() => { const s2 = (S.d.plan || []).find((r) => r.id === x.section); return s2 && objOfSec(s2)?.id === obj?.id; })()).sort((a, b) => b.id - a.id)[0];
        const g1 = el('optgroup'); g1.label = cfg.role; byRole.forEach((n) => g1.append(new Option(n, n)));
        const g2 = el('optgroup'); g2.label = 'Все'; allPeopleNames().filter((n) => !byRole.includes(n)).forEach((n) => g2.append(new Option(n, n)));
        fWho.replaceChildren(new Option('— выберите —', ''), ...(byRole.length ? [g1] : []), g2);
        fWho.value = prev?.assignee || byRole[0] || '';
        fDays.value = isNum(cfg.days) ? cfg.days : '';
      };
      fStage.addEventListener('change', fill); fill();
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); const later = el('button', 'btn ghost', 'Позже'); later.type = 'button'; later.addEventListener('click', close);
      const go = el('button', 'btn primary', 'Назначить'); go.type = 'button'; foot.append(err, later, go); m.append(foot);
      fStage.addEventListener('change', () => { go.textContent = fStage.value === '__close' ? 'Закрыть раздел' : 'Назначить'; });
      go.addEventListener('click', async () => {
        if (fStage.value === '__close') { close(); closeSection(sec, 'закрыт ГИПом'); return; }
        if (!fWho.value) { err.textContent = 'Выберите исполнителя.'; return; }
        go.disabled = true; go.textContent = 'Назначаю…';
        try {
          await addTask({ assignee: fWho.value, project: sec.project, task: `${fStage.value} — ${sec.code ? sec.code + ' ' : ''}${sec.name || ''}${obj ? ' · ' + obj.name : ''}`, type: '', priority: 2, days: fDays.value === '' ? null : Number(fDays.value), status: 'Новая', comment: `Этап проекта: ${fStage.value}${sec.doc ? ' · ' + sec.doc : ''}`, section: sec.id, flow: 'Проект', stage: fStage.value, tz: fNote.value.trim() });
          toast(`${fStage.value} → ${fWho.value}`); close(); refreshAll();
        } catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); go.disabled = false; go.textContent = 'Назначить'; }
      });
      void st;
    });
  }
  // issue ТЗ to many drafts at once
  function openBulkTz(proj) {
    const drafts = (S.d.tasks || []).filter((t) => t.project === proj && t.status === 'Черновик' && canApprove(t)).sort((a, b) => a.id - b.id);
    if (!drafts.length) return toast('Черновиков нет.');
    modal(`Выдать ТЗ · ${proj}`, (m, close) => {
      m.append(el('p', 'note', 'Отметьте разделы. Срок в днях считается с момента, когда исполнитель примет задачу; пустой срок исполнитель назовёт сам.'));
      const list = el('div', 'tp-list ob-list'); const rows = [];
      drafts.forEach((t) => { const r = el('div', 'ob-row'); r.style.gridTemplateColumns = 'auto minmax(0,1fr) 5.5rem'; const cb = el('input'); cb.type = 'checkbox'; cb.checked = true; cb.id = 'bt-' + t.id; const lab = el('label', 'ob-lab'); lab.htmlFor = cb.id; lab.append(el('b', null, '№' + t.id + ' '), document.createTextNode(`${t.task} · ${t.assignee || '—'}`)); const d = input('bt-d-' + t.id, 'number', t.days ?? '', { min: 1, step: 1, placeholder: 'дней' }); r.append(cb, lab, d); list.append(r); rows.push({ t, cb, d }); });
      const tz = el('textarea', 'ctl'); tz.id = 'bt-tz'; tz.placeholder = 'Общее ТЗ: ссылка на папку или текст (необязательно)';
      const form = el('div', 'form'); form.append(field('Общее ТЗ', tz, 'full')); m.append(list, form);
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); const cancel = el('button', 'btn ghost', 'Отмена'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const go = el('button', 'btn primary', 'Выдать ТЗ'); go.type = 'button'; foot.append(err, cancel, go); m.append(foot);
      go.addEventListener('click', async () => {
        const pick = rows.filter((x) => x.cb.checked); if (!pick.length) { err.textContent = 'Отметьте хотя бы один раздел.'; return; }
        go.disabled = true; let n = 0;
        try {
          for (const x of pick) { go.textContent = `Выдаю ${++n} из ${pick.length}…`; await taskAction(x.t, 'issue_tz', { tz: tz.value.trim() || x.t.tz || '', days: x.d.value }); }
          toast(`ТЗ выдано: ${pick.length}`); close(); refreshAll();
        } catch (e) { err.textContent = (e && e.userText ? e.userText : errText(e)) + (n > 1 ? ` Успели выдать ${n - 1}.` : ''); go.disabled = false; go.textContent = 'Выдать ТЗ'; refreshAll(); }
      });
    });
  }

  // non-standard task (кадры, админ, бухгалтерия…)
  function openNonStd(preset = {}) {
    if (!S.mcp) return toast('Сервер недоступен.');
    const tpl = (S.d.templates || []).filter((x) => x.dept && x.dept !== 'Проектирование');
    modal('Нестандартная задача', (m, close) => {
      const form = el('div', 'form');
      const fDept = select('ns-dept', DEPTS, preset.dept || 'Кадры');
      const fTpl = el('select', 'ctl'); fTpl.id = 'ns-tpl';
      const fTask = el('textarea', 'ctl'); fTask.id = 'ns-task'; fTask.placeholder = 'Что сделать';
      const fWho = el('select', 'ctl'); fWho.id = 'ns-who';
      const fDays = input('ns-days', 'number', '', { min: 1, step: 1, placeholder: 'назовёт сам' });
      const fPrio = select('ns-prio', [new Option('1 — срочно', '1'), new Option('2 — обычный', '2'), new Option('3 — когда будет время', '3')], '2');
      const fProj = select('ns-proj', [new Option('— без проекта —', 'GASTEC'), ...(S.d.projects || []).filter((p) => p.status !== 'Закрыт').map((p) => new Option(p.name, p.name))], preset.project || 'GASTEC');
      const syncDept = () => {
        const d = fDept.value; const ts = tpl.filter((x) => x.dept === d || (d === 'Прочее' && !DEPTS.includes(x.dept)));
        fTpl.replaceChildren(new Option('— своя задача —', ''), ...ts.map((x) => new Option(x.name, x.name)));
        const role = DEPT_ROLE[d]; const byRole = role ? peopleForRole(role) : [];
        const g1 = el('optgroup'); g1.label = d; byRole.forEach((n) => g1.append(new Option(n, n)));
        const g2 = el('optgroup'); g2.label = 'Все'; allPeopleNames().filter((n) => !byRole.includes(n)).forEach((n) => g2.append(new Option(n, n)));
        fWho.replaceChildren(new Option('— кому —', ''), ...(byRole.length ? [g1] : []), g2); fWho.value = byRole[0] || '';
      };
      fDept.addEventListener('change', syncDept); syncDept();
      fTpl.addEventListener('change', () => { const x = tpl.find((y) => y.name === fTpl.value); if (!x) return; if (!fTask.value.trim()) fTask.value = x.name + (x.desc ? ': ' + x.desc : ''); if (isNum(x.days)) fDays.value = x.days; });
      form.append(field('Отдел', fDept), field('Шаблон', fTpl), field('Задача', fTask, 'full'), field('Кому', fWho), field('Срок, дней', fDays), field('Приоритет', fPrio), field('Проект', fProj));
      m.append(form, el('p', 'note', 'Исполнитель увидит задачу в «Моей работе», примет её, будет отмечать процент и сдаст вам на проверку.'));
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); const cancel = el('button', 'btn ghost', 'Отмена'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const go = el('button', 'btn primary', 'Поставить'); go.type = 'button'; foot.append(err, cancel, go); m.append(foot);
      go.addEventListener('click', async () => {
        if (!fTask.value.trim()) { err.textContent = 'Напишите, что сделать.'; return; } if (!fWho.value) { err.textContent = 'Выберите, кому.'; return; }
        go.disabled = true; go.textContent = 'Ставлю…';
        try { await addTask({ task: fTask.value.trim(), assignee: fWho.value, project: fProj.value, type: fTpl.value, priority: Number(fPrio.value), days: fDays.value === '' ? null : Number(fDays.value), status: 'Новая', comment: '', flow: 'Нестандартная', dept: fDept.value }); toast('Задача поставлена: ' + fWho.value); close(); refreshAll(); }
        catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); go.disabled = false; go.textContent = 'Поставить'; }
      });
    });
  }

  // ---- task card: next step, actions, history
  function taskCardBody(t, m) {
    const box = el('div', 'tc');
    const head = el('div', 'tc-head'); head.append(statusPill(t.status));
    if (isProjectTask(t)) head.append(el('span', 'pill', stageOf(t))); else if (t.dept) head.append(el('span', 'pill', t.dept));
    const pr = problem(t); if (pr && pr.key <= 3) head.append(el('span', 'pill ' + pr.cls, pr.text));
    box.append(head, el('div', 'tc-title', t.task || '—'));
    box.append(el('div', 'note', [t.assignee || '—', t.project || '', t.plan ? 'сдать до ' + fD(t.plan) : isNum(t.days) ? `${t.days} дн. после принятия` : 'срок не назван'].filter(Boolean).join(' · ')));
    box.append(el('div', 'tc-next', nextStepText(t)));
    if (t.tz) { const z = el('div', 'tc-tz'); z.append(el('b', null, 'ТЗ: ')); if (/^https?:\/\//.test(t.tz)) { const a = el('a', null, t.tz); a.href = t.tz; a.target = '_blank'; a.rel = 'noopener'; z.append(a); } else z.append(document.createTextNode(t.tz)); box.append(z); }
    if (!['Черновик', 'Новая', 'На согласовании'].includes(t.status)) { const bar = el('div', 'track'); const f = el('div', 'fill'); f.style.width = Math.round((t.done || 0) * 100) + '%'; f.style.background = taskColor(t); bar.append(f); const r = el('div', 'prog-row'); r.append(el('span', null, 'сделано'), bar, el('span', 'num', fPct(t.done))); box.append(r); }
    const acts = actionsFor(t);
    if (acts.length) { const row = el('div', 'tc-acts'); acts.forEach((a) => { const b = el('button', 'btn ' + (a.primary ? 'primary' : a.danger ? 'danger' : '')); b.type = 'button'; b.textContent = a.label; b.addEventListener('click', () => { if (m) $('#modal-root').replaceChildren(); runAction(t, a.k); }); row.append(b); }); box.append(row); }
    const logs = logsOf(t.id).slice(-8).reverse();
    if (logs.length) { const h = el('details', 'tc-log'); h.append(el('summary', null, `История · ${logsOf(t.id).length}`)); const ul = el('ul'); logs.forEach((r) => ul.append(el('li', null, `${fD(r.date).slice(0, 5)} · ${isStatusLog(r) ? str(r.comment).slice(2) : 'отчёт ' + fPct(r.done) + (r.comment && r.comment !== 'Записано на сайте' ? ' — ' + r.comment : '')}`))); h.append(ul); box.append(h); }
    return box;
  }
  function openTaskCard(id) {
    const t = (S.d.tasks || []).find((x) => x.id === id); if (!t) return toast('Задача не найдена, обновите страницу.');
    modal(`Задача №${t.id}`, (m, close) => {
      m.append(taskCardBody(t, m));
      const foot = el('div', 'modal-foot');
      // comments and attachments live on the platform's task page
      if (t.url) { const a = el('a', 'btn ghost', 'Файлы и комментарии ↗'); a.href = t.url; a.target = '_top'; foot.append(a); }
      if (isMgr()) { const ed = el('button', 'btn ghost', 'Редактировать все поля'); ed.type = 'button'; ed.addEventListener('click', () => { close(); openTask(t.id); }); foot.append(ed); }
      const c = el('button', 'btn', 'Закрыть'); c.type = 'button'; c.addEventListener('click', close); foot.append(c); m.append(foot);
    });
  }
  function openSecCard(secId) {
    const sec = (S.d.plan || []).find((r) => r.id === secId); if (!sec) return toast('Раздел не найден, обновите страницу.');
    const st = secState(sec);
    modal(secLabel(sec), (m, close) => {
      if (sec.doc) m.append(el('div', 'mono note', sec.doc));
      const tl = el('ol', 'sc-tl');
      st.stages.forEach((s) => {
        const t = st.byStage[s.name]; const li = el('li', 'sc-st ' + (t ? (t.status === 'Принята' ? 'done' : 'on') : st.closed ? 'skip' : 'todo'));
        li.append(el('b', null, s.name), el('span', null, t ? `${t.assignee || '—'} · ${t.status}${t.status !== 'Принята' && !['Черновик', 'Новая', 'На согласовании'].includes(t.status) ? ' · ' + fPct(t.done) : ''}` : st.closed ? 'не требовался' : st.pending === s.name ? 'ждёт назначения' : '—'));
        if (t) li.addEventListener('click', () => { close(); openTaskCard(t.id); });
        tl.append(li);
      });
      m.append(tl);
      const cur = st.cur;
      if (cur) m.append(taskCardBody(cur, m));
      else if (st.pending && isMgr() && inMyProjects(sec.project)) { const b = el('button', 'btn primary', `Назначить: ${st.pending}`); b.type = 'button'; b.addEventListener('click', () => { close(); openHandoff(sec, st.stages.slice(st.stages.findIndex((x) => x.name === st.pending)), st.last); }); m.append(b); }
      else if (!cur && !st.closed) m.append(el('p', 'note', sec.owner ? 'Задача ещё не создана: нажмите «Задачи и договоры» на вкладке «Состав проекта».' : 'У раздела нет исполнителя. Назначьте его в составе проекта.'));
      const foot = el('div', 'modal-foot');
      if (isMgr()) { const ed = el('button', 'btn ghost', 'Раздел в составе'); ed.type = 'button'; ed.addEventListener('click', () => { close(); openPlan(sec.id, {}, true); }); foot.append(ed); }
      const c = el('button', 'btn', 'Закрыть'); c.type = 'button'; c.addEventListener('click', close); foot.append(c); m.append(foot);
    });
  }

  // ---- what waits for the viewer's decision
  function pendingDecisions() {
    if (!isMgr()) return [];
    const out = [];
    const tasks = (S.d.tasks || []).filter((t) => canApprove(t));
    const drafts = d3.group(tasks.filter((t) => t.status === 'Черновик'), (t) => t.project);
    drafts.forEach((list, proj) => out.push({ kind: 'drafts', proj, list, age: 0 }));
    tasks.filter((t) => APPROVER_ST.includes(t.status)).forEach((t) => {
      const l = logsOf(t.id).filter(isStatusLog).pop(); const since = l ? l.date : t.status === 'На проверке' ? t.finished || t.start : t.status === 'Согласование' ? t.apprSince || t.start : t.start || t.created; out.push({ kind: 'task', t, age: since ? Math.max(0, Math.round((today() - parseD(since)) / DAY)) : 0 });
    });
    // accepted stage, next stage not assigned
    const projs = [...new Set((S.d.plan || []).filter((r) => isSection(r)).map((r) => r.project))].filter(inMyProjects);
    projs.forEach((p) => projectSections(p).forEach((sec) => { const st = secState(sec); if (st.pending) out.push({ kind: 'handoff', sec, st, age: 0 }); }));
    return out.sort((a, b) => b.age - a.age);
  }
  function decisionText(t) {
    const st = t.status;
    if (st === 'На согласовании') return `предлагает срок ${t.days ?? '—'} дн.`;
    if (st === 'Согласование') return (t.approver === 'Заказчик' ? 'у заказчика: ' : 'просит согласовать: ') + (lastLogText(t, 'Согласование') || '—');
    if (st === 'Есть вопрос') return 'вопрос: ' + (lastLogText(t, 'Есть вопрос') || '—');
    if (st === 'На проверке') return 'сдал работу' + (t.source_ok === 'Да' ? ', исходники переданы' : ', исходники НЕ переданы');
    return st;
  }

  // ---------- «Моя работа»: одна страница со всем, что нужно сделать сегодня
  function noAccessBlock() {
    const c = el('div', 'card mw-noacc'); const v = S.me || {};
    c.append(el('h2', null, 'Нет доступа к Пульту'), el('p', null, 'У вашей учётной записи нет роли сотрудника. Попросите администратора сменить роль в разделе «Пользователи».'));
    if (v.email) { const p = el('p', 'note'); p.append(document.createTextNode('Ваш email: '), el('b', 'mono', v.email)); c.append(p); }
    return c;
  }
  function mwCard(t) {
    const pr = problem(t); const lvl = pr && pr.key <= 1 ? 'bad' : pr && pr.key <= 3 ? 'warn' : APPROVER_ST.includes(t.status) ? 'ink' : '';
    const c = el('article', 'mw-card ' + lvl);
    const top = el('button', 'mw-ctop'); top.type = 'button'; top.addEventListener('click', () => openTaskCard(t.id));
    top.append(el('span', 'mw-ctitle', t.task || '—'));
    const meta = [t.project || '', isProjectTask(t) ? stageOf(t) : t.dept || '', `№${t.id}`].filter(Boolean).join(' · ');
    top.append(el('span', 'mw-cmeta', meta)); c.append(top);
    const dl = daysLeft(t);
    const chips = el('div', 'mw-chips'); chips.append(statusPill(t.status));
    if (t.plan && !CLOSED.includes(t.status) && !['Черновик', 'Новая', 'На согласовании', 'Согласование'].includes(t.status)) chips.append(el('span', 'pill ' + (dl < 0 ? 'bad' : dl <= 1 ? 'warn' : ''), dl < 0 ? `просрочено ${-dl} дн.` : dl === 0 ? 'сдать сегодня' : `осталось ${dl} дн.`));
    if (pr && pr.key <= 3 && pr.text !== 'Просрочена') chips.append(el('span', 'pill ' + pr.cls, pr.text));
    if (ACTIVE.includes(t.status)) { const r = reportedToday(t); chips.append(el('span', 'pill ' + (r ? 'ok' : needsReport(t) ? 'warn' : ''), r ? 'отчёт есть' : 'нет отчёта')); }
    c.append(chips);
    if (!['Черновик', 'Новая', 'На согласовании'].includes(t.status) && t.status !== 'Принята') { const bar = el('div', 'mw-bar'); const f = el('i'); f.style.width = Math.round((t.done || 0) * 100) + '%'; bar.append(f); c.append(bar); }
    c.append(el('p', 'mw-next', nextStepText(t)));
    const acts = actionsFor(t);
    if (acts.length) { const row = el('div', 'mw-acts'); acts.forEach((a) => { const b = el('button', 'btn ' + (a.primary ? 'primary' : a.danger ? 'danger' : '')); b.type = 'button'; b.textContent = a.label; b.addEventListener('click', () => runAction(t, a.k)); row.append(b); }); c.append(row); }
    return c;
  }
  function reportBlock(act) {
    const card = el('section', 'card mw-report'); const allDone = act.every(reportedToday);
    const h = el('div', 'card-h'); h.append(el('h2', null, 'Отчёт за сегодня'), el('span', 'pill ' + (allDone ? 'ok' : 'warn'), allDone ? 'отправлен' : 'не отправлен')); card.append(h);
    card.append(el('p', 'note', 'Передвиньте ползунок на сколько процентов готова каждая задача и нажмите «Отправить». Даже если процент не изменился — отправьте: это и есть ежедневный отчёт.'));
    const list = el('div', 'mw-rows');
    act.forEach((t) => {
      const cur = Math.round((t.done || 0) * 100); const val = S.rep.has(t.id) ? S.rep.get(t.id) : cur;
      const r = el('div', 'mw-rrow'); const name = el('div', 'mw-rname'); name.append(el('span', null, t.task || '—'), el('span', 'note', `${t.project || ''} · было ${cur}%${reportedToday(t) ? ' · сегодня уже отмечено' : ''}`));
      const rng = el('input'); rng.type = 'range'; rng.min = 0; rng.max = 100; rng.step = 5; rng.value = val; rng.id = 'rep-' + t.id; rng.setAttribute('aria-label', `Процент: ${t.task}`);
      const out = el('output', 'mw-rval num', val + '%'); out.htmlFor = rng.id;
      rng.addEventListener('input', () => { S.rep.set(t.id, Number(rng.value)); out.textContent = rng.value + '%'; out.classList.toggle('up', Number(rng.value) > cur); });
      out.classList.toggle('up', val > cur);
      r.append(name, rng, out); list.append(r);
    });
    card.append(list);
    const note = el('input', 'ctl'); note.id = 'rep-note'; note.placeholder = 'Комментарий к отчёту (необязательно)'; note.value = S.repNote || ''; note.addEventListener('input', () => { S.repNote = note.value; });
    const send = el('button', 'btn primary mw-send', allDone ? 'Обновить отчёт' : 'Отправить отчёт'); send.type = 'button';
    const foot = el('div', 'mw-rfoot'); foot.append(note, send); card.append(foot);
    send.addEventListener('click', async () => {
      if (!S.mcp) return toast('Сервер недоступен.');
      send.disabled = true; send.textContent = 'Отправляю…';
      try {
        const items = act.map((t) => ({ id: t.id, done: S.rep.has(t.id) ? S.rep.get(t.id) : Math.round((t.done || 0) * 100) }));
        const r = await apiFetch(API.report, { items, note: S.repNote || '' }); S.rep.clear(); S.repNote = '';
        toast(`Отчёт отправлен: ${r.count} ${plural(r.count, 'задача', 'задачи', 'задач')}`); refreshAll();
      } catch (e) { toast(e && e.userText ? e.userText : errText(e)); send.disabled = false; send.textContent = 'Отправить отчёт'; }
    });
    return card;
  }
  function decisionsBlock() {
    const items = pendingDecisions(); const card = el('section', 'card mw-dec');
    const h = el('div', 'card-h'); h.append(el('h2', null, 'Ждут вашего решения'), el('span', 'pill ' + (items.length ? 'warn' : 'ok'), String(items.length))); card.append(h);
    if (!items.length) { card.append(el('p', 'note', 'Сейчас ничего не ждёт вашего решения.')); return card; }
    const ul = el('div', 'mw-dlist');
    items.forEach((it) => {
      const row = el('div', 'mw-drow'); const txt = el('div', 'mw-dtxt'); const acts = el('div', 'mw-dacts');
      if (it.kind === 'drafts') {
        txt.append(el('b', null, it.proj), document.createTextNode(` · ${it.list.length} ${plural(it.list.length, 'раздел ждёт', 'раздела ждут', 'разделов ждут')} ТЗ`));
        txt.append(el('span', 'note', it.list.slice(0, 4).map((t) => `${t.assignee || '—'}: ${t.task}`).join('; ') + (it.list.length > 4 ? '…' : '')));
        const b = el('button', 'btn primary sm', 'Выдать ТЗ'); b.type = 'button'; b.addEventListener('click', () => openBulkTz(it.proj)); acts.append(b);
      } else if (it.kind === 'handoff') {
        txt.append(el('b', null, secLabel(it.sec)), document.createTextNode(` · «${stageOf(it.st.last)}» принят`), el('span', 'note', `${it.sec.project} · дальше: ${it.pending || it.st.pending}`));
        const b = el('button', 'btn primary sm', `Назначить: ${it.st.pending}`); b.type = 'button'; b.addEventListener('click', () => openHandoff(it.sec, it.st.stages.slice(it.st.stages.findIndex((x) => x.name === it.st.pending)), it.st.last)); acts.append(b);
      } else {
        const t = it.t; const who = el('b', null, t.assignee || '—');
        const link = el('button', 'linkbtn', `№${t.id} ${t.task}`); link.type = 'button'; link.addEventListener('click', () => openTaskCard(t.id));
        txt.append(who, document.createTextNode(' · '), link, el('span', 'note', decisionText(t) + (it.age ? ` · ждёт ${it.age} дн.` : '')));
        actionsFor(t).filter((a) => !['accept', 'accept_own', 'submit', 'to_appr', 'question'].includes(a.k)).forEach((a) => { const b = el('button', 'btn sm ' + (a.primary ? 'primary' : a.danger ? 'danger' : '')); b.type = 'button'; b.textContent = a.label; b.addEventListener('click', () => runAction(t, a.k)); acts.append(b); });
      }
      row.append(txt, acts); ul.append(row);
    });
    card.append(ul); return card;
  }
  function missingBlock() {
    const miss = (S.d.tasks || []).filter((t) => canApprove(t) && needsReport(t) && !reportedToday(t));
    const byWho = d3.groups(miss, (t) => t.assignee || '—').sort((a, b) => b[1].length - a[1].length);
    const card = el('section', 'card mw-miss');
    const h = el('div', 'card-h'); h.append(el('h2', null, 'Нет отчёта за сегодня'), el('span', 'pill ' + (byWho.length ? 'warn' : 'ok'), byWho.length ? `${byWho.length} чел.` : 'все отчитались')); card.append(h);
    if (!S.d.cal.isWork(dn(todayIso()))) { card.append(el('p', 'note', 'Сегодня выходной, отчёт не нужен.')); return card; }
    if (!byWho.length) { card.append(el('p', 'note', 'Все, у кого есть задачи в работе, отметили процент.')); return card; }
    const ul = el('div', 'tm-names'); byWho.forEach(([n, list]) => { const b = el('button', null, n); b.type = 'button'; b.title = list.map((t) => t.task).join('\n'); b.append(el('span', null, String(list.length))); b.addEventListener('click', () => openTaskCard(list[0].id)); ul.append(b); });
    card.append(ul, el('p', 'note', 'Пропуски считаются автоматически и попадают в KPI при приёмке работы.'));
    return card;
  }
  function renderWork() {
    const box = $('#mw'); const v = viewer();
    if (!S.payload) { if (S.load === 'error') failIn(box); else skel(box, 260); return; }
    if (v.unknown) { box.replaceChildren(noAccessBlock()); return; }
    if (!S.d.tasks || !S.d.progress) { if (status('tasks') === 'error') failIn(box, 'tasks'); else skel(box, 260); return; }
    const parts = []; const me = v.person;
    const hello = el('div', 'mw-hello'); hello.append(el('h2', null, me || 'Моя работа'), el('p', 'note', [v.role, (v.projects || []).length ? v.projects.join(', ') : '', new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })].filter(Boolean).join(' · ')));
    parts.push(hello);
    if (isMgr()) parts.push(decisionsBlock());
    if (me) {
      const mine = (S.d.tasks || []).filter((t) => t.assignee === me && t.status !== 'Отменена');
      const act = mine.filter((t) => ACTIVE.includes(t.status));
      if (act.length) parts.push(reportBlock(act));
      const lim = new Date(today().getTime() - 14 * DAY);
      const groups = [
        ['Нужно ваше действие', mine.filter((t) => t.status === 'Новая' || t.status === 'На доработке'), true],
        ['В работе', mine.filter((t) => t.status === 'В работе'), true],
        ['Ждёт ГИПа', mine.filter((t) => APPROVER_ST.includes(t.status)), true],
        ['Скоро: черновики (ТЗ ещё не выдано)', mine.filter((t) => t.status === 'Черновик'), false],
        ['Принято за 2 недели', mine.filter((t) => t.status === 'Принята' && (!t.finished || parseD(t.finished) >= lim)), false],
      ];
      groups.forEach(([title, list, open]) => {
        if (!list.length) return;
        const d = el('details', 'mw-group'); if (open) d.open = true;
        d.append(el('summary', null, `${title} · ${list.length}`));
        const g = el('div', 'mw-cards'); list.sort((a, b) => ((problem(a)?.key ?? 9) - (problem(b)?.key ?? 9)) || ((a.plan || '9') < (b.plan || '9') ? -1 : 1)).forEach((t) => g.append(mwCard(t)));
        d.append(g); parts.push(d);
      });
      if (!mine.length && !isMgr()) parts.push(el('div', 'card empty', 'Задач пока нет. Когда ГИП выдаст ТЗ, задача появится здесь.'));
      const k = (kpiRows() || []).find((r) => r.name === me);
      if (k && (mine.length || k.accepted)) { const p = el('p', 'note mw-kpi'); p.textContent = `KPI за месяц: принято ${k.accepted}` + (isNum(k.avg) ? `, средний балл ${nf1.format(k.avg)}` : '') + (k.cat ? `, категория ${k.cat}` : '') + '. Подробно — вкладка KPI.'; parts.push(p); }
    } else if (!isMgr()) parts.push(el('div', 'card empty', 'Вы не связаны с сотрудником: попросите администратора проверить вашу учётную запись.'));
    if (isMgr()) parts.push(missingBlock());
    box.replaceChildren(...parts);
  }

  // ---------- Канбан проекта: карточка = раздел, колонки = этапы
  const PK_SIG = ['Проблема', 'Ждёт решения', 'Нет отчёта', 'В порядке', 'Закрыт'];
  function pkSignal(x) {
    const cur = x.st.cur; if (x.st.closed) return 'Закрыт';
    if (cur && problem(cur) && problem(cur).key <= 1) return 'Проблема';
    if (x.st.pending || (cur && (APPROVER_ST.includes(cur.status) || cur.status === 'Черновик'))) return 'Ждёт решения';
    if (cur && needsReport(cur) && !reportedToday(cur)) return 'Нет отчёта';
    return 'В порядке';
  }
  function pkProjects() {
    const all = [...new Set((S.d.plan || []).filter((r) => isSection(r)).map((r) => r.project))];
    if (isMgr()) return all.filter(inMyProjects);
    const me = viewer().person; const mine = new Set((S.d.tasks || []).filter((t) => t.assignee === me && isProjectTask(t)).map((t) => t.project));
    return all.filter((p) => mine.has(p) || (viewer().projects || []).includes(p));
  }
  function renderPK() {
    const board = $('#kb-board'), sl = $('#kb-slicers'), sel = $('#pk-project');
    if (!S.d.plan || !S.d.tasks) { if (status('plan') === 'error') failIn(board, 'plan'); else skel(board, 260); return; }
    const projs = pkProjects();
    if (!projs.includes(S.pk.project)) S.pk.project = (S.filters.project && projs.includes(S.filters.project)) ? S.filters.project : projs[0] || '';
    if (document.activeElement !== sel) { sel.replaceChildren(...projs.map((p) => new Option(p, p))); sel.value = S.pk.project; }
    if (!projs.length) { sl.replaceChildren(); board.replaceChildren(el('div', 'pl-empty', isMgr() ? 'Нет проектов с составом. Создайте состав проекта, затем «Задачи и договоры» — разделы появятся здесь черновиками.' : 'У вас пока нет задач по проектам.')); $('#kb-count').textContent = ''; return; }
    const items = projectSections(S.pk.project).map((sec) => { const x = { sec, st: secState(sec), obj: objOfSec(sec) }; x.sig = pkSignal(x); x.who = x.st.cur?.assignee || (x.st.pending ? '' : sec.owner || ''); return x; });
    const f = S.pk.f; const val = (x, k) => (k === 'obj' ? x.obj?.name || '—' : k === 'disc' ? x.sec.code || '—' : k === 'who' ? x.who || '—' : x.sig);
    const pass = (x, skip) => ['obj', 'disc', 'who', 'sig'].every((k) => k === skip || !f[k].size || f[k].has(val(x, k)));
    const opt = (k) => [...new Set(items.map((x) => val(x, k)))].sort((a, b) => (k === 'sig' ? PK_SIG.indexOf(a) - PK_SIG.indexOf(b) : a.localeCompare(b, 'ru')));
    const groups = [['obj', 'Объект'], ['disc', 'Дисциплина'], ['who', 'Исполнитель'], ['sig', 'Сигнал']];
    sl.replaceChildren(...groups.map(([k, title]) => {
      const bx = el('div', 'kb-slicer kb-s-' + k); const hd = el('div', 'kb-s-head'); hd.append(el('span', null, title));
      const clr = el('button', 'kb-clear'); clr.type = 'button'; clr.title = 'Сбросить срез'; clr.innerHTML = KB_FUNNEL; clr.disabled = !f[k].size; clr.addEventListener('click', () => { f[k].clear(); renderPK(); }); hd.append(clr); bx.append(hd);
      const list = el('div', 'kb-opts'); const avail = new Set(items.filter((x) => pass(x, k)).map((x) => val(x, k)));
      opt(k).forEach((v) => { const b = el('button', 'kb-opt'); b.type = 'button'; b.textContent = k === 'who' ? kbShort(v) : v; b.title = v; const on = f[k].has(v); b.setAttribute('aria-pressed', String(on)); if (!avail.has(v) && !on) b.classList.add('dim'); b.addEventListener('click', (e) => { const s = f[k]; if (e.ctrlKey || e.metaKey || S.kb.multi) { if (s.has(v)) s.delete(v); else s.add(v); } else if (s.size === 1 && s.has(v)) s.clear(); else { s.clear(); s.add(v); } renderPK(); }); list.append(b); });
      bx.append(list); return bx;
    }));
    const shown = items.filter((x) => pass(x));
    const W = d3.sum(shown, (x) => x.sec.dur || 1) || 1; const pct = d3.sum(shown, (x) => (x.sec.dur || 1) * x.st.pct) / W;
    const closed = shown.filter((x) => x.st.closed).length;
    $('#kb-fill').style.height = Math.round(pct * 100) + '%'; $('#kb-pct').textContent = Math.round(pct * 100) + '%';
    $('#kb-gauge-note').textContent = `${closed} из ${shown.length} ${plural(shown.length, 'раздела', 'разделов', 'разделов')} закрыто. Процент учитывает вес этапов.`;
    const order = { 'Проблема': 0, 'Ждёт решения': 1, 'Нет отчёта': 2, 'В порядке': 3, 'Закрыт': 4 };
    board.replaceChildren(...PK_COLS.map((c) => {
      const col = el('section', 'kb-col pk-' + c.key);
      const cards = shown.filter((x) => x.st.col === c.key).sort((a, b) => order[a.sig] - order[b.sig] || wbsCmp(a.sec.wbs, b.sec.wbs));
      const hd = el('div', 'kb-head'); hd.title = c.hint; hd.append(el('span', null, c.title), el('span', 'kb-n', String(cards.length))); col.append(hd);
      const list = el('div', 'kb-list');
      cards.forEach((x) => list.append(pkCard(x)));
      if (!cards.length) list.append(el('div', 'kb-empty', '—'));
      col.append(list); return col;
    }));
    $('#kb-count').textContent = `${shown.length} ${plural(shown.length, 'раздел', 'раздела', 'разделов')} · выполнено ${Math.round(pct * 100)}% · закрыто ${closed}` + (Object.values(f).some((s) => s.size) ? ' · с фильтрами' : '');
    const nf0 = Object.values(f).reduce((a, s) => a + s.size, 0); $('#kb-filt').textContent = nf0 ? `Фильтры · ${nf0}` : 'Фильтры';
  }
  function pkCard(x) {
    const { sec, st } = x; const cur = st.cur;
    const cls = x.sig === 'Проблема' ? 'p1' : x.sig === 'Ждёт решения' ? 'p2' : x.sig === 'Нет отчёта' ? 'p2' : 'p3';
    const c = el('article', `kb-card pk ${cls}${st.closed ? ' closed' : ''}`); c.tabIndex = 0;
    c.append(el('div', 'kb-t', `${sec.code ? sec.code + ' · ' : ''}${sec.name || '—'}`), el('div', 'kb-a', x.obj?.name || ''));
    c.append(el('div', 'kb-m', x.who ? x.who : st.pending ? `назначить: ${st.pending}` : 'нет исполнителя'));
    const meta = [];
    if (cur && cur.plan && !CLOSED.includes(cur.status) && cur.status !== 'Согласование') meta.push('до ' + fD(cur.plan).slice(0, 5));
    else if (cur && isNum(cur.days) && ['Черновик', 'Новая', 'На согласовании'].includes(cur.status)) meta.push(cur.days + ' дн.');
    meta.push(Math.round(st.pct * 100) + '%');
    c.append(el('div', 'kb-m', meta.join(' · ')));
    if (cur && !['Черновик', 'Новая', 'На согласовании'].includes(cur.status)) { const bar = el('div', 'kb-bar'); const f = el('i'); f.style.width = Math.round((cur.done || 0) * 100) + '%'; bar.append(f); c.append(bar); }
    const tags = el('div', 'kb-tags');
    if (cur) {
      const pr = problem(cur);
      if (pr && pr.key <= 1) tags.append(el('span', 'kb-tag bad', pr.text));
      if (cur.status === 'На проверке') tags.append(el('span', 'kb-tag ink', 'сдано, ждёт ГИПа'));
      if (cur.status === 'На согласовании') tags.append(el('span', 'kb-tag ink', `срок ${cur.days ?? '—'} дн.?`));
      if (cur.status === 'Новая') tags.append(el('span', 'kb-tag', 'ждёт принятия'));
      if (cur.status === 'Есть вопрос') tags.append(el('span', 'kb-tag warn', 'вопрос'));
      if (cur.status === 'На доработке') tags.append(el('span', 'kb-tag warn', 'доработка'));
      if (cur.status === 'Согласование') tags.append(el('span', 'kb-tag ink', cur.approver === 'Заказчик' ? 'у заказчика' : 'у ГИПа'));
      if (x.sig === 'Нет отчёта') tags.append(el('span', 'kb-tag warn', 'нет отчёта'));
    }
    if (st.pending) tags.append(el('span', 'kb-tag ink', 'назначить этап'));
    if (sec.doc) tags.append(el('span', 'kb-id', sec.doc.split('_').slice(-3).join('_')));
    c.append(tags);
    c.addEventListener('click', () => openSecCard(sec.id));
    c.addEventListener('keydown', (e) => { if (e.key === 'Enter') openSecCard(sec.id); });
    return c;
  }
  function renderKanban() {
    $$('#kb-mode button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.m === S.kbMode)));
    const proj = S.kbMode === 'proj';
    $('#pk-project').hidden = !proj; $('#kb-add-ns').hidden = proj || !(isMgr() || ['Кадры', 'Админ', 'Бухгалтер'].includes(viewer().role)); $('#kb-old-l').hidden = proj;
    $('#kb-board').classList.toggle('pk-board', proj);
    $('#kb-sub').textContent = proj ? 'Разделы проекта по этапам. Нажмите на карточку, чтобы увидеть этапы, историю и доступные действия.' : (isBoss() ? 'Нестандартные задачи · перетащите карточку, чтобы сменить статус, или нажмите на неё' : 'Нестандартные задачи · нажмите на карточку, чтобы увидеть действия');
    $('#kb-legend').replaceChildren(el('p', 'note', proj ? 'Сигнал' : 'Приоритет'), ...(proj ? [['var(--kb-hi)', 'Проблема'], ['var(--kb-md)', 'Ждёт решения или отчёта'], ['var(--kb-lo)', 'В порядке']] : [['var(--kb-hi)', 'Высокий'], ['var(--kb-md)', 'Средний'], ['var(--kb-lo)', 'Низкий']]).map(([c, t]) => { const s = el('span'); const i = el('i', 'kb-arrow'); i.style.background = c; s.append(i, document.createTextNode(t)); return s; }));
    if (proj) renderPK(); else renderNS();
  }

  // ---------- wiring
  function goTab(t) { S.tab = t; try { localStorage.setItem('gx-tab', t); } catch (e) { /* ignore */ } render(); window.scrollTo({ top: 0 }); }
  $$('.tab').forEach((b) => b.addEventListener('click', () => goTab(b.dataset.tab)));
  $$('[data-goto]').forEach((b) => b.addEventListener('click', () => goTab(b.dataset.goto)));
  $('#f-project').addEventListener('change', (e) => { S.filters.project = e.target.value; if (e.target.value) { S.pl.project = e.target.value; S.pl.keepScroll = false; } render(); });
  $('#f-person').addEventListener('change', (e) => { S.filters.person = e.target.value; render(); });
  $('#f-reset').addEventListener('click', () => { S.filters = { project: '', person: '' }; render(); });
  $('#btn-refresh').addEventListener('click', () => { refreshAll(); toast('Обновляю…'); });
  $('#btn-task').addEventListener('click', () => openTask(null, {}));
  $('#btn-op').addEventListener('click', () => openOp({}));
  $('#btn-op2').addEventListener('click', () => openOp({}));
  $('#t-search').addEventListener('input', renderTasks); $('#t-status').addEventListener('change', renderTasks);
  $('#g-group').addEventListener('change', (e) => { S.gGroup = e.target.value; try { localStorage.setItem('gx-group', S.gGroup); } catch (x) { /* ignore */ } renderGantt(); });
  $('#g-done').addEventListener('change', (e) => { S.gDone = e.target.checked; renderGantt(); });
  $('#kpi-month').addEventListener('change', (e) => { if (/^\d{4}-\d{2}$/.test(e.target.value)) { S.kpiMonth = e.target.value; renderKpi(); } });
  $('#op-search').addEventListener('input', renderMoney); $('#c-search').addEventListener('input', renderContracts); $('#c-status').addEventListener('change', renderContracts);
  $$('#p-team .tm-chip').forEach((c) => c.addEventListener('click', () => { S.teamF = c.dataset.f; renderTeam(); }));
  $('#kb-multi').addEventListener('click', () => { S.kb.multi = !S.kb.multi; renderKanban(); });
  $$('#kb-mode button').forEach((b) => b.addEventListener('click', () => { S.kbMode = b.dataset.m; try { localStorage.setItem('gx-kbmode', S.kbMode); } catch (x) { /* ignore */ } renderKanban(); }));
  $('#pk-project').addEventListener('change', (e) => { S.pk.project = e.target.value; Object.values(S.pk.f).forEach((x) => x.clear()); renderKanban(); });
  $('#kb-add-ns').addEventListener('click', () => openNonStd({ dept: ({ 'Кадры': 'Кадры', 'Админ': 'Админ', 'Бухгалтер': 'Бухгалтерия' })[viewer().role] }));
  $('#f-as').addEventListener('change', (e) => { const list = (S.d.access || []).filter((r) => r.person && r.person !== S.me?.person); const r = list[Number(e.target.value)]; S.as = e.target.value === '' || !r ? null : { role: r.role || 'Специалист', person: r.person, projects: r.projects, pages: r.pages }; S.filters = { project: '', person: '' }; render(); });
  $('#pl-tails').addEventListener('change', (e) => { S.pl.tails = e.target.checked; renderPlan(); });
  $('#kb-filt').addEventListener('click', () => { const o = $('#kb-slicers').classList.toggle('open'); $('#kb-filt').setAttribute('aria-expanded', String(o)); });
  $('#kb-reset').addEventListener('click', () => { Object.values(S.kb.f).forEach((x) => x.clear()); Object.values(S.pk.f).forEach((x) => x.clear()); renderKanban(); });
  $('#kb-old').addEventListener('change', (e) => { S.kb.oldDone = e.target.checked; renderKanban(); });
  $('#cp-project').addEventListener('change', (e) => { S.pl.project = e.target.value; S.pl.keepScroll = false; renderComp(); });
  $('#cp-obj').addEventListener('click', () => openObject(null));
  $('#cp-import').addEventListener('click', (e) => importPlatformObjects(e.currentTarget));
  $('#cp-ciph').addEventListener('click', () => openCipher(S.pl.project));
  $('#cp-sync').addEventListener('click', () => openSync(S.pl.project));
  $('#cp-move').addEventListener('click', () => openTransfer(S.pl.project));
  $('#cp-xlsx').addEventListener('click', (e) => exportCompXlsx(e.currentTarget));
  $('#cp-pdf').addEventListener('click', (e) => exportCompPdf(e.currentTarget));
  ['#cp-owners', '#pl-owners'].forEach((id) => $(id).addEventListener('change', (e) => { S.pl.owners = e.target.checked; try { localStorage.setItem('gx-owners', S.pl.owners ? '1' : '0'); } catch (x) { /* ignore */ } render(); }));
  $('#pl-project').addEventListener('change', (e) => { S.pl.project = e.target.value; S.pl.keepScroll = false; renderPlan(); });
  $('#pl-add').addEventListener('click', () => openPlan(null, { project: S.pl.project }));
  $('#pl-tpl').addEventListener('click', () => openTemplate(S.pl.project));
  $('#pl-base').addEventListener('click', (e) => saveBaseline(e.currentTarget));
  $('#pl-xlsx').addEventListener('click', (e) => exportXlsx(e.currentTarget));
  $('#pl-pdf').addEventListener('click', (e) => exportPdf(e.currentTarget));
  $$('#pl-zoom button').forEach((b) => b.addEventListener('click', () => { S.pl.zoom = b.dataset.z; S.pl.keepScroll = false; try { localStorage.setItem('gx-zoom', S.pl.zoom); } catch (x) { /* ignore */ } renderPlan(); }));
  [['#pl-crit', 'crit'], ['#pl-basechk', 'base'], ['#pl-links', 'links']].forEach(([id, k]) => $(id).addEventListener('change', (e) => { S.pl[k] = e.target.checked; renderPlan(); }));
  let rw; window.addEventListener('resize', () => { clearTimeout(rw); rw = setTimeout(render, 150); });
  render();
  boot();
})();
