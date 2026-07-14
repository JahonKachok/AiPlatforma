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
