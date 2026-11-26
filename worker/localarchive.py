"""Lokal papkada fayl joylash: Loyiha/Obyekt/Intizom/<fayl>; shu nomli eski fayl
o'chirilmaydi — asl nomi bilan «Old/<vaqt>/» papkasiga ko'chiriladi."""
import re
import shutil
from datetime import datetime
from pathlib import Path

_UNSAFE = re.compile(r'[\\/:*?"<>|]+')


def _safe(part):
    return _UNSAFE.sub("_", str(part)).strip(" .") or "_"


def place(path, root, parts, now=None):
    folder = Path(root).joinpath(*(_safe(p) for p in parts if p))
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / Path(path).name
    if target.exists():
        # Nom o'zgarmaydi: har eski nusxa Old/<vaqt>/ ichida asl nomi bilan.
        stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
        old = folder / "Old" / stamp
        old.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(old / target.name))
    shutil.copy2(str(path), str(target))
    return target
