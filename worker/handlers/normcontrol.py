"""Normokontrol: PDF'dan mashina faktlarini yig'adi (format, ustma-ust matnlar,
ramkadan chiqqan matn), AI esa ulardan qisqa zamechaniyalar ro'yxatini tuzadi.
DWG bo'lsa avval AutoCAD orqali PDF qilinadi."""
from pypdf import PdfReader

from ..common import Output
from ..textfit import overlaps, sheet_format

PT_TO_MM = 25.4 / 72
FRAME_LEFT_MM, FRAME_OTHER_MM = 20, 5  # ГОСТ 2.104 ramka chetlari
MAX_FACTS = 25


def pdf_facts(path):
    sheets = []
    reader = PdfReader(str(path))
    for index, page in enumerate(reader.pages, start=1):
        box = page.mediabox
        w_mm, h_mm = float(box.width) * PT_TO_MM, float(box.height) * PT_TO_MM
        facts = []
        fmt = sheet_format(w_mm, h_mm)
        if fmt is None:
            facts.append(f"non-standard sheet size {w_mm:.0f}x{h_mm:.0f} mm")
        boxes, outside = [], 0

        def visit(text, cm, tm, font_dict, font_size, _boxes=boxes):
            text = (text or "").strip()
            if not text:
                return
            size = (font_size or 2.5) * abs(tm[0] or 1) * abs(cm[0] or 1)
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            _boxes.append((f"{text[:30]}#{len(_boxes)}", x, y, x + len(text) * size * 0.55, y + size))

        page.extract_text(visitor_text=visit)
        for _id, x1, y1, x2, y2 in boxes:
            if (x1 - float(box.left)) * PT_TO_MM < FRAME_LEFT_MM - 1 or (float(box.right) - x2) * PT_TO_MM < FRAME_OTHER_MM - 1:
                outside += 1
        if outside:
            facts.append(f"{outside} text item(s) outside the drawing frame")
        for a, b in overlaps(boxes)[:MAX_FACTS]:
            facts.append(f"overlapping text: '{a.split('#')[0]}' / '{b.split('#')[0]}'")
        if not boxes:
            facts.append("no text layer (scan?) — title block cannot be checked")
        sheets.append({"sheet": str(index), "format": fmt or "", "facts": facts})
    return sheets


def norm_control(job, source, ctx):
    pdf = source
    if source.suffix.lower() == ".dwg":
        from .autocad import Drawing, plot_pdf

        pdf = source.with_suffix(".pdf")
        with Drawing(source) as doc:
            plot_pdf(doc, pdf)
    sheets = pdf_facts(pdf)
    if not any(s["facts"] for s in sheets):
        return Output(result={"remarks": []})
    answer = ctx.ai("norm_control", {"file": job["file_name"], "sheets": [s for s in sheets if s["facts"]]})
    return Output(result={"remarks": answer.get("remarks", [])})
