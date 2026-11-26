"""AutoCAD COM avtomatizatsiyasi (pywin32): PDF, shtamp, tarjima.

Qoidalar (TZ):
- PDF har bir varaqning (Layout) o'z page setup'i bilan chiqadi — ramkadan
  chiqarilmaydi, format va masshtab o'zgartirilmaydi; faqat plotter
  «DWG To PDF.pc3» ga almashtiriladi.
- Shtamp: faqat bo'sh atributlar to'ldiriladi (qo'lda yozilgani o'chirilmaydi).
- Tarjima: fayl nomi o'zgarmaydi; matn ramkaga sig'masa WidthFactor
  kamaytiriladi; ustma-ust tushgan matnlar soni natijada qaytariladi.
"""
import time
from datetime import date
from pathlib import Path

from ..common import Output, RetryableError
from ..textfit import (
    detect_lang, join_mtext, max_len, needs_translation, overlaps, shrink_factor, split_mtext,
)

PDF_PLOTTER = "DWG To PDF.pc3"
RPC_REJECTED = (-2147418111, -2147417846)  # «Call was rejected by callee» — AutoCAD band
BATCH = 120


def _com(fn, *args, tries=20):
    """AutoCAD band bo'lsa COM chaqiruvini qayta urinadi."""
    import pywintypes

    for attempt in range(tries):
        try:
            return fn(*args)
        except pywintypes.com_error as exc:
            if exc.args and exc.args[0] in RPC_REJECTED and attempt < tries - 1:
                time.sleep(0.5)
                continue
            raise


class Drawing:
    """`with Drawing(path) as doc:` — DWG'ni ochadi va har holda yopadi."""

    def __init__(self, path, save=False):
        self.path, self.save = str(path), save

    def __enter__(self):
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        try:
            self.acad = win32com.client.GetActiveObject("AutoCAD.Application")
        except Exception:  # noqa: BLE001 — ishlamayotgan bo'lsa ishga tushiramiz
            try:
                self.acad = win32com.client.Dispatch("AutoCAD.Application")
            except Exception as exc:
                raise RetryableError(f"AutoCAD is not available: {exc}") from exc
        self.doc = _com(self.acad.Documents.Open, self.path)
        _com(self.doc.SetVariable, "BACKGROUNDPLOT", 0)
        return self.doc

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.save and exc_type is None:
                _com(self.doc.Save)
            _com(self.doc.Close, False)
        finally:
            import pythoncom

            pythoncom.CoUninitialize()


def _paper_layouts(doc):
    layouts = [doc.Layouts.Item(i) for i in range(doc.Layouts.Count)]
    paper = [lay for lay in layouts if lay.Name.lower() != "model"]
    return sorted(paper, key=lambda lay: lay.TabOrder) or layouts


def _iter_texts(doc):
    """(ent, turi) — barcha bloklardagi TEXT, MTEXT va blok atributlari."""
    for i in range(doc.Blocks.Count):
        block = doc.Blocks.Item(i)
        if not (block.IsLayout or not block.IsXRef):
            continue
        for ent in block:
            name = ent.ObjectName
            if name in ("AcDbText", "AcDbMText"):
                yield ent, name
            elif name == "AcDbBlockReference" and ent.HasAttributes:
                for att in ent.GetAttributes():
                    yield att, "AcDbAttribute"


def _box(ent):
    try:
        lo, hi = ent.GetBoundingBox()
        return lo[0], lo[1], hi[0], hi[1]
    except Exception:  # noqa: BLE001 — bo'sh matnda bbox yo'q
        return None


# ---------------------------------------------------------------- shtamp + PDF

