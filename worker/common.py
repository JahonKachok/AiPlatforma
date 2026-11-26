from dataclasses import dataclass, field
from pathlib import Path


class RetryableError(Exception):
    """Vaqtinchalik xato (AutoCAD band, fayl qulflangan, AI vaqtincha yo'q) — ish qayta navbatga."""


@dataclass
class Output:
    """Handler natijasi: file — asosiy natija (PDF, tarjima qilingan fayl);
    source — o'zgartirilgan asl fayl (masalan, shtamp to'ldirilgan DWG)."""

    file: Path | None = None
    source: Path | None = None
    result: dict = field(default_factory=dict)
