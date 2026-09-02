"""Fayl yuklash validatorlari."""
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class MaxFileSizeValidator:
    """Yuklanadigan fayl hajmini cheklaydi (megabaytlarda)."""

    def __init__(self, max_mb: int):
        self.max_mb = max_mb

    def __call__(self, value):
        if value.size > self.max_mb * 1024 * 1024:
            raise ValidationError(
                _("Fayl hajmi %(max)d MB dan oshmasligi kerak (yuklangan: %(size).1f MB)."),
                params={"max": self.max_mb, "size": value.size / (1024 * 1024)},
            )

    def __eq__(self, other):
        return isinstance(other, MaxFileSizeValidator) and self.max_mb == other.max_mb


# Loyiha hujjatlari uchun ruxsat etilgan kengaytmalar. Ro'yxat ataylab oq
# ro'yxat: .html, .htm, .svg, .xhtml, .js kabi fayllar brauzerda saytning o'z
# domenida ijro etilishi mumkin, ya'ni yuklangan fayl saqlanuvchi XSS'ga
# aylanadi. Ular bu yerda yo'q.
DOCUMENT_EXTENSIONS = (
    "pdf", "doc", "docx", "xls", "xlsx", "xlsm", "ppt", "pptx",
    "txt", "csv", "rtf", "odt", "ods",
    "dwg", "dxf", "dwf", "rvt", "ifc", "skp",
    "png", "jpg", "jpeg", "gif", "webp", "bmp", "tif", "tiff",
    "zip", "rar", "7z",
)

IMAGE_EXTENSIONS = ("png", "jpg", "jpeg", "gif", "webp")

# Loyiha muqova rasmi: brauzerlar hammasini yaxshi ko'rsatadigan va
# ImageField (Pillow) o'qiy oladigan formatlar.
PROJECT_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp")


@deconstructible
class AllowedExtensionsValidator:
    """Faqat ro'yxatdagi kengaytmali fayllarni o'tkazadi."""

    def __init__(self, allowed=DOCUMENT_EXTENSIONS):
        self.allowed = tuple(sorted({ext.lower().lstrip(".") for ext in allowed}))

    def __call__(self, value):
        name = getattr(value, "name", "") or ""
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in self.allowed:
            raise ValidationError(
                _("«.%(ext)s» turidagi fayllarni yuklab bo'lmaydi. Ruxsat etilgan turlar: %(allowed)s."),
                params={"ext": ext or "?", "allowed": ", ".join(self.allowed)},
                code="invalid_extension",
            )

    def __eq__(self, other):
        return isinstance(other, AllowedExtensionsValidator) and self.allowed == other.allowed
