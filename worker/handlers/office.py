"""Word va Excel: DOCX -> PDF (Sekretar), Excel tarjimasi."""
import shutil
import subprocess

from ..common import Output, RetryableError
from ..textfit import detect_lang, max_len, needs_translation

WD_FORMAT_PDF = 17
BATCH = 150


def docx_to_pdf(job, source, ctx):
    out = source.with_suffix(".pdf")
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        try:
            doc = word.Documents.Open(str(source), ReadOnly=True)
            doc.ExportAsFixedFormat(str(out), WD_FORMAT_PDF)
            doc.Close(False)
        finally:
            word.Quit()
            pythoncom.CoUninitialize()
    except ImportError:
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice:
            raise RetryableError("neither MS Word nor LibreOffice is installed")
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(source.parent), str(source)],
                       check=True, timeout=300)
    return Output(file=out)


def xlsx_translate(job, source, ctx):
    """Kataklar matni tarjima qilinadi; formulalar, raqamlar, varaq va fayl
    nomlari o'zgarmaydi."""
    from openpyxl import load_workbook

    target = job["params"].get("target_lang") or "ru"
    wb = load_workbook(source, keep_vba=source.suffix.lower() == ".xlsm")
    cells, items = {}, []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                value = cell.value
                if not isinstance(value, str) or value.startswith("=") or not needs_translation(value):
                    continue
                if detect_lang(value) == target:
                    continue
                key = f"{ws.title}!{cell.coordinate}"
                cells[key] = cell
                items.append({"id": key, "text": value, "max_len": max_len(value, detect_lang(value), target, 1.3)})
    done = 0
    for i in range(0, len(items), BATCH):
        answer = ctx.ai("translator", {"target": target, "items": items[i:i + BATCH]})
        for row in answer.get("items", []):
            cell = cells.get(row["id"])
            if cell is not None and row["text"]:
                cell.value = row["text"]
                done += 1
    wb.save(source)
    return Output(file=source, result={"summary": f"Переведено ячеек: {done}"})
