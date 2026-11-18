from django.conf import settings
from django.db import models


class IntegrationSetting(models.Model):
    """Admin paneldan kiritiladigan integratsiya sozlamasi (token, API kalit,
    model nomi). `.env` dagi qiymatdan ustun turadi; bo'sh bo'lsa `.env`
    ishlatiladi. Qiymat bazada shifrlangan holda saqlanadi — backup yoki baza
    dampi orqali kalitlar ochiq ko'rinib qolmasin (runtime_config.py)."""

    key = models.CharField(max_length=64, unique=True)
    value_encrypted = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key
