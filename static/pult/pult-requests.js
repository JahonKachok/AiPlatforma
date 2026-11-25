/* «Запросы»: so'rovlar reyestri, kontaktlar, ТКП konstruktori (PDF bilan), imzo va muhr.
 * Manba: GASTEC Пульт (5).html; Google Sheets o'rniga platforma API'si (apps/pult/inquiries.py).
 * pult.js yordamchi funksiyalarini `ctx` orqali beradi — global o'zgaruvchi yo'q.
 * ТКП matni — buyurtmachiga ketadigan ruscha hujjat: interfeys tili o'zbek/ingliz bo'lsa ham
 * tarjima qilinmaydi (elR/rawText va data-no-i18n, qarang: pult-i18n.js). */
window.PULT_REQUESTS = (ctx) => {
  'use strict';
  const { S, API, DS, $, $$, el, nf, nf1, isNum, fNum, fPct, fD, fN, iso, today, pad, str, dn, plural, DAY, modal, field, input, select, tile, emptyRow, skel, failIn, status, toast, userErr, errText, apiFetch, refreshAll, loadScript, saveFile, safeName, allPeopleNames, isBoss } = ctx;
  const rawText = (t) => (window.PULT_I18N?.raw ? window.PULT_I18N.raw(t) : document.createTextNode(t));
  const elR = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; e.dataset.noI18n = ''; if (text != null) e.append(rawText(String(text))); return e; };
  const optR = (text, value) => { const o = document.createElement('option'); o.value = value; o.dataset.noI18n = ''; o.append(rawText(String(text))); return o; };
  const ruPlural = (n, a, b, c) => { const x = Math.abs(n) % 100, y = x % 10; if (x > 10 && x < 20) return c; if (y > 1 && y < 5) return b; if (y === 1) return a; return c; };
  const canSign = () => !!S.d.features?.sign && isBoss();
  const canManageSeal = () => !!S.d.features?.seal && isBoss();

  // =====================================================================
  // ЗАПРОСЫ: реестр, контакты, конструктор ТКП, подпись и печать на PDF
  // =====================================================================
  const RQ_STATUSES = ['Новый', 'Готовим ТКП', 'ТКП отправлено', 'Переговоры', 'Ожидание', 'Выигран', 'Проигран', 'Отказались'];
  const RQ_OPEN = ['Новый', 'Готовим ТКП', 'ТКП отправлено', 'Переговоры', 'Ожидание'];
  const RQ_CLS = { 'Новый': 'ink', 'Готовим ТКП': 'warn', 'ТКП отправлено': 'ink', 'Переговоры': 'ink', 'Ожидание': '', 'Выигран': 'ok', 'Проигран': 'bad', 'Отказались': '' };
  const RQ_KINDS = ['ПСД', 'Рабочий проект (РП)', 'Рабочая документация (РД)', 'ТЭО', 'Обследование', 'Экспертиза', 'Авторский надзор', 'Изыскания', 'Слаботочные системы', 'Прочее'];
  const COMPANY = { name: 'ООО "GASTEC PROJECT"', addr: 'Адрес: город Ташкент, Чиланзарский район, Чилонзор МФЙ, улица Чилонзор, дом-3А, Кв-24.', inn: 'ИНН: 311926984. Телефон: +998 90 805 00 48, +998 99 022 6777', mail: 'sardor.gastec@gmail.com' };
  const rqStatusPill = (s) => el('span', 'pill ' + (RQ_CLS[s] ?? ''), s || '—');
  const rqContacts = (no) => (S.d.rcont || []).filter((c) => c.req === no);
  const rqTkps = (no) => (S.d.tkp || []).filter((t) => t.req === no).sort((a, b) => str(b.at).localeCompare(str(a.at)));
  const rqUzs = (r) => (!isNum(r.amount) ? 0 : r.cur === 'USD' ? r.amount * (S.d.rate || S.d.home?.rate || 0) : r.amount);
  const fMoneyRq = (v, cur) => (!isNum(v) ? '—' : cur === 'USD' ? '$' + nf.format(v) : nf.format(v) + ' сум');
  const libSetting = (name, def) => { const r = (S.d.tkplib || []).find((x) => x.sec === 'Настройка' && x.text === name); return r && str(r.priceRaw) !== '' ? str(r.priceRaw) : def; };

  // ---------- registry page
  function renderReq() {
    const tb = $('#rq-table tbody'); const tiles = $('#rq-tiles');
    $$('#rq-filter button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.f === S.rqF)));
    $('#rq-sign').hidden = !canSign(); $('#rq-import').hidden = !isBoss();
    if (!S.d.reqs) {
      tb.replaceChildren(); emptyRow(tb, 9, status() === 'error' ? 'Не загрузилось: ' + (S.loadErr || 'ошибка сервера') : 'Загрузка…');
      if (status() === 'error') failIn(tiles); else skel(tiles, 84); return;
    }
    const all = S.d.reqs; const yearAgo = iso(new Date(today().getTime() - 365 * DAY));
    const inWork = all.filter((r) => r.status === 'Новый' || r.status === 'Готовим ТКП');
    const waiting = all.filter((r) => ['ТКП отправлено', 'Переговоры', 'Ожидание'].includes(r.status));
    const won = all.filter((r) => r.status === 'Выигран' && (r.tkpDate || r.date || '9') >= yearAgo);
    const lost = all.filter((r) => (r.status === 'Проигран' || r.status === 'Отказались') && (r.tkpDate || r.date || '9') >= yearAgo);
    const late = inWork.filter((r) => r.due && r.due < iso(today()));
    const fMln2 = (v) => (v >= 1e9 ? nf1.format(v / 1e9) + ' млрд' : nf1.format(v / 1e6) + ' млн');
    tiles.replaceChildren(
      tile('Готовим ТКП', fNum(inWork.length), late.length ? `просрочен срок подачи: ${late.length}` : 'новые и в работе', late.length ? 'bad' : 'ink'),
      tile('Ждём ответа', fNum(waiting.length), `на сумму ${fMln2(d3.sum(waiting, rqUzs))} сум`, ''),
      tile('Выиграно за год', fNum(won.length), `на сумму ${fMln2(d3.sum(won, rqUzs))} сум`, 'ok'),
      tile('Конверсия', won.length + lost.length ? fPct(won.length / (won.length + lost.length)) : '—', 'выиграно из решённых за год', ''),
    );
    const q = $('#rq-search').value.trim().toLowerCase(); const f = S.rqF;
    let rows = all.filter((r) => (f === 'open' ? RQ_OPEN.includes(r.status) || !r.status : f === 'all' ? true : f === 'win' ? r.status === 'Выигран' : r.status === 'Проигран' || r.status === 'Отказались'));
    if (q) rows = rows.filter((r) => [r.no, r.short, r.client, r.title, r.tkpNo, r.note, ...rqContacts(r.no).map((c) => c.name + ' ' + (c.phone || ''))].some((v) => v && String(v).toLowerCase().includes(q)));
    rows = rows.slice().sort((a, b) => str(b.no).localeCompare(str(a.no), 'ru', { numeric: true }));
    $('#rq-count').textContent = `${rows.length} / ${all.length}`;
    tb.replaceChildren();
    rows.forEach((r) => {
      const tr = el('tr', 'click'); tr.addEventListener('click', (e) => { if (e.target.closest('button,a')) return; openReq(r.no); });
      const name = el('td'); name.append(elR('b', null, r.short || '—'), elR('div', 'note', r.client || '')); name.style.minWidth = '14rem';
      const st = el('td'); st.append(rqStatusPill(r.status));
      const c0 = rqContacts(r.no)[0]; const ct = el('td', 'hide-narrow'); if (c0) { ct.append(elR('div', null, c0.name || '')); if (c0.phone) { const a = el('a', 'note', c0.phone); a.href = 'tel:' + c0.phone.replace(/[^\d+]/g, ''); ct.append(a); } }
      const tk = el('td', 'num'); tk.textContent = r.tkpNo ? `${r.tkpNo}${r.tkpDate ? ' · ' + fD(r.tkpDate) : ''}` : '—';
      const sum = el('td', 'r num'); sum.textContent = isNum(r.amount) ? fMoneyRq(r.amount, r.cur) : '—'; if (r.tkp2) sum.title = 'Первое ТКП: ' + (r.tkpText || '');
      const due = el('td', 'num hide-narrow'); due.textContent = r.due ? fD(r.due) : ''; if (r.due && r.due < iso(today()) && (r.status === 'Новый' || r.status === 'Готовим ТКП')) due.style.color = 'var(--bad)';
      const act = el('td', 'r'); const b = el('button', 'btn sm', 'ТКП'); b.type = 'button'; b.title = 'Конструктор ТКП'; b.addEventListener('click', () => openTkp(r.no)); act.append(b);
      if (r.folder && /^https:\/\//.test(r.folder)) { const a = el('a', 'btn sm ghost', 'Папка'); a.href = r.folder; a.target = '_blank'; a.rel = 'noopener'; act.append(a); }
      tr.append(el('td', 'num', r.no), el('td', 'num hide-narrow', r.date ? fD(r.date) : ''), name, st, ct, tk, sum, due, act);
      tb.append(tr);
    });
    if (!rows.length) emptyRow(tb, 9, all.length ? 'По фильтру ничего нет.' : 'Запросов пока нет. Нажмите «+ Запрос».');
  }

  // ---------- request card
  function openReq(no) {
        const r = no ? (S.d.reqs || []).find((x) => x.no === no) : null;
    if (no && !r) return toast('Запрос не найден, обновите страницу.');
    modal(r ? `${r.no} · ${r.short || 'Запрос'}` : 'Новый запрос', (m, close) => {
      m.classList.add('rq-modal');
      const form = el('div', 'form');
      const fShort = input('rq-short', 'text', r?.short || '', { placeholder: 'Например: ХВП Фергана', autocomplete: 'off' });
      const fClient = input('rq-client', 'text', r?.client || '', { list: 'rq-clients', autocomplete: 'off', placeholder: 'ООО «…»' });
      const dlc = el('datalist'); dlc.id = 'rq-clients'; [...new Set((S.d.reqs || []).map((x) => x.client).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'ru')).forEach((c) => dlc.append(optR(c, c)));
      const fTitle = el('textarea', 'ctl'); fTitle.id = 'rq-title'; fTitle.value = r?.title || ''; fTitle.rows = 3; fTitle.placeholder = 'Полное название объекта, как в ТЗ — пойдёт в ТКП';
      const fStatus = select('rq-status', RQ_STATUSES, r?.status || 'Новый');
      const fDate = input('rq-date', 'date', r?.date || iso(today()));
      const fDue = input('rq-due', 'date', r?.due || '');
      const fKind = input('rq-kind', 'text', r?.kind || '', { list: 'rq-kinds', autocomplete: 'off' }); const dlk = el('datalist'); dlk.id = 'rq-kinds'; RQ_KINDS.forEach((k) => dlk.append(optR(k, k)));
      const owners = allPeopleNames(); const fOwner = select('rq-owner', [new Option('—', ''), ...owners.map((n) => optR(n, n))], r?.owner || ''); if (r?.owner && !owners.includes(r.owner)) fOwner.append(new Option(r.owner, r.owner)); fOwner.value = r?.owner || '';
      const fBasis = input('rq-basis', 'text', r?.basis || '', { placeholder: 'письмо №… от …, тендер №…', autocomplete: 'off' });
      const fPlace = input('rq-place', 'text', r?.place || '', { placeholder: 'город, область', autocomplete: 'off' });
      const fFolder = input('rq-folder', 'url', r?.folder || '', { placeholder: 'https://drive.google.com/…' });
      const fTz = input('rq-tz', 'url', r?.tz || '', { placeholder: 'ссылка на ТЗ на Диске' });
      const fNote = el('textarea', 'ctl'); fNote.id = 'rq-note'; fNote.value = r?.note || ''; fNote.rows = 2; fNote.placeholder = 'Что уточнить у заказчика, договорённости, торг';
      const fReason = input('rq-reason', 'text', r?.reason || '', { placeholder: 'почему выиграли / проиграли', autocomplete: 'off' });
      const projs = (S.d.projects || []).map((p) => p.name); const fProj = select('rq-proj', [new Option('—', ''), ...projs.map((p) => optR(p, p))], r?.project || ''); if (r?.project && !projs.includes(r.project)) { fProj.append(new Option(r.project, r.project)); fProj.value = r.project; }
      const lReason = field('Причина выигрыша / проигрыша', fReason, 'full'); const lProj = field('Проект в финансах (после победы)', fProj);
      const syncSt = () => { const s = fStatus.value; lReason.hidden = !['Выигран', 'Проигран', 'Отказались'].includes(s); lProj.hidden = s !== 'Выигран'; }; fStatus.addEventListener('change', syncSt);
      form.append(field('Краткое название', fShort), field('Заказчик', fClient), dlc, field('Объект / название проекта', fTitle, 'full'), field('Статус', fStatus), field('Ответственный у нас', fOwner),
        field('Дата поступления', fDate), field('Срок подачи ТКП', fDue), field('Вид работ', fKind), dlk, field('Основание (письмо, тендер)', fBasis), field('Место объекта', fPlace), field('Папка на Диске', fFolder), field('ТЗ (ссылка)', fTz, 'full'), field('Примечание', fNote, 'full'), lReason, lProj);
      syncSt(); m.append(form);
      // contacts
      const cBox = el('div', 'rq-contacts'); const cHead = el('div', 'card-h'); cHead.append(el('h4', null, 'Контакты: с кем связываемся'));
      const cAdd = el('button', 'btn sm', '+ Контакт'); cAdd.type = 'button'; cHead.append(cAdd); cBox.append(cHead);
      const cList = el('div', 'rq-clist'); cBox.append(cList);
      const lines = [];
      const addLine = (c) => {
        const row = el('div', 'rq-crow'); const mk = (k, ph, type = 'text') => { const i = el('input', 'ctl'); i.type = type; i.value = c?.[k] || ''; i.placeholder = ph; i.setAttribute('aria-label', ph); return i; };
        const L = { c, name: mk('name', 'Имя'), role: mk('role', 'Должность / организация'), phone: mk('phone', 'Телефон', 'tel'), email: mk('email', 'Email', 'email'), tg: mk('tg', 'Telegram'), note: mk('note', 'Примечание'), del: false };
        const x = el('button', 'btn sm ghost', '✕'); x.type = 'button'; x.setAttribute('aria-label', 'Удалить контакт'); x.addEventListener('click', () => { L.del = true; row.remove(); });
        row.append(L.name, L.role, L.phone, L.email, L.tg, L.note, x); cList.append(row); lines.push(L);
      };
      (r ? rqContacts(r.no) : []).forEach(addLine); if (!lines.length) addLine(null);
      cAdd.addEventListener('click', () => addLine(null));
      m.append(cBox);
      // TKP versions + journal
      if (r) {
        const tk = rqTkps(r.no); const info = el('div', 'rq-side');
        if (r.tkpNo || r.tkpText) { const p = el('p', 'note'); p.textContent = `ТКП №${r.tkpNo || '—'} от ${r.tkpDate ? fD(r.tkpDate) : '—'}: ${r.tkpText || fMoneyRq(r.amount, r.cur)}` + (r.tkp2 ? `. ТКП-2 от ${r.tkp2Date ? fD(r.tkp2Date) : '—'}: ${r.tkp2}` : ''); info.append(p); }
        if (tk.length) { const ul = el('ul', 'sy-list'); tk.slice(0, 6).forEach((t) => { const li = el('li'); const b = el('button', 'linkbtn', `№${t.no} от ${fD(t.date)} · ${fMoneyRq(t.total, t.cur)} · версия ${t.ver || 1}`); b.type = 'button'; b.addEventListener('click', () => { close(); openTkp(r.no, t); }); li.append(b); ul.append(li); }); info.append(el('h4', null, 'Сохранённые ТКП'), ul); }
        const logs = (S.d.rlog || []).filter((x) => x.req === r.no).slice(-8).reverse();
        if (logs.length) { const d = el('details', 'tc-log'); d.append(el('summary', null, `История · ${logs.length}`)); const ul = el('ul'); logs.forEach((x) => ul.append(el('li', null, `${fD(x.date).slice(0, 5)} · ${x.text}${x.by ? ' · ' + x.by : ''}`))); d.append(ul); info.append(d); }
        if (info.children.length) m.append(info);
      }
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); foot.append(err);
      if (r) { const t = el('button', 'btn', 'Конструктор ТКП'); t.type = 'button'; t.addEventListener('click', () => { close(); openTkp(r.no); }); foot.append(t); }
      const cancel = el('button', 'btn ghost', 'Отмена'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const save = el('button', 'btn primary', r ? 'Сохранить' : 'Создать запрос'); save.type = 'button'; foot.append(cancel, save); m.append(foot);
      save.addEventListener('click', async () => {
        if (!fShort.value.trim() && !fTitle.value.trim()) { err.textContent = 'Напишите краткое название или название объекта.'; return; }
        const set = { short: fShort.value.trim(), client: fClient.value.trim(), title: fTitle.value.trim(), status: fStatus.value, owner: fOwner.value, date: fDate.value || '', due: fDue.value || '', kind: fKind.value.trim(), basis: fBasis.value.trim(), place: fPlace.value.trim(), folder: fFolder.value.trim(), tz: fTz.value.trim(), note: fNote.value.trim(), reason: fReason.value.trim(), project: fProj.value };
        if (set.folder && !/^https:\/\//.test(set.folder)) { err.textContent = 'Ссылка на папку должна начинаться с https://'; return; }
        save.disabled = true; save.textContent = 'Сохраняю…'; err.textContent = '';
        try {
          const contacts = lines.filter((L) => !L.del).map((L) => ({ id: L.c?.id || null, name: L.name.value.trim(), role: L.role.value.trim(), phone: L.phone.value.trim(), email: L.email.value.trim(), tg: L.tg.value.trim(), note: L.note.value.trim() }));
          const out = await apiFetch(API.requests, { no: r?.no || null, version: r?.version ?? null, set, contacts });
          toast(r ? 'Запрос сохранён' : `Создан запрос ${out.no}`); close(); refreshAll();
        } catch (e) { err.textContent = e && e.userText ? e.userText : errText(e); save.disabled = false; save.textContent = r ? 'Сохранить' : 'Создать запрос'; }
      });
    });
  }

  // ---------- numbers in words (Russian)
  function numWords(n) {
    n = Math.round(Math.abs(n)); if (n === 0) return 'ноль';
    const u = [['', 'один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять'], ['', 'одна', 'две', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять']];
    const teen = ['десять', 'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать', 'пятнадцать', 'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать'];
    const tens = ['', '', 'двадцать', 'тридцать', 'сорок', 'пятьдесят', 'шестьдесят', 'семьдесят', 'восемьдесят', 'девяносто'];
    const hund = ['', 'сто', 'двести', 'триста', 'четыреста', 'пятьсот', 'шестьсот', 'семьсот', 'восемьсот', 'девятьсот'];
    const units = [['', '', ''], ['тысяча', 'тысячи', 'тысяч'], ['миллион', 'миллиона', 'миллионов'], ['миллиард', 'миллиарда', 'миллиардов'], ['триллион', 'триллиона', 'триллионов']];
    const out = []; let i = 0;
    while (n > 0 && i < units.length) {
      const t = n % 1000; n = Math.floor(n / 1000);
      if (t) { const w = []; const h = Math.floor(t / 100), d = Math.floor((t % 100) / 10), o = t % 10; if (h) w.push(hund[h]); if (d === 1) w.push(teen[o]); else { if (d) w.push(tens[d]); if (o) w.push(u[i === 1 ? 1 : 0][o]); } if (i) w.push(units[i][ruPlural(t, 0, 1, 2)]); out.unshift(w.join(' ')); }
      i++;
    }
    return out.join(' ').replace(/\s+/g, ' ').trim();
  }
  const groupNum = (v) => nf.format(Math.round(v)).replace(/ /g, ' ');

  // ---------- TKP state
  function tkpLib() {
    const L = S.d.tkplib || [];
    return { items: L.filter((x) => x.sec === 'Позиция').sort((a, b) => (a.order ?? 999) - (b.order ?? 999)), groups: L.filter((x) => x.sec === 'Группа'), pays: L.filter((x) => x.sec === 'Оплата').sort((a, b) => (a.order ?? 99) - (b.order ?? 99)), notes: L.filter((x) => x.sec === 'Примечание').sort((a, b) => (a.order ?? 99) - (b.order ?? 99)), apps: L.filter((x) => x.sec === 'Приложение').sort((a, b) => (a.order ?? 99) - (b.order ?? 99)) };
  }
  function nextTkpNo() {
    const d = today(); const pfx = String(d.getFullYear()).slice(2) + pad(d.getMonth() + 1) + pad(d.getDate());
    const used = [...(S.d.reqs || []).map((r) => r.tkpNo), ...(S.d.tkp || []).map((t) => t.no)].filter((x) => str(x).startsWith(pfx));
    const n = d3.max(used, (x) => Number(str(x).split('-')[1]) || 1) || 0; return pfx + '-' + (n + 1);
  }
  // «Разработку ПСД по объекту: X» → предмет + объект без повтора
  function tkpSubject(r) {
    const t = str(r.title || r.short).replace(/\s+/g, ' ');
    const m = t.match(/^(.*?по\s+объект(?:у|ам)\s*:?)\s*(.+)$/i);
    // «Разработка …» → «на разработку …»
    const acc = (x) => 'на ' + (x.charAt(0).toLowerCase() + x.slice(1)).replace(/^разработка(?=[ :]|$)/, 'разработку');
    if (m && m[2].length > 3) return { subject: acc(m[1]).replace(/:?$/, ':'), object: m[2] };
    if (/^разработк/i.test(t)) return { subject: acc(t), object: '' };
    return { subject: 'на разработку проектно-сметной документации (ПСД) по объекту:', object: t };
  }
  function newTkp(r) {
    const L = tkpLib(); const vatRate = Number(libSetting('Ставка НДС, %', '12')) || 12;
    return {
      v: 1, req: r.no, no: nextTkpNo(), date: iso(today()), to: r.client || '', toPerson: '',
      greeting: libSetting('Приветствие', 'ООО «GASTEC PROJECT» приветствует Вас и предлагает следующее коммерческое предложение'),
      ...tkpSubject(r), basis: 'согласно Техническому заданию' + (r.basis ? ' (' + r.basis + ')' : ''),
      items: L.items.map((x, i) => ({ id: 'L' + i, group: x.group || '', text: x.text, price: isNum(x.price) ? x.price : null, days: isNum(x.days) ? x.days : null, on: x.def === 'Да', par: false, resp: 'GASTEC' })),
      groups: Object.fromEntries(L.groups.map((g) => [g.group || g.text, isNum(g.days) ? g.days : null])),
      showItems: 'appendix', vatMode: 'with', vatRate, cur: r.cur === 'USD' ? 'USD' : 'сум', manual: null, manualVat: true, words: true,
      termLabel: 'Срок проектирования', termFrom: '', termTo: '', termUnit: 'календарных', termTail: 'после получения исходных данных и авансового платежа.',
      pay: (L.pays.find((p) => p.def === 'Да') || L.pays[0] || { text: '' }).text,
      notes: L.notes.map((x) => ({ text: x.text, on: x.def === 'Да' })), notesExtra: '',
      apps: L.apps.map((x) => ({ text: x.text, on: x.def === 'Да' })), appsExtra: '',
      gTable: false, gGantt: false, gStart: '', gCost: true,
      signer: { pos: libSetting('Подпись: должность', 'Директор'), org: libSetting('Подпись: организация', 'ООО «GASTEC PROJECT»'), fio: libSetting('Подпись: ФИО', 'А.А. Саидходжаев') },
    };
  }

  // derived numbers and schedule
  function tkpCalc(T) {
    const on = T.items.filter((x) => x.on);
    const sumItems = d3.sum(on, (x) => (isNum(x.price) ? x.price : 0));
    let net, vat, total; const rate = (Number(T.vatRate) || 0) / 100;
    if (sumItems > 0) { net = sumItems; vat = Math.round(net * rate); total = net + vat; }
    else if (isNum(T.manual) && T.manual > 0) { if (T.manualVat) { total = T.manual; net = Math.round(total / (1 + rate)); vat = total - net; } else { net = T.manual; vat = Math.round(net * rate); total = net + vat; } }
    else { net = 0; vat = 0; total = 0; }
    // schedule: blocks in order; group with group-days = one block; par = starts with previous block
    const blocks = []; const seen = new Set();
    on.forEach((x) => {
      const gd = x.group && T.groups[x.group];
      if (gd && !isNum(x.days)) { if (seen.has(x.group)) return; seen.add(x.group); blocks.push({ group: x.group, days: gd, items: on.filter((y) => y.group === x.group && !isNum(y.days)), par: x.par, resp: x.resp }); }
      else blocks.push({ item: x, days: isNum(x.days) ? x.days : 0, par: x.par, resp: x.resp });
    });
    let prevS = 0, prevE = 0; blocks.forEach((b) => { b.s = b.par ? prevS : prevE; b.e = b.s + (b.days || 0); prevS = b.s; prevE = Math.max(prevE, b.e); });
    const span = d3.max(blocks, (b) => b.e) || 0;
    // numbering for tables
    const rows = []; let n = 0;
    blocks.forEach((b) => {
      if (b.group) { n++; const kids = b.items; rows.push({ num: n + '.', text: b.group, days: b.days, price: d3.sum(kids, (k) => k.price || 0) || null, head: true, s: b.s, e: b.e, resp: b.resp }); kids.forEach((k, j) => rows.push({ num: `${n}.${j + 1}.`, text: k.text, days: null, price: k.price, s: b.s, e: b.e, sub: true, resp: k.resp })); }
      else { n++; rows.push({ num: n + '.', text: b.item.text, days: b.days || null, price: b.item.price, s: b.s, e: b.e, resp: b.resp }); }
    });
    return { on, net, vat, total, rate, blocks, span, rows, hasPrices: sumItems > 0 };
  }
  function priceSentence(T, C) {
    const cur = T.cur; const w = (v) => (T.words ? ` (${numWords(v)})` : '');
    const money = (v) => (cur === 'USD' ? '$' + groupNum(v) : groupNum(v)) + w(v) + (cur === 'USD' ? '' : ' сум');
    if (!C.total) return '[укажите стоимость]';
    if (T.vatMode === 'without') return `${money(C.net)} без учёта НДС.`;
    if (T.vatMode === 'both') return `${money(C.net)} без учёта НДС; НДС ${Math.round(C.rate * 100)}% — ${cur === 'USD' ? '$' : ''}${groupNum(C.vat)}${cur === 'USD' ? '' : ' сум'}; итого ${money(C.total)} с учётом НДС.`;
    return `${money(C.total)} с учётом НДС.`;
  }
  function termSentence(T, C) {
    const a = str(T.termFrom), b = str(T.termTo); const n = a && b && a !== b ? `${a}-${b}` : a || b || (C.span ? String(C.span) : '');
    if (!n) return '[укажите срок]';
    const last = Number(n.split('-').pop()) || 0; const single = !n.includes('-');
    return `${n}${single && last ? ' (' + numWords(last) + ')' : ''} ${T.termUnit} ${ruPlural(last, 'день', 'дня', 'дней')} ${T.termTail}`.replace(/\s+/g, ' ').trim();
  }
  // shared document model: preview and PDF are drawn from the same blocks
  function tkpModel(T) {
    const C = tkpCalc(T); const apps = []; const appTitles = [];
    if (T.gTable && C.on.length) appTitles.push('Предварительный график работ со стоимостью');
    if (T.gGantt && C.blocks.length) appTitles.push('Календарный график выполнения работ');
    const appNo = (t) => appTitles.indexOf(t) + 1;
    let price = priceSentence(T, C);
    if (C.hasPrices && T.showItems === 'appendix' && T.gTable) price += ` Расшифровка по позициям — Приложение №${appNo('Предварительный график работ со стоимостью')}.`;
    let term = termSentence(T, C); if (T.gGantt && C.blocks.length) term += ` Календарный график — Приложение №${appNo('Календарный график выполнения работ')}.`;
    const payParts = str(T.pay).split(/;\s*/).map((s) => s.trim().replace(/\.$/, '')).filter(Boolean);
    const notes = [...T.notes.filter((x) => x.on).map((x) => x.text), ...str(T.notesExtra).split('\n').map((s) => s.trim()).filter(Boolean)];
    const appList = [...appTitles, ...T.apps.filter((x) => x.on).map((x) => x.text), ...str(T.appsExtra).split('\n').map((s) => s.trim()).filter(Boolean)];
    const kv = [['Стоимость услуг:', [price]], [T.termLabel + ':', [term]], ['Условия платежа:', payParts.length > 1 ? payParts.map((p, i) => `${i + 1}) ${p}${i === payParts.length - 1 ? '.' : ';'}`) : [payParts[0] ? payParts[0] + '.' : '[укажите условия оплаты]']]];
    if (notes.length) kv.push(['Примечания:', notes.map((t, i) => (notes.length > 1 ? `${i + 1}) ` : '') + t)]);
    if (appList.length) kv.push(['Приложения:', appList.map((t, i) => `${i + 1}) ${t}${i === appList.length - 1 ? '.' : ';'}`)]);
    const body = { no: T.no, date: fD(T.date), to: [T.toPerson, T.to].filter(Boolean).join('\n'), intro: { lead: `${T.greeting} ${T.subject}`.replace(/\s+/g, ' ').trim(), object: T.object, tail: T.basis ? ' ' + T.basis + ':' : ':' }, kv, posTable: C.hasPrices && T.showItems === 'body' ? C.rows : null };
    if (T.gTable && C.on.length) apps.push({ kind: 'table', n: appNo('Предварительный график работ со стоимостью'), title: 'Предварительный график работ со стоимостью', rows: C.rows });
    if (T.gGantt && C.blocks.length) apps.push({ kind: 'gantt', n: appNo('Календарный график выполнения работ'), title: 'Календарный график выполнения работ', rows: C.rows });
    return { T, C, body, apps };
  }
  const posTotals = (M) => { const { C, T } = M; const pc = Math.round(C.rate * 100); return [['Всего без НДС', C.net], [`НДС ${pc}%`, C.vat], [`Итого с учётом НДС${T.cur === 'USD' ? ', $' : ', сум'}`, C.total]]; };
  const dateOfDay = (T, k) => { if (!T.gStart) return null; const s = dn(T.gStart); const n = T.termUnit === 'рабочих' && S.d.cal ? S.d.cal.shift(s, k) : s + k; return fN(n); };

  // ---------- HTML preview
  function tkpPreview(M) {
    const { T, C, body } = M; const wrap = elR('div', 'tkp-pages'); wrap.dataset.noI18n = '';
    const page = (land) => { const p = elR('div', 'tkp-page' + (land ? ' land' : '')); wrap.append(p); return p; };
    const head = (p) => { const h = elR('div', 'tkp-head'); const l = elR('div'); l.append(elR('div', 'tkp-org', COMPANY.name), elR('div', null, COMPANY.addr), elR('div', null, COMPANY.inn), elR('div', 'tkp-mail', COMPANY.mail)); const img = elR('img'); img.src = DS.logo; img.alt = 'GASTEC PROJECT'; h.append(l, img); p.append(h, elR('div', 'tkp-rule')); };
    const sign = (p) => { const s = elR('div', 'tkp-sign'); const a = elR('div'); a.append(elR('b', null, T.signer.pos), elR('br'), elR('b', null, T.signer.org)); s.append(a, elR('div', 'tkp-fio', T.signer.fio)); p.append(elR('p', 'tkp-p', 'С уважением и наилучшими пожеланиями,'), s); };
    const p1 = page(false); head(p1);
    const meta = elR('div', 'tkp-meta'); const a = elR('div'); a.append(elR('div', null, '№ ' + body.no), elR('div', null, 'Дата: ' + body.date)); const b = elR('div'); b.append(elR('b', null, 'Кому: '), rawText(body.to || '—')); meta.append(a, b); p1.append(meta, elR('h3', 'tkp-title', 'КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ'));
    const intro = elR('p', 'tkp-p ind'); intro.append(rawText(body.intro.lead + ' '), elR('i', null, body.intro.object || (/:$/.test(M.T.subject.trim()) ? '[объект]' : '')), rawText(body.intro.tail)); p1.append(intro);
    const kv = elR('table', 'tkp-kv'); body.kv.forEach(([k, lines]) => { const tr = elR('tr'); const th = elR('th', null, k); const td = elR('td'); lines.forEach((t) => td.append(elR('div', null, t))); tr.append(th, td); kv.append(tr); }); p1.append(kv);
    if (body.posTable) p1.append(posTableHtml(M, body.posTable));
    sign(p1);
    M.apps.forEach((ap) => {
      const p = page(ap.kind === 'gantt'); p.append(elR('div', 'tkp-app', `Приложение №${ap.n} к КП №${T.no} от ${fD(T.date)}`), elR('h3', 'tkp-title', ap.title), elR('p', 'tkp-p c', T.object || ''));
      if (ap.kind === 'table') p.append(posTableHtml(M, ap.rows, true)); else p.append(ganttHtml(M));
      sign(p);
    });
    return wrap;
  }
  function posTableHtml(M, rows, withDays) {
    const { T } = M; const t = elR('table', 'tkp-tbl'); const h = elR('tr'); ['№', 'Наименование работ', ...(withDays ? ['Сроки, дней'] : []), `Стоимость без НДС, ${T.cur === 'USD' ? '$' : 'сум'}`].forEach((x) => h.append(elR('th', null, x))); t.append(h);
    rows.forEach((r) => { const tr = elR('tr', r.head ? 'g' : ''); tr.append(elR('td', 'c', r.num), elR('td', r.sub ? 'sub' : null, r.text), ...(withDays ? [elR('td', 'c', r.days ? String(r.days) : '')] : []), elR('td', 'r', isNum(r.price) && r.price ? groupNum(r.price) : (r.head ? '' : '—'))); t.append(tr); });
    posTotals(M).forEach(([k, v], i) => { const tr = elR('tr', 'tot'); const td = elR('td', 'r', k); td.colSpan = withDays ? 2 : 2; tr.append(td); if (withDays) tr.append(elR('td', 'c', i === 2 && M.C.span ? String(M.C.span) : '')); tr.append(elR('td', 'r', groupNum(v))); t.append(tr); });
    return t;
  }
  function ganttUnits(M) { const per = M.T.termUnit === 'рабочих' ? 5 : 7; const span = M.C.span || 1; const byDay = span <= 21; let unit = byDay ? 1 : per; while (!byDay && Math.ceil(span / unit) > 36) unit *= 2; const n = Math.max(1, Math.ceil(span / unit)); return { unit, n, byDay, label: byDay ? 'дни' : unit === per ? 'недели' : `периоды по ${unit / per} нед.` }; }
  function ganttHtml(M) {
    const { T, C } = M; const G = ganttUnits(M); const t = elR('table', 'tkp-tbl tkp-gantt'); const h = elR('tr');
    ['№', 'Наименование работ', 'Отв.', 'Начало', 'Дн.', 'Окончание', ...(T.gCost ? ['Стоимость'] : [])].forEach((x) => h.append(elR('th', null, x)));
    for (let i = 0; i < G.n; i++) h.append(elR('th', 'w', String(i + 1))); t.append(h);
    C.rows.filter((r) => !r.sub).forEach((r) => {
      const tr = elR('tr', r.head ? 'g' : ''); tr.append(elR('td', 'c', r.num), elR('td', null, r.text), elR('td', 'c', r.resp === 'Заказчик' ? 'Заказчик' : 'GASTEC'), elR('td', 'c', dateOfDay(T, r.s) || 'день ' + (r.s + 1)), elR('td', 'c', r.e > r.s ? String(r.e - r.s) : '—'), elR('td', 'c', r.e > r.s ? dateOfDay(T, r.e) || 'день ' + r.e : '—'), ...(T.gCost ? [elR('td', 'r', r.price ? groupNum(r.price) : '')] : []));
      for (let i = 0; i < G.n; i++) { const a = i * G.unit, b = a + G.unit; const on = r.e > a && r.s < b && r.e > r.s; const td = elR('td', 'w' + (on ? ' on' + (r.resp === 'Заказчик' ? ' z' : '') : '')); tr.append(td); }
      t.append(tr);
    });
    const box = elR('div', 'tkp-gwrap'); box.append(t, elR('p', 'tkp-p small', `Шкала — ${G.label} от начала работ${T.gStart ? ' (' + fD(T.gStart) + ')' : ''}. Сроки в ${T.termUnit} днях. Отв.: GASTEC — исполнитель, Заказчик — действие заказчика.`));
    return box;
  }

  // ---------- PDF (pdfmake) from the same model
  const PDFMAKE = 'https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.2.11/pdfmake.min.js';
  const PDFLIB = 'https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js';
  const PDFJS = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
  const PDFJS_W = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
  let LOGO_B64 = '';
  async function fileB64(url) {
    let res; try { res = await fetch(url); } catch (e) { res = null; }
    if (!res || !res.ok) throw userErr('Не загрузились шрифты документа. Обновите страницу.');
    const b = new Uint8Array(await res.arrayBuffer()); let s = '';
    for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
    return btoa(s);
  }
  async function pdfMakeLib() {
    const pm = await loadScript(PDFMAKE, 'pdfMake');
    if (!pm.__gastec) { const [fr, fb, fi, fbi, logo] = await Promise.all([DS.tinosR, DS.tinosB, DS.tinosI, DS.tinosBi, DS.logo].map(fileB64)); LOGO_B64 = logo; pm.vfs = { 'T-R.ttf': fr, 'T-B.ttf': fb, 'T-I.ttf': fi, 'T-BI.ttf': fbi }; pm.fonts = { Tinos: { normal: 'T-R.ttf', bold: 'T-B.ttf', italics: 'T-I.ttf', bolditalics: 'T-BI.ttf' } }; pm.__gastec = true; }
    return pm;
  }
  const nbh = (t) => str(t).replace(/(\S)-(?=\S)/g, '$1\u2011');
  function tkpDocDef(M) {
    const { T, body } = M; const BLUE = '#1f3a93', OR = '#e36c09';
    const header = () => [{ columns: [{ width: '*', stack: [{ text: COMPANY.name, bold: true, fontSize: 15 }, { text: COMPANY.addr, fontSize: 10 }, { text: COMPANY.inn, fontSize: 10 }, { text: COMPANY.mail, fontSize: 10, color: '#1155cc', decoration: 'underline' }] }, { width: 150, image: 'logo', fit: [150, 52], alignment: 'right' }] }, { canvas: [{ type: 'rect', x: 0, y: 4, w: 499, h: 4, lineColor: OR, lineWidth: 1.2 }], margin: [0, 2, 0, 18] }];
    const sign = () => [{ text: 'С уважением и наилучшими пожеланиями,', margin: [0, 26, 0, 30] }, { columns: [{ width: '*', stack: [{ text: T.signer.pos, bold: true }, { text: T.signer.org, bold: true }] }, { width: 'auto', text: T.signer.fio, margin: [0, 13, 40, 0] }], unbreakable: true }];
    const kvBody = body.kv.map(([k, lines]) => [{ text: k, bold: true, margin: [0, 0, 0, 8] }, { stack: lines.map((t) => ({ text: nbh(t), alignment: 'justify' })), margin: [0, 0, 0, 8] }]);
    const content = [...header(),
      { columns: [{ width: '*', stack: [`№ ${body.no}`, `Дата: ${body.date}`], margin: [16, 0, 0, 0] }, { width: 'auto', text: [{ text: 'Кому:   ', bold: true }, body.to || '—'], margin: [0, 0, 20, 0] }], margin: [0, 0, 0, 18] },
      { text: 'КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ', bold: true, alignment: 'center', margin: [0, 0, 0, 14] },
      { text: [nbh(body.intro.lead) + ' ', { text: nbh(body.intro.object || ''), italics: true }, nbh(body.intro.tail)], alignment: 'justify', leadingIndent: 30, margin: [0, 0, 0, 16] },
      { table: { widths: [130, '*'], body: kvBody }, layout: 'noBorders', margin: [0, 0, 0, 6] },
    ];
    if (body.posTable) content.push(pdfPosTable(M, body.posTable, false));
    content.push(...sign());
    M.apps.forEach((ap) => {
      const land = ap.kind === 'gantt';
      content.push({ text: `Приложение №${ap.n} к КП №${T.no} от ${fD(T.date)}`, alignment: 'right', fontSize: 10, pageBreak: 'before', pageOrientation: land ? 'landscape' : 'portrait' },
        { text: ap.title, bold: true, alignment: 'center', margin: [0, 10, 0, 4] }, { text: nbh(T.object || ''), alignment: 'center', italics: true, fontSize: 10.5, margin: [0, 0, 0, 12] },
        ap.kind === 'table' ? pdfPosTable(M, ap.rows, true) : pdfGantt(M), ...sign());
    });
    void BLUE;
    return { pageSize: 'A4', pageMargins: [56, 34, 40, 40], defaultStyle: { font: 'Tinos', fontSize: 12, lineHeight: 1.12 }, images: { logo: 'data:image/png;base64,' + LOGO_B64 }, content, info: { title: `Коммерческое предложение №${T.no}`, author: 'ООО «GASTEC PROJECT»' } };
  }
  function pdfPosTable(M, rows, withDays) {
    const { T } = M; const H = (t) => ({ text: t, bold: true, alignment: 'center', fillColor: '#dbe5fb', fontSize: 10.5 });
    const b = [[H('№'), H('Наименование работ'), ...(withDays ? [H('Сроки, дней')] : []), H(`Стоимость без НДС, ${T.cur === 'USD' ? '$' : 'сум'}`)]];
    rows.forEach((r) => b.push([{ text: r.num, alignment: 'center' }, { text: nbh(r.text), bold: !!r.head, margin: [r.sub ? 10 : 0, 0, 0, 0] }, ...(withDays ? [{ text: r.days ? String(r.days) : '', alignment: 'center' }] : []), { text: isNum(r.price) && r.price ? groupNum(r.price) : r.head ? '' : '—', alignment: 'right' }]));
    posTotals(M).forEach(([k, v], i) => b.push([{ text: k, colSpan: 2, alignment: 'right', bold: i === 2 }, {}, ...(withDays ? [{ text: i === 2 && M.C.span ? String(M.C.span) : '', alignment: 'center', bold: true }] : []), { text: groupNum(v), alignment: 'right', bold: i === 2 }]));
    return { table: { headerRows: 1, widths: withDays ? [32, '*', 52, 100] : [32, '*', 110], body: b }, fontSize: 10.5, margin: [0, 6, 0, 6] };
  }
  function pdfGantt(M) {
    const { T, C } = M; const G = ganttUnits(M); const H = (t, o = {}) => ({ text: t, bold: true, alignment: 'center', fillColor: '#dbe5fb', fontSize: 8, ...o });
    const fixed = [22, 150, 44, 50, 24, 50, ...(T.gCost ? [58] : [])]; const wW = Math.max(4, Math.min(18, Math.floor((744 - d3.sum(fixed) - fixed.length * 6 - G.n * 0.6) / G.n)));
    const head = [H('№'), H('Наименование работ'), H('Отв.'), H('Начало'), H('Дн.'), H('Окончание'), ...(T.gCost ? [H('Стоимость')] : [])]; for (let i = 0; i < G.n; i++) head.push(H(String(i + 1), { fontSize: 6.5 }));
    const body = [head];
    C.rows.filter((r) => !r.sub).forEach((r) => {
      const row = [{ text: r.num, alignment: 'center' }, { text: nbh(r.text), bold: !!r.head }, { text: r.resp === 'Заказчик' ? 'Заказчик' : 'GASTEC', alignment: 'center' }, { text: dateOfDay(T, r.s) || 'день ' + (r.s + 1), alignment: 'center' }, { text: r.e > r.s ? String(r.e - r.s) : '—', alignment: 'center' }, { text: r.e > r.s ? dateOfDay(T, r.e) || 'день ' + r.e : '—', alignment: 'center' }, ...(T.gCost ? [{ text: r.price ? groupNum(r.price) : '', alignment: 'right' }] : [])];
      for (let i = 0; i < G.n; i++) { const a = i * G.unit, b = a + G.unit; const on = r.e > a && r.s < b && r.e > r.s; row.push({ text: '', fillColor: on ? (r.resp === 'Заказчик' ? '#f0a83a' : '#4f7fe0') : null }); }
      body.push(row);
    });
    return { stack: [{ table: { headerRows: 1, widths: [...fixed, ...Array(G.n).fill(wW)], body }, fontSize: 8, layout: { hLineColor: '#9aa3b0', vLineColor: '#c9d0db', hLineWidth: () => 0.5, vLineWidth: () => 0.4, paddingLeft: (i) => (i >= fixed.length ? 0 : 3), paddingRight: (i) => (i >= fixed.length ? 0 : 3) } }, { text: `Шкала — ${G.label} от начала работ${T.gStart ? ' (' + fD(T.gStart) + ')' : ''}. Сроки в ${T.termUnit} днях. Синий — GASTEC PROJECT, оранжевый — действия Заказчика.`, fontSize: 8.5, italics: true, margin: [0, 6, 0, 0] }] };
  }
  async function tkpPdfBytes(M) {
    const pm = await pdfMakeLib(); const dd = tkpDocDef(M);
    return new Promise((res, rej) => { try { pm.createPdf(dd).getBuffer((buf) => res(new Uint8Array(buf))); } catch (e) { rej(e); } });
  }
  const tkpFileName = (T, signed) => safeName(`Коммерческое предложение №${T.no}_GASTEC-${T.to || T.req}${signed ? '-signed' : ''}`) + '.pdf';

  // ---------- TKP builder modal
  async function openTkp(no, saved) {
        const r = (S.d.reqs || []).find((x) => x.no === no); if (!r) return toast('Запрос не найден.');
    if (!S.d.tkplib) return toast('Справочник ТКП ещё загружается.');
    let T = newTkp(r);
    if (saved) {
      let o = null; try { o = (await apiFetch(`${API.requests}offers/${saved.id}/`)).data; } catch (e) { return toast(errText(e)); }
      if (o && Array.isArray(o.items)) T = { ...T, ...o, ver: Number(saved.ver) || 1 }; else toast('Сохранённое ТКП не прочиталось, открыт новый шаблон.');
    }
    modal(`ТКП · ${r.no} · ${r.short || ''}`, (m, close) => {
      m.classList.add('tkp-modal');
      const grid = el('div', 'tkp-grid'); const left = el('div', 'tkp-form'); const right = el('div', 'tkp-prev'); grid.append(left, right); m.append(grid);
      const upd = () => { right.replaceChildren(tkpPreview(tkpModel(T))); sumLine.textContent = sumText(); };
      const sumText = () => { const C = tkpCalc(T); return C.total ? `Итого: ${fMoneyRq(C.net, T.cur)} без НДС · НДС ${fMoneyRq(C.vat, T.cur)} · ${fMoneyRq(C.total, T.cur)} с НДС${C.span ? ' · по графику ' + C.span + ' дн.' : ''}` : 'Отметьте позиции с ценой или введите сумму вручную.'; };
      const sec = (title, open = true) => { const d = el('details', 'tkp-sec'); d.open = open; d.append(el('summary', null, title)); left.append(d); return d; };
      const bind = (ctl, k, conv = (x) => x) => { ctl.addEventListener('input', () => { T[k] = conv(ctl.type === 'checkbox' ? ctl.checked : ctl.value); upd(); }); ctl.addEventListener('change', () => { T[k] = conv(ctl.type === 'checkbox' ? ctl.checked : ctl.value); upd(); }); return ctl; };
      const inp = (k, ph, type = 'text') => { const i = el('input', 'ctl'); i.type = type; i.value = T[k] ?? ''; if (ph) i.placeholder = ph; return bind(i, k); };
      const ta = (k, rows = 2, ph) => { const i = el('textarea', 'ctl'); i.rows = rows; i.value = T[k] ?? ''; if (ph) i.placeholder = ph; return bind(i, k); };
      const chk = (obj, key, label, after, raw) => { const l = el('label', 'tp-item'); const c = el('input'); c.type = 'checkbox'; c.checked = !!obj[key]; c.addEventListener('change', () => { obj[key] = c.checked; if (after) after(); upd(); }); l.append(c, raw ? elR('span', null, label) : el('span', null, label)); return l; };
      // 1. шапка
      const s1 = sec('1. Шапка и объект'); const f1 = el('div', 'form');
      f1.append(field('№ ТКП', inp('no')), field('Дата', inp('date', '', 'date')), field('Кому (организация)', inp('to', 'ООО «…»')), field('Кому (должность, ФИО — необязательно)', inp('toPerson', 'Директору … И.И. Иванову')),
        field('Вступление', ta('greeting', 2), 'full'), field('Предмет', inp('subject'), 'full'), field('Объект (курсивом)', ta('object', 3), 'full'), field('Основание', inp('basis', 'согласно Техническому заданию от …'), 'full'));
      s1.append(f1);
      // 2. состав работ
      const s2 = sec('2. Что входит в объём: позиции и цены'); const itBox = el('div', 'tkp-items'); s2.append(el('p', 'note', 'Отметьте нужные позиции. Цена — без НДС, дни — длительность. «‖» — начать одновременно с предыдущей позицией. Разделы рабочего проекта идут параллельно в общем сроке группы.'), itBox);
      const drawItems = () => {
        itBox.replaceChildren(); const groups = [...new Set(T.items.map((x) => x.group || 'Прочее'))];
        groups.forEach((g) => {
          const gd = el('div', 'tkp-grp'); const gh = el('div', 'tkp-gh'); gh.append(elR('b', null, g));
          if (g in T.groups) { const gi = el('input', 'ctl num'); gi.type = 'number'; gi.min = 0; gi.value = T.groups[g] ?? ''; gi.title = 'Общий срок группы, дней'; gi.setAttribute('aria-label', `Срок группы ${g}, дней`); gi.addEventListener('input', () => { T.groups[g] = gi.value === '' ? null : Number(gi.value); upd(); }); gh.append(el('span', 'note', 'срок группы'), gi); }
          gd.append(gh);
          T.items.filter((x) => (x.group || 'Прочее') === g).forEach((x) => {
            const row = el('div', 'tkp-it' + (x.on ? ' on' : '')); const c = el('input'); c.type = 'checkbox'; c.checked = x.on; c.setAttribute('aria-label', x.text);
            const tx = el('input', 'ctl'); tx.value = x.text; tx.setAttribute('aria-label', 'Наименование');
            const pr = el('input', 'ctl num'); pr.type = 'number'; pr.min = 0; pr.step = 1000; pr.placeholder = 'цена'; pr.value = x.price ?? ''; pr.setAttribute('aria-label', 'Цена без НДС');
            const dy = el('input', 'ctl num tkp-dy'); dy.type = 'number'; dy.min = 0; dy.placeholder = 'дн.'; dy.value = x.days ?? ''; dy.setAttribute('aria-label', 'Дней');
            const pa = el('button', 'btn sm ' + (x.par ? 'primary' : 'ghost'), '‖'); pa.type = 'button'; pa.title = 'Начать одновременно с предыдущей'; pa.setAttribute('aria-pressed', String(!!x.par));
            const rs = el('select', 'ctl'); rs.append(new Option('GASTEC', 'GASTEC'), new Option('Заказчик', 'Заказчик')); rs.value = x.resp || 'GASTEC'; rs.setAttribute('aria-label', 'Ответственный');
            c.addEventListener('change', () => { x.on = c.checked; row.classList.toggle('on', x.on); upd(); });
            tx.addEventListener('input', () => { x.text = tx.value; upd(); });
            pr.addEventListener('input', () => { x.price = pr.value === '' ? null : Number(pr.value); if (pr.value !== '' && !x.on) { x.on = true; c.checked = true; row.classList.add('on'); } upd(); });
            dy.addEventListener('input', () => { x.days = dy.value === '' ? null : Number(dy.value); upd(); });
            pa.addEventListener('click', () => { x.par = !x.par; pa.className = 'btn sm ' + (x.par ? 'primary' : 'ghost'); pa.setAttribute('aria-pressed', String(x.par)); upd(); });
            rs.addEventListener('change', () => { x.resp = rs.value; upd(); });
            row.append(c, tx, pr, dy, pa, rs); gd.append(row);
          });
          itBox.append(gd);
        });
        const add = el('div', 'tkp-add'); const ag = el('input', 'ctl'); ag.placeholder = 'Группа (необязательно)'; ag.setAttribute('list', 'tkp-groups'); const dl = el('datalist'); dl.id = 'tkp-groups'; groups.forEach((g) => dl.append(optR(g, g)));
        const at = el('input', 'ctl'); at.placeholder = 'Своя позиция: что делаем'; const ab = el('button', 'btn sm', '+ Добавить'); ab.type = 'button';
        ab.addEventListener('click', () => { if (!at.value.trim()) return; T.items.push({ id: 'C' + Date.now(), group: ag.value.trim() || 'Дополнительно', text: at.value.trim(), price: null, days: null, on: true, par: false, resp: 'GASTEC' }); drawItems(); upd(); });
        add.append(ag, dl, at, ab); itBox.append(add);
      };
      if (!T.items.length) { const p = el('p', 'rq-empty-lib', 'Справочник ТКП пуст: загрузите файл Excel кнопкой «Импорт из Excel» в реестре или добавьте свои позиции ниже.'); itBox.before(p); }
      drawItems();
      // 3. цена
      const s3 = sec('3. Цена и НДС'); const f3 = el('div', 'form');
      const vm = select('tkp-vat', [new Option('Итог с учётом НДС', 'with'), new Option('Без НДС', 'without'), new Option('Без НДС + НДС + итого', 'both')], T.vatMode); bind(vm, 'vatMode');
      const vr = el('input', 'ctl num'); vr.type = 'number'; vr.min = 0; vr.max = 30; vr.value = T.vatRate; bind(vr, 'vatRate', Number);
      const cu = select('tkp-cur', ['сум', 'USD'], T.cur); bind(cu, 'cur');
      const sh = select('tkp-show', [new Option('Позиции — отдельным приложением', 'appendix'), new Option('Позиции — таблицей в письме', 'body'), new Option('Только итоговая сумма', 'total')], T.showItems); bind(sh, 'showItems');
      const mn = el('input', 'ctl num'); mn.type = 'number'; mn.min = 0; mn.step = 1000; mn.value = T.manual ?? ''; mn.placeholder = 'если позиции без цен'; mn.addEventListener('input', () => { T.manual = mn.value === '' ? null : Number(mn.value); upd(); });
      const mv = select('tkp-mv', [new Option('сумма вручную — с НДС', '1'), new Option('сумма вручную — без НДС', '0')], T.manualVat ? '1' : '0'); mv.addEventListener('change', () => { T.manualVat = mv.value === '1'; upd(); });
      f3.append(field('Как показать цену', vm), field('Ставка НДС, %', vr), field('Валюта', cu), field('Позиции с ценами', sh), field('Сумма вручную', mn), field('Сумма вручную включает', mv), chk(T, 'words', 'Писать сумму прописью'));
      s3.append(f3);
      // 4. срок, оплата
      const s4 = sec('4. Сроки и оплата'); const f4 = el('div', 'form');
      const tu = select('tkp-tu', ['календарных', 'рабочих'], T.termUnit); bind(tu, 'termUnit');
      const auto = el('button', 'btn sm', 'Взять из графика'); auto.type = 'button'; auto.addEventListener('click', () => { const C = tkpCalc(T); if (!C.span) return toast('Сначала укажите дни у позиций.'); T.termFrom = String(C.span); T.termTo = ''; tf.value = T.termFrom; tt.value = ''; upd(); });
      const tf = inp('termFrom', 'от', 'number'); const tt = inp('termTo', 'до (необязательно)', 'number');
      const pays = tkpLib().pays; const ps = select('tkp-pay', [...pays.map((p) => optR(p.text, p.text)), new Option('Свой вариант…', '__own')], pays.some((p) => p.text === T.pay) ? T.pay : '__own');
      const pt = ta('pay', 2); ps.addEventListener('change', () => { if (ps.value !== '__own') { T.pay = ps.value; pt.value = ps.value; upd(); } else pt.focus(); });
      pt.addEventListener('input', () => { ps.value = pays.some((p) => p.text === pt.value) ? pt.value : '__own'; });
      f4.append(field('Название строки', inp('termLabel')), field('Дни', tu), field('Срок от', tf), field('Срок до', tt), field('После чего', inp('termTail'), 'full'), auto, field('Условия оплаты (части через «;» — станут списком)', ps, 'full'), field('Текст условий', pt, 'full'));
      s4.append(f4);
      // 5. примечания, приложения
      const s5 = sec('5. Примечания и приложения', false); const nl = el('div', 'tp-list'); T.notes.forEach((n) => nl.append(chk(n, 'on', n.text, null, true)));
      const al = el('div', 'tp-list'); T.apps.forEach((n) => al.append(chk(n, 'on', n.text, null, true)));
      s5.append(el('h4', null, 'Примечания'), nl, field('Свои примечания (каждое с новой строки)', ta('notesExtra', 2)), el('h4', null, 'Приложения'), al, field('Свои приложения (каждое с новой строки)', ta('appsExtra', 2)));
      // 6. графики
      const s6 = sec('6. Графики'); const f6 = el('div', 'form');
      const gs = inp('gStart', '', 'date');
      f6.append(chk(T, 'gTable', 'Предварительный график работ со стоимостью (таблица, как Приложение №1)'), chk(T, 'gGantt', 'Календарный график (диаграмма Ганта по неделям, альбомный лист)'), chk(T, 'gCost', 'Стоимость в календарном графике'), field('Дата начала (пусто — «день 1»)', gs));
      s6.append(f6);
      // 7. подпись
      const s7 = sec('7. Подпись', false); const f7 = el('div', 'form');
      const sp = (k, label) => { const i = el('input', 'ctl'); i.value = T.signer[k]; i.addEventListener('input', () => { T.signer[k] = i.value; upd(); }); return field(label, i); };
      f7.append(sp('pos', 'Должность'), sp('org', 'Организация'), sp('fio', 'ФИО'));
      s7.append(f7, el('p', 'note', canSign() ? 'Подпись и печать ставятся кнопкой «PDF с подписью и печатью» — автоматически справа от строки «Директор».' : 'Подпись и печать может поставить только руководитель.'));
      // footer
      const foot = el('div', 'modal-foot tkp-foot'); const sumLine = el('span', 'note tkp-sum'); const err = el('span', 'err');
      const bPdf = el('button', 'btn', 'Скачать PDF'); bPdf.type = 'button';
      const bSig = el('button', 'btn', 'PDF с подписью и печатью'); bSig.type = 'button'; bSig.hidden = !canSign();
      const bSave = el('button', 'btn primary', 'Сохранить ТКП в реестр'); bSave.type = 'button';
      const bClose = el('button', 'btn ghost', 'Закрыть'); bClose.type = 'button'; bClose.addEventListener('click', close);
      foot.append(sumLine, err, bClose, bPdf, bSig, bSave); m.append(foot);
      const busy = async (btn, label, fn) => { const t0 = btn.textContent; btn.disabled = true; btn.textContent = label; err.textContent = ''; try { await fn(); } catch (e) { err.textContent = e && e.userText ? e.userText : 'Ошибка: ' + (e.message || e); } finally { btn.disabled = false; btn.textContent = t0; } };
      bPdf.addEventListener('click', () => busy(bPdf, 'Готовлю…', async () => { const bytes = await tkpPdfBytes(tkpModel(T)); await saveFile(tkpFileName(T, false), new Blob([bytes], { type: 'application/pdf' })); }));
      bSig.addEventListener('click', () => busy(bSig, 'Готовлю…', async () => { const bytes = await tkpPdfBytes(tkpModel(T)); openSign({ bytes, name: tkpFileName(T, false), fio: T.signer.fio }); }));
      bSave.addEventListener('click', () => busy(bSave, 'Сохраняю…', async () => {
        const M = tkpModel(T); const C = M.C; if (!C.total) throw userErr('Нет суммы: отметьте позиции с ценой или введите сумму вручную.');
        const out = await apiFetch(`${API.requests}${encodeURIComponent(r.no)}/offers/`, { data: T, text: priceSentence(T, C).replace(/\.$/, '') });
        toast(`ТКП №${T.no} сохранено, версия ${out.ver}`); refreshAll();
      }));
      upd();
    });
  }

  // ---------- signature and seal on any PDF
  async function pdfJsLib() {
    await loadScript(PDFJS_W, 'pdfjsWorker'); const lib = await loadScript(PDFJS, 'pdfjsLib');
    lib.GlobalWorkerOptions.workerSrc = PDFJS_W; return lib;
  }
  // Картинки приходят только тем, кому разрешено подписывать; каждое использование пишется в журнал аудита.
  async function sealImages(doc) {
    const out = await apiFetch(API.seal, { doc });
    if (!out.ready) { const e = userErr('Подпись и печать ещё не загружены.'); e.noSeal = true; e.canUpload = out.canUpload; throw e; }
    const b = (s) => Uint8Array.from(atob(s), (ch) => ch.charCodeAt(0));
    const signUrl = 'data:image/png;base64,' + out.images.sign, sealUrl = 'data:image/png;base64,' + out.images.seal;
    const im = new Image(); im.src = signUrl; try { await im.decode(); } catch (e) { throw userErr('Картинка подписи не читается. Загрузите её заново.'); }
    return { seal: b(out.images.seal), sign: b(out.images.sign), sealUrl, signUrl, ratio: im.naturalWidth / im.naturalHeight || 224 / 187 };
  }
  const MM = 72 / 25.4;
  // geometry from the anchor (left end of name, baseline y, right end of «GASTEC PROJECT»), in PDF points
  function placeFrom(a, ratio) {
    const sigH = 18 * MM, sigW = sigH * ratio, seal = 35 * MM;
    const xA = a.xA != null && a.xA < a.xName - 40 ? a.xA : a.xName - 190;
    const sigCx = Math.min((xA + a.xName) / 2 + 18, a.xName - sigW / 2 - 6);
    const sig = { x: sigCx - sigW / 2, y: a.y - 13, w: sigW, h: sigH };
    return { page: a.page, sig, seal: { cx: sig.x - seal / 2 + 20, cy: a.y - 8, d: seal } };
  }
  async function findAnchors(lib, bytes, fio) {
    const doc = await lib.getDocument({ data: bytes.slice(0), isEvalSupported: false }).promise; const out = [];
    const key = str(fio).split(/\s+/).pop().replace(/[^А-Яа-яЁёA-Za-z]/g, '') || 'Саидходжаев';
    for (let p = 1; p <= doc.numPages; p++) {
      const page = await doc.getPage(p); const tc = await page.getTextContent();
      const items = tc.items.filter((it) => it.str && it.str.trim());
      items.filter((it) => it.str.includes(key)).forEach((it) => {
        const y = it.transform[5]; let x = it.transform[4];
        const idx = it.str.indexOf(str(fio).split(/\s+/)[0] || key); if (idx > 0 && it.width) x += it.width * idx / it.str.length;
        const org = items.filter((o) => /PROJEC/.test(o.str) && Math.abs(o.transform[5] - y) < 9 && o.transform[4] < x).sort((u, v) => v.transform[4] - u.transform[4])[0];
        out.push({ page: p, xName: x, y, xA: org ? org.transform[4] + org.width : null });
      });
    }
    return { doc, anchors: out };
  }
  async function signBytes(bytes, places, imgs, opts) {
    const PL = await loadScript(PDFLIB, 'PDFLib'); const pdf = await PL.PDFDocument.load(bytes);
    const seal = await pdf.embedPng(imgs.seal), sign = await pdf.embedPng(imgs.sign); const pages = pdf.getPages();
    places.forEach((P) => {
      const pg = pages[P.page - 1]; if (!pg) return;
      if (opts.sign) pg.drawImage(sign, { x: P.sig.x, y: P.sig.y, width: P.sig.w, height: P.sig.h });
      if (opts.seal) { const d = P.seal.d, th = -10 * Math.PI / 180; const ox = P.seal.cx - (d / 2 * Math.cos(th) - d / 2 * Math.sin(th)), oy = P.seal.cy - (d / 2 * Math.sin(th) + d / 2 * Math.cos(th)); pg.drawImage(seal, { x: ox, y: oy, width: d, height: d, rotate: PL.degrees(-10), opacity: 0.93 }); }
    });
    return pdf.save();
  }
  function openSign(pre) {
    if (!canSign()) return toast('Подпись и печать может ставить только руководитель.');
    modal('Подпись и печать директора на PDF', (m, close) => {
      m.classList.add('sg-modal');
      const top = el('div', 'sg-top'); const fi = el('input', 'ctl'); fi.type = 'file'; fi.accept = 'application/pdf,.pdf'; fi.id = 'sg-file';
      const st = { bytes: pre?.bytes || null, name: pre?.name || '', fio: pre?.fio || libSetting('Подпись: ФИО', 'А.А. Саидходжаев'), places: [], seal: true, sign: true, doc: null, imgs: null };
      const c1 = el('label', 'tp-item'); const k1 = el('input'); k1.type = 'checkbox'; k1.checked = true; c1.append(k1, el('span', null, 'Печать организации'));
      const c2 = el('label', 'tp-item'); const k2 = el('input'); k2.type = 'checkbox'; k2.checked = true; c2.append(k2, el('span', null, 'Подпись'));
      if (!pre) top.append(field('PDF-файл', fi));
      top.append(c1, c2); m.append(top);
      const info = el('p', 'note', pre ? 'Ищу строку с ФИО директора…' : 'Выберите PDF. Подпись и печать встанут справа от «Директор ООО «GASTEC PROJECT»» на каждой странице, где есть ФИО директора. Нажмите на страницу, чтобы поставить печать в другое место.'); m.append(info);
      const pagesBox = el('div', 'sg-pages'); m.append(pagesBox);
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); const cancel = el('button', 'btn ghost', 'Закрыть'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const go = el('button', 'btn primary', 'Скачать подписанный PDF'); go.type = 'button'; go.disabled = true; foot.append(err, cancel, go); m.append(foot);
      const draw = async () => {
        pagesBox.replaceChildren(); const lib = await pdfJsLib();
        for (let p = 1; p <= st.doc.numPages; p++) {
          const page = await st.doc.getPage(p); const vp0 = page.getViewport({ scale: 1 }); const scale = Math.min(1.1, 520 / vp0.width); const vp = page.getViewport({ scale });
          const box = el('div', 'sg-page'); const cv = el('canvas'); const dpr = Math.min(2, window.devicePixelRatio || 1); cv.width = vp.width * dpr; cv.height = vp.height * dpr; cv.style.width = vp.width + 'px'; cv.style.height = vp.height + 'px';
          await page.render({ canvasContext: cv.getContext('2d'), viewport: page.getViewport({ scale: scale * dpr }) }).promise;
          box.append(cv, el('span', 'sg-pn', `стр. ${p}`)); pagesBox.append(box);
          const overlay = () => {
            box.querySelectorAll('.sg-ov').forEach((x) => x.remove()); const P = st.places.find((q) => q.page === p); if (!P) return;
            const H = vp0.height; const mk = (src, x, y, w, h, rot) => { const i = el('img', 'sg-ov'); i.src = src; i.alt = ''; Object.assign(i.style, { left: x * scale + 'px', top: (H - y - h) * scale + 'px', width: w * scale + 'px', height: h * scale + 'px', transform: rot ? 'rotate(10deg)' : '' }); box.append(i); };
            if (st.sign) mk(st.imgs.signUrl, P.sig.x, P.sig.y, P.sig.w, P.sig.h);
            if (st.seal) mk(st.imgs.sealUrl, P.seal.cx - P.seal.d / 2, P.seal.cy - P.seal.d / 2, P.seal.d, P.seal.d, true);
            const rm = el('button', 'btn sm sg-rm sg-ov', 'Убрать'); rm.type = 'button'; rm.addEventListener('click', (e) => { e.stopPropagation(); st.places = st.places.filter((q) => q.page !== p); overlay(); sync(); }); box.append(rm);
          };
          cv.addEventListener('click', (e) => {
            const rc = cv.getBoundingClientRect(); const x = (e.clientX - rc.left) / scale, y = vp0.height - (e.clientY - rc.top) / scale;
            const seal = 35 * MM; const sigH = 18 * MM, sigW = sigH * st.imgs.ratio; const P = { page: p, seal: { cx: x, cy: y, d: seal }, sig: { x: x + seal / 2 - 20, y: y - 5, w: sigW, h: sigH } };
            st.places = [...st.places.filter((q) => q.page !== p), P]; overlay(); sync();
          });
          box.__ov = overlay; overlay();
        }
        void lib;
      };
      const sync = () => { go.disabled = !st.places.length || (!st.seal && !st.sign); info.textContent = st.places.length ? `Подпись и печать: ${st.places.map((q) => 'стр. ' + q.page).join(', ')}. Нажмите на страницу, чтобы переставить.` : 'ФИО директора в файле не найдено. Нажмите на страницу там, где должна стоять печать.'; };
      const load = async () => {
        try {
          err.textContent = ''; st.imgs = await sealImages(st.name); const lib = await pdfJsLib();
          const { doc, anchors } = await findAnchors(lib, st.bytes, st.fio); st.doc = doc; st.places = anchors.map((x) => placeFrom(x, st.imgs.ratio));
          await draw(); sync();
        } catch (e) {
          if (e && e.noSeal) { info.textContent = ''; showUpload(e.canUpload); return; }
          err.textContent = e && e.userText ? e.userText : 'Не удалось открыть PDF: ' + (e.message || e);
        }
      };
      const showUpload = (can) => {
        pagesBox.replaceChildren(); if (!can) { err.textContent = 'Подпись и печать ещё не загружены. Их загружает администратор.'; return; }
        const box = el('div', 'sg-upload'); box.append(el('b', null, 'Загрузите подпись и печать'), el('p', 'note', 'Две картинки PNG с прозрачным фоном, до 2 МБ. Они хранятся в зашифрованном виде.'));
        const mk = (label) => { const i = el('input', 'ctl'); i.type = 'file'; i.accept = 'image/png'; box.append(field(label, i)); return i; };
        const iSign = mk('Подпись (PNG)'), iSeal = mk('Печать (PNG)'); const bUp = el('button', 'btn primary', 'Загрузить'); bUp.type = 'button'; box.append(bUp); pagesBox.append(box);
        bUp.addEventListener('click', async () => {
          if (!iSign.files[0] || !iSeal.files[0]) { err.textContent = 'Выберите обе картинки.'; return; }
          bUp.disabled = true; err.textContent = '';
          try { const fd = new FormData(); fd.append('sign', iSign.files[0]); fd.append('seal', iSeal.files[0]); await apiFetch(API.seal + 'upload/', fd); toast('Подпись и печать загружены'); if (st.bytes) load(); else { pagesBox.replaceChildren(); info.textContent = 'Выберите PDF.'; } }
          catch (e) { err.textContent = errText(e); bUp.disabled = false; }
        });
      };
      k1.addEventListener('change', () => { st.seal = k1.checked; $$('.sg-page', pagesBox).forEach((b) => b.__ov && b.__ov()); sync(); });
      k2.addEventListener('change', () => { st.sign = k2.checked; $$('.sg-page', pagesBox).forEach((b) => b.__ov && b.__ov()); sync(); });
      fi.addEventListener('change', async () => { const f = fi.files[0]; if (!f) return; if (f.size > 40e6) { err.textContent = 'Файл больше 40 МБ.'; return; } st.name = f.name; st.bytes = new Uint8Array(await f.arrayBuffer()); info.textContent = 'Ищу строку с ФИО директора…'; load(); });
      go.addEventListener('click', async () => {
        go.disabled = true; const t0 = go.textContent; go.textContent = 'Готовлю…'; err.textContent = '';
        try { const out = await signBytes(st.bytes, st.places, st.imgs, { seal: st.seal, sign: st.sign }); const base = st.name.replace(/\.pdf$/i, ''); await saveFile(base + '-signed.pdf', new Blob([out], { type: 'application/pdf' })); }
        catch (e) { err.textContent = e && e.userText ? e.userText : 'Не получилось: ' + (e.message || e); }
        finally { go.disabled = false; go.textContent = t0; }
      });
      if (pre) load(); else if (canManageSeal()) { const b = el('button', 'btn sm ghost', 'Заменить подпись и печать'); b.type = 'button'; b.addEventListener('click', () => showUpload(true)); top.append(b); }
    });
  }

  // ---------- import of the Google Sheets file saved as Excel
  function openImport() {
    modal('Импорт запросов из Excel', (m, close) => {
      m.append(el('p', 'note', 'Скачайте финансовую Google Таблицу как Excel (Файл → Скачать → .xlsx) и выберите файл. Загрузятся листы «Запросы», «Контакты запросов», «ТКП», «Справочник ТКП» и «Журнал запросов».'), el('p', 'note', 'Запросы, которые уже есть на платформе, не меняются. Позиции и цены справочника обновятся по файлу.'));
      const fi = el('input', 'ctl'); fi.type = 'file'; fi.id = 'rq-import-file'; fi.accept = '.xlsx'; m.append(field('Файл Excel (.xlsx)', fi));
      const foot = el('div', 'modal-foot'); const err = el('span', 'err'); const cancel = el('button', 'btn ghost', 'Отмена'); cancel.type = 'button'; cancel.addEventListener('click', close);
      const go = el('button', 'btn primary', 'Загрузить'); go.type = 'button'; foot.append(err, cancel, go); m.append(foot);
      go.addEventListener('click', async () => {
        if (!fi.files[0]) { err.textContent = 'Выберите файл Excel (.xlsx).'; return; }
        go.disabled = true; go.textContent = 'Загружаю…'; err.textContent = '';
        try {
          const fd = new FormData(); fd.append('file', fi.files[0]); const c = (await apiFetch(API.requests + 'import/', fd)).counts;
          close(); toast(`Загружено: запросов ${c.requests}, контактов ${c.contacts}, ТКП ${c.offers}, строк справочника ${c.library}. Уже были: ${c.skipped}`); refreshAll();
        } catch (e) { err.textContent = errText(e); go.disabled = false; go.textContent = 'Загрузить'; }
      });
    });
  }

  // ---------- wiring
  $$('#rq-filter button').forEach((b) => b.addEventListener('click', () => { S.rqF = b.dataset.f; renderReq(); }));
  $('#rq-search').addEventListener('input', renderReq);
  $('#rq-add').addEventListener('click', () => openReq(null));
  $('#rq-sign').addEventListener('click', () => openSign(null));
  $('#rq-import').addEventListener('click', () => openImport());
  if (DS.libUrl) { const a = $('#rq-lib'); a.href = DS.libUrl; a.hidden = false; }
  return { renderReq };
};
