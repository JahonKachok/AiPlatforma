"""Apply the office's approved named page setups, title blocks and fonts to a DWG revision."""
import json
from pathlib import Path

from ..common import Output
from .autocad import Drawing, _paper_layouts


def _stamp(layout, rule, fields):
    # The approved block definition is supplied by the project's drawing template.
    name = rule["stamp_block"]
    stamps = [entity for entity in layout.Block if entity.ObjectName == "AcDbBlockReference"
              and entity.EffectiveName.casefold() == name.casefold()]
    if len(stamps) > 1:
        raise ValueError(f"{layout.Name}: multiple title blocks named {name}")
    if stamps:
        stamp = stamps[0]
    else:
        import pythoncom
        from win32com.client import VARIANT

        point = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, rule["origin"])
        stamp = layout.Block.InsertBlock(point, name, 1.0, 1.0, 1.0, 0.0)
    attrs = {a.TagString.casefold(): a for a in stamp.GetAttributes()} if stamp.HasAttributes else {}
    for tag, field in rule["attributes"].items():
        att = attrs[tag.casefold()]
        if not att.TextString.strip():
            att.TextString = fields[field]


def apply_profile(doc, profile, job):
    sheets = [layout for layout in _paper_layouts(doc) if not layout.ModelType]
    if not sheets or not profile["fonts"]:
        raise ValueError("A paper layout and an approved font map are required")
    for style, font in profile["fonts"].items():
        if not font:
            raise ValueError(f"Missing font for {style}")
        doc.TextStyles.Item(style).FontFile = font
    for sheet in sheets:
        rule = profile.get("layouts", {}).get(sheet.Name) or profile.get("media", {}).get(sheet.CanonicalMediaName)
        if not rule:
            raise ValueError(f"No approved format for {sheet.Name} ({sheet.CanonicalMediaName})")
        sheet.CopyFrom(doc.PlotConfigurations.Item(rule["page_setup"]))
        fields = {key: job.get(key, "") for key in ("project", "object", "discipline", "executor")}
        _stamp(sheet, rule, {**fields, "sheet": sheet.Name, "drawing": Path(job["file_name"]).stem})
    return len(sheets)


def format_drawing(job, source, ctx):
    with ctx.gost_profile.open(encoding="utf-8-sig") as handle:
        profile = json.load(handle)
    with Drawing(source, save=True) as doc:
        count = apply_profile(doc, profile, job)
    return Output(file=source, result={"summary": f"Оформлено листов: {count}", "sheets": count})