def _fill_stamp(doc, job, ctx):
    attrs = {}
    for layout in _paper_layouts(doc):
        for ent in layout.Block:
            if ent.ObjectName == "AcDbBlockReference" and ent.HasAttributes:
                for att in ent.GetAttributes():
                    attrs.setdefault(att.TagString, []).append(att)
    if not attrs:
        return 0
    data = {
        "project": job.get("project", ""), "object": job.get("object", ""), "discipline": job.get("discipline", ""),
        "executor": job.get("executor", ""), "date": date.today().strftime("%m.%y"),
        "sheet_name": Path(job["file_name"]).stem,
    }
    answer = ctx.ai("printer", {"tags": sorted(attrs), "data": data})
    filled = 0
    for row in answer.get("fields", []):
        for att in attrs.get(row["tag"], []):
            if row["value"] and not att.TextString.strip():
                att.TextString = row["value"]
                filled += 1
    return filled


def plot_pdf(doc, out_pdf):
    """Har varaq o'z sozlamalari bilan PDF'ga, keyin bitta faylga birlashtiriladi."""
    from pypdf import PdfWriter

    parts = []
    for n, layout in enumerate(_paper_layouts(doc)):
        layout.ConfigName = PDF_PLOTTER
        doc.ActiveLayout = layout
        part = out_pdf.with_name(f"{out_pdf.stem}__{n}.pdf")
        if not _com(doc.Plot.PlotToFile, str(part)):
            raise RuntimeError(f"plot failed: {layout.Name}")
        parts.append(part)
    writer = PdfWriter()
    for part in parts:
        writer.append(str(part))
    writer.write(str(out_pdf))
    for part in parts:
        part.unlink(missing_ok=True)
    return out_pdf


def dwg_print(job, source, ctx):
    out_pdf = source.with_suffix(".pdf")
    with Drawing(source, save=True) as doc:
        filled = _fill_stamp(doc, job, ctx)
        plot_pdf(doc, out_pdf)
    return Output(file=out_pdf, source=source if filled else None,
                  result={"summary": f"Штамп: заполнено полей {filled}" if filled else ""})


# ---------------------------------------------------------------- tarjima

def dwg_translate(job, source, ctx):
    target = job["params"].get("target_lang") or "ru"
    with Drawing(source, save=True) as doc:
        items, ents = [], {}
        for n, (ent, kind) in enumerate(_iter_texts(doc)):
            value = ent.TextString
            parts = split_mtext(value) if kind == "AcDbMText" else [(False, value)]
            for k, (is_code, text) in enumerate(parts):
                if is_code or not needs_translation(text) or detect_lang(text) == target:
                    continue
                key = f"{n}.{k}"
                items.append({"id": key, "text": text, "max_len": max_len(text, detect_lang(text), target)})
                ents.setdefault(n, (ent, kind, parts, _box(ent)))
        translated = {}
        for i in range(0, len(items), BATCH):
            answer = ctx.ai("translator", {"target": target, "items": items[i:i + BATCH]})
            translated.update({row["id"]: row["text"] for row in answer.get("items", [])})
        changed, squeezed, boxes = 0, 0, []
        for n, (ent, kind, parts, old_box) in ents.items():
            new_parts = [(c, translated.get(f"{n}.{k}", t) if not c else t) for k, (c, t) in enumerate(parts)]
            ent.TextString = join_mtext(new_parts) if kind == "AcDbMText" else new_parts[0][1]
            changed += 1
            new_box = _box(ent)
            if old_box and new_box and kind != "AcDbMText":
                factor = shrink_factor(old_box[2] - old_box[0], new_box[2] - new_box[0], ent.ScaleFactor)
                if factor and factor != ent.ScaleFactor:
                    ent.ScaleFactor = factor  # TEXT/ATTRIB uchun WidthFactor
                    squeezed += 1
                    new_box = _box(ent)
            if new_box:
                boxes.append((n, *new_box))
        clashes = overlaps(boxes)
    summary = f"Переведено текстов: {changed}, сжато: {squeezed}, наложений: {len(clashes)}"
    return Output(file=source, result={"summary": summary, "overlaps": len(clashes)})
