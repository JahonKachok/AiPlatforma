"""Chizma matnlari bilan ishlash uchun sof funksiyalar (AutoCAD/Excel'siz test qilinadi).

- needs_translation: raqam, o'q belgisi, kod kabi matnlarga tegmaslik
- max_len: tarjima ramkadan chiqmasligi uchun belgilar chegarasi
- split_mtext / join_mtext: MText formatlash kodlarini (\\P, {\\fArial|b1;...})
  saqlagan holda faqat matn bo'laklarini tarjima qilish
- overlaps: matn to'rtburchaklari ustma-ust tushishini aniqlash
- shrink_factor: uzun tarjimani WidthFactor bilan siqish
"""
import math
import re

_LETTER = re.compile(r"[A-Za-zА-Яа-яЁё一-鿿]")
# Faqat kod/belgi: «A-1», «Ø20», «М1:100», «+0.000», «КЖ-01», «2-2»
_CODE_ONLY = re.compile(r"^[\s\dA-ZА-ЯЁ.,:;+\-–—=×xØ%°/\\()\[\]#№'\"]{0,12}$")
_MTEXT_CODE = re.compile(r"(\\[PpNn~]|\\[A-Za-z][^;\\{}]*;|[{}])")

# Tarjima kenglik koeffitsiyenti: xitoy ieroglifi ~2 lotin harfi kengligida.
WIDTH_PER_CHAR = {"zh": 1.8, "ru": 1.0, "en": 0.95}


def needs_translation(text):
    text = (text or "").strip()
    if not text or not _LETTER.search(text):
        return False
    return not _CODE_ONLY.match(text)


def visual_len(text, lang):
    """Matnning taxminiy ko'rinish kengligi (lotin harfi = 1)."""
    if lang == "zh":
        return sum(WIDTH_PER_CHAR["zh"] if "一" <= ch <= "鿿" else 1 for ch in text)
    return len(text) * WIDTH_PER_CHAR.get(lang, 1.0)


def max_len(original, source_lang_hint, target_lang, slack=1.1):
    """Tarjimaga ruxsat etilgan belgilar soni: asl matn kengligiga sig'sin."""
    width = visual_len(original, source_lang_hint) * slack
    per_char = WIDTH_PER_CHAR.get(target_lang, 1.0)
    return max(1, math.floor(width / per_char))


def detect_lang(text):
    if re.search(r"[一-鿿]", text):
        return "zh"
    if re.search(r"[А-Яа-яЁё]", text):
        return "ru"
    return "en"


def split_mtext(value):
    """MText -> [(is_code, bo'lak)]; faqat is_code=False bo'laklar tarjima qilinadi."""
    parts, pos = [], 0
    for m in _MTEXT_CODE.finditer(value):
        if m.start() > pos:
            parts.append((False, value[pos:m.start()]))
        parts.append((True, m.group(0)))
        pos = m.end()
    if pos < len(value):
        parts.append((False, value[pos:]))
    return parts


def join_mtext(parts):
    return "".join(text for _code, text in parts)


def overlaps(boxes, min_area=0.0):
    """boxes: [(id, x1, y1, x2, y2)] -> [(id_a, id_b)] ustma-ust tushganlar.
    Kesishma maydoni ikkalasidan kichigining 10% idan katta bo'lsa — hisobga olinadi."""
    found = []
    items = sorted(boxes, key=lambda b: b[1])
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if b[1] >= a[3]:
                break  # x bo'yicha saralangan: keyingilar o'ngda
            w = min(a[3], b[3]) - max(a[1], b[1])
            h = min(a[4], b[4]) - max(a[2], b[2])
            if w <= 0 or h <= 0:
                continue
            area = w * h
            smaller = min((a[3] - a[1]) * (a[4] - a[2]), (b[3] - b[1]) * (b[4] - b[2]))
            if area > max(min_area, 0.1 * smaller):
                found.append((a[0], b[0]))
    return found


def shrink_factor(original_width, new_width, current=1.0, minimum=0.6):
    """Yangi matn eski kenglikka sig'ishi uchun WidthFactor (None — sig'maydi)."""
    if new_width <= original_width * 1.02 or new_width <= 0:
        return current
    factor = current * original_width / new_width
    return round(factor, 3) if factor >= minimum else None


STANDARD_SHEETS = {"A4": (210, 297), "A3": (297, 420), "A2": (420, 594), "A1": (594, 841), "A0": (841, 1189)}


def sheet_format(width_mm, height_mm, tol=3):
    """Varaq formati (ГОСТ 2.301): A0–A4 va ularning karrali kengaytmalari (A3x3...)."""
    w, h = sorted((width_mm, height_mm))
    for name, (sw, sh) in STANDARD_SHEETS.items():
        if abs(w - sw) <= tol and abs(h - sh) <= tol:
            return name
    for name, (sw, sh) in STANDARD_SHEETS.items():
        for k in range(2, 10):  # karrali (A3x3 = 420×891): qisqa tomon = formatning uzun tomoni, uzuni = qisqasi×k
            if abs(w - sh) <= tol and abs(h - sw * k) <= tol * k:
                return f"{name}x{k}"
    return None
