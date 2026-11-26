"""Ish turi -> bajaruvchi funksiya. Har biri (job, manba_fayl, ctx) -> Output."""


def _lazy(module, name):
    # pywin32 faqat kerakli ish kelganda yuklanadi (Excel/normokontrol uchun AutoCAD shart emas).
    def run(job, source, ctx):
        from importlib import import_module

        return getattr(import_module(f"{__name__}.{module}"), name)(job, source, ctx)
    return run


HANDLERS = {
    "gost_format": _lazy("gost", "format_drawing"),
    "dwg_print": _lazy("autocad", "dwg_print"),
    "dwg_translate": _lazy("autocad", "dwg_translate"),
    "xlsx_translate": _lazy("office", "xlsx_translate"),
    "docx_to_pdf": _lazy("office", "docx_to_pdf"),
    "norm_control": _lazy("normcontrol", "norm_control"),
}
