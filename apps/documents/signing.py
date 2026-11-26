"""PDF'ga direktor imzosi va muhrini qo'yish (server tomonida, Telegram oqimi uchun).

Brauzerdagi ТКП imzolash (static/pult/pult-requests.js) bilan bir xil joylashuv:
imzo «Директор» so'zidan o'ngda, muhr imzo ustida −10° burilgan holda.
pypdf matn o'rnini topadi va sahifalarni birlashtiradi, reportlab esa shaffof
PNG'larni alohida qatlam (overlay) sahifaga chizadi.
"""
import io

MM = 72 / 25.4
SIGN_H = 18 * MM
SEAL_D = 35 * MM
SEAL_ROTATE = -10
LABEL = "Директор"


class LabelNotFound(Exception):
    """PDF'da «Директор» yozuvi topilmadi (yoki matn qatlami yo'q — skan)."""


def find_label(reader, label=LABEL):
    """[(sahifa_indeksi, x, y)] — har sahifada yozuvning oxirgi uchrashi
    (imzo qatori odatda pastda bo'ladi)."""
    found = []
    for index, page in enumerate(reader.pages):
        hits = []

        def visit(text, cm, tm, font_dict, font_size, _hits=hits):
            if label.lower() in (text or "").lower():
                # Matn koordinatasi: tm (matn matritsasi) × cm (joriy transformatsiya)
                x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
                y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
                # Taxminiy kenglik (shrift metrikasisiz): o'rtacha harf ~0.6 em
                width = len(text.rstrip()) * (font_size or 10) * abs(tm[0] or 1) * 0.6
                _hits.append((x + width, y))

        page.extract_text(visitor_text=visit)
        if hits:
            x, y = min(hits, key=lambda h: h[1])
            found.append((index, x, y))
    return found


def _overlay(width, height, x, y, sign_png, seal_png):
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    sign = ImageReader(io.BytesIO(sign_png))
    sw, sh = sign.getSize()
    sign_w = SIGN_H * (sw / sh if sh else 1.2)
    sign_x, sign_y = x + 12, y - SIGN_H * 0.35
    c.drawImage(sign, sign_x, sign_y, width=sign_w, height=SIGN_H, mask="auto")
    if seal_png:
        seal = ImageReader(io.BytesIO(seal_png))
        cx, cy = sign_x - SEAL_D / 2 + 20, y - 8
        c.saveState()
        c.translate(cx, cy)
        c.rotate(SEAL_ROTATE)
        c.drawImage(seal, -SEAL_D / 2, -SEAL_D / 2, width=SEAL_D, height=SEAL_D, mask="auto")
        c.restoreState()
    c.save()
    buf.seek(0)
    return buf


def sign_pdf(pdf_bytes, sign_png, seal_png=None, label=LABEL):
    """Imzolangan PDF baytlarini qaytaradi; yozuv topilmasa LabelNotFound."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(pdf_bytes))
    places = find_label(reader, label)
    if not places:
        raise LabelNotFound(label)
    writer = PdfWriter(clone_from=reader)
    for index, x, y in places:
        page = writer.pages[index]
        box = page.mediabox
        # Overlay sahifa ham shu foydalanuvchi koordinatalarida chiziladi (mediabox siljishi shart emas).
        overlay = PdfReader(_overlay(float(box.right), float(box.top), x, y, sign_png, seal_png))
        page.merge_page(overlay.pages[0])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
