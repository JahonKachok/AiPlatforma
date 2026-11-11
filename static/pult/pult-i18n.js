/* GASTEC Pult — interfeys tarjimasi (uz / en).
 *
 * Pult kodi (pult.js) ruscha yozilgan va ruscha so'zlar ma'lumot qiymati ham
 * bo'ladi: statuslar ('В работе'), qator turlari ('Объект'), select qiymatlari.
 * Shuning uchun kod ichidagi satrlar o'zgartirilmaydi — tarjima faqat matn
 * ekranga chiqayotgan paytda qilinadi: textContent / createTextNode / append /
 * new Option / placeholder·title·aria-label. Qiymatlar (option.value, input.value,
 * API'ga yuboriladigan ma'lumot) ruscha qoladi.
 *
 * Lug'at: pult-i18n-data.js — [ruscha, o'zbekcha, inglizcha] qatorlari.
 * {0}, {1}… — o'zgaruvchan qism (ism, sana, son); tarjimada tartibi boshqacha
 * bo'lishi mumkin. Til <html lang> dan olinadi (Django LANGUAGE_CODE);
 * ru (yoki noma'lum til) bo'lsa hech narsa o'zgarmaydi.
 */
(() => {
  'use strict';
  const LANG = (document.documentElement.lang || 'ru').slice(0, 2).toLowerCase();
  const COL = { uz: 1, en: 2 }[LANG];
  const API = {
    lang: LANG,
    t: (s) => s,
    months: null,
    locale: 'ru-RU',
    plural: null,
  };
  window.PULT_I18N = API;
  const DATA = window.PULT_I18N_DATA || [];
  if (!COL || !DATA.length) return;

  const CYR = /[А-Яа-яЁё]/;
  const PH = /\{(\d+)\}/g;
  const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const exact = new Map();
  const patterns = []; // to'liq matn: ^...$
  const pieces = []; // matn ichidagi bo'lak: ', сдано {0}', 'Пример:'
  const isPiece = (ru) => /^[,.·(;]\s?|^\s/.test(ru) || /[:«]$/.test(ru);

  for (const row of DATA) {
    const ru = row[0];
    const out = row[COL];
    if (!out || out === ru) continue;
    if (!ru.includes('{')) {
      exact.set(ru, out);
      if (isPiece(ru)) pieces.push({ ru, out });
      continue;
    }
    const order = [];
    const literal = ru.split(PH).filter((x, i) => i % 2 === 0).sort((a, b) => b.length - a.length)[0] || '';
    if (!CYR.test(literal)) continue; // '{0} · {1}' kabi umumiy shablonlar — tarjima kerak emas
    const body = esc(ru).replace(/\\\{(\d+)\\\}/g, (_, n) => { order.push(Number(n)); return '([\\s\\S]+?)'; });
    // '{0} от {1}', '{0} млн' kabi qisqa shablonlar faqat qisqa qiymatlarga (son, ism, sana)
    // qo'llanadi — aks holda boshqa uzun matnni «yutib» buzib qo'yardi.
    const short = ru.replace(PH, '').replace(/[\s\d\p{P}]/gu, '').length < 6;
    patterns.push({ re: new RegExp('^' + body + '$'), order, out, literal, short, len: ru.replace(PH, '').length });
    if (isPiece(ru)) {
      const pbody = esc(ru).replace(/\\\{(\d+)\\\}/g, () => '([^,·;()«»]+?)').replace(/\(\[\^,·;\(\)«»\]\+\?\)$/, '([^,·;()«»]+)');
      pieces.push({ re: new RegExp(pbody, 'g'), order, out, literal });
    }
  }
  // Uzunroq (aniqroq) shablon birinchi tekshiriladi.
  patterns.sort((a, b) => b.len - a.len);
  pieces.sort((a, b) => (b.ru || b.literal).length - (a.ru || a.literal).length);

  const fill = (out, order, groups, depth) => out.replace(PH, (_, n) => {
    const g = groups[order.indexOf(Number(n))];
    return g == null ? '' : translate(g, depth + 1);
  });

  const cache = new Map();
  function translate(s, depth = 0) {
    if (typeof s !== 'string' || !CYR.test(s)) return s;
    const hit = cache.get(s);
    if (hit !== undefined) return hit;
    const m = /^(\s*)([\s\S]*?)(\s*)$/.exec(s);
    const core = m[2];
    let r = exact.get(core);
    if (r === undefined) {
      for (const p of patterns) {
        if (!core.includes(p.literal)) continue;
        const g = p.re.exec(core);
        if (!g) continue;
        const groups = g.slice(1);
        if (p.short && groups.some((x) => x.length > 40 || CYR.test(x))) continue;
        r = fill(p.out, p.order, groups, depth);
        break;
      }
    }
    if (r === undefined && depth < 2) {
      // Bir nechta bo'lakdan yig'ilgan matn: 'Пример: ' + shifr, 'Сделано 50%' + ', сдано 12.05'.
      let t = core;
      for (const p of pieces) {
        if (p.re) { if (t.includes(p.literal)) t = t.replace(p.re, (...a) => fill(p.out, p.order, a.slice(1, 1 + p.order.length), depth)); }
        else if (t.includes(p.ru)) t = t.split(p.ru).join(p.out);
      }
      if (t !== core) r = translate(t, depth + 1);
    }
    if (r === undefined && depth < 3) {
      // [rol, loyihalar, sana].join(' · '), 'Смета: 01.11 → 05.11', ko'p qatorli title kabi
      // yig'ma matnlar: har bir bo'lak alohida.
      const parts = core.split(/(\n| · |: |, |; )/);
      if (parts.length > 1) {
        const tr = parts.map((x, i) => (i % 2 ? x : translate(x, depth + 1)));
        if (tr.some((x, i) => x !== parts[i])) r = tr.join('');
      }
    }
    const res = r === undefined ? s : m[1] + r + m[3];
    if (cache.size > 20000) cache.clear();
    cache.set(s, res);
    return res;
  }
  API.t = translate;
  API.months = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'].map((x) => exact.get(x) || x);
  API.locale = LANG === 'uz' ? 'uz-Latn-UZ' : 'en-GB';
  // Ruscha ko'plik shakllari (1 задача / 2 задачи / 5 задач) o'rniga: o'zbekchada
  // sondan keyin birlik, inglizchada 1 — birlik, qolgani — ko'plik.
  API.plural = (n, a, b, c) => translate(LANG === 'en' && Math.abs(n) !== 1 ? c : a);

  // ---------- DOM'ga ulash
  const SKIP = new Set(['SCRIPT', 'STYLE', 'TEXTAREA']);
  const ATTRS = ['placeholder', 'title', 'aria-label', 'alt'];

  const tc = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent');
  Object.defineProperty(Node.prototype, 'textContent', {
    configurable: true,
    enumerable: tc.enumerable,
    get: tc.get,
    set(v) {
      if (typeof v === 'string' && this.nodeType === 1) {
        if (SKIP.has(this.tagName)) return tc.set.call(this, v);
        // <option> qiymatsiz bo'lsa, qiymati matnidan olinadi — tarjima uni buzmasin.
        if (this.tagName === 'OPTION' && !this.hasAttribute('value')) this.setAttribute('value', v);
      }
      tc.set.call(this, translate(v));
    },
  });

  const ctn = Document.prototype.createTextNode;
  Document.prototype.createTextNode = function (v) { return ctn.call(this, translate(String(v))); };

  const wrapArgs = (proto, name) => {
    const orig = proto[name];
    if (typeof orig !== 'function') return;
    proto[name] = function (...args) {
      if (this.nodeType === 1 && SKIP.has(this.tagName)) return orig.apply(this, args);
      return orig.apply(this, args.map((a) => (typeof a === 'string' ? translate(a) : a)));
    };
  };
  ['append', 'prepend', 'before', 'after', 'replaceWith', 'replaceChildren'].forEach((n) => { wrapArgs(Element.prototype, n); });
  ['append', 'prepend', 'replaceChildren'].forEach((n) => { wrapArgs(DocumentFragment.prototype, n); });
  wrapArgs(CharacterData.prototype, 'before');
  wrapArgs(CharacterData.prototype, 'after');

  const NativeOption = window.Option;
  const TOption = function (text, value, defaultSelected, selected) {
    const v = value === undefined ? text : value;
    return new NativeOption(translate(text == null ? '' : String(text)), v, defaultSelected, selected);
  };
  TOption.prototype = NativeOption.prototype;
  window.Option = TOption;

  const sa = Element.prototype.setAttribute;
  Element.prototype.setAttribute = function (name, value) {
    return sa.call(this, name, ATTRS.includes(String(name).toLowerCase()) ? translate(String(value)) : value);
  };
  const wrapProp = (proto, prop) => {
    const d = Object.getOwnPropertyDescriptor(proto, prop);
    if (!d || !d.set) return;
    Object.defineProperty(proto, prop, { ...d, set(v) { d.set.call(this, translate(v)); } });
  };
  wrapProp(HTMLElement.prototype, 'title');
  wrapProp(HTMLInputElement.prototype, 'placeholder');
  wrapProp(HTMLTextAreaElement.prototype, 'placeholder');
  wrapProp(Element.prototype, 'ariaLabel');

  // Sahifa shabloni (_markup.html) va innerHTML bilan qo'shilgan qismlar.
  const translateTree = (root) => {
    if (root.nodeType === 3) {
      // Sahifa yuklanayotganda parser keyingi <script> (pult.js) matnini ham qo'shadi —
      // uni tarjima qilish kodni buzardi.
      const parent = root.parentNode;
      if (!parent || (parent.nodeType === 1 && SKIP.has(parent.tagName))) return;
      const t = translate(root.data);
      if (t !== root.data) root.data = t;
      return;
    }
    if (root.nodeType !== 1 || SKIP.has(root.tagName)) return;
    const els = [root, ...root.querySelectorAll('*')];
    for (const e of els) {
      for (const a of ATTRS) {
        const v = e.getAttribute(a);
        if (v && CYR.test(v)) { const t = translate(v); if (t !== v) sa.call(e, a, t); }
      }
      if (e.tagName === 'OPTION' && !e.hasAttribute('value')) sa.call(e, 'value', e.text);
    }
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => (n.parentElement && SKIP.has(n.parentElement.tagName) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
    });
    const texts = [];
    while (w.nextNode()) texts.push(w.currentNode);
    for (const n of texts) {
      if (!CYR.test(n.data)) continue;
      const t = translate(n.data);
      if (t !== n.data) n.data = t;
    }
  };
  document.title = translate(document.title);
  if (document.body) translateTree(document.body);
  new MutationObserver((list) => {
    for (const m of list) m.addedNodes.forEach((n) => { if (n.nodeType === 1 || n.nodeType === 3) translateTree(n); });
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
