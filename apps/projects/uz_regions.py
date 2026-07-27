"""Uzbekistan's 14 administrative regions (viloyat).

Each has an approximate map-centering coordinate (the regional capital) —
this is not surveyed precision, just a starting viewport for the location
picker map.
"""
from django.utils.translation import gettext_lazy as _

REGION_CHOICES = [
    ("tashkent_city", _("Tashkent city")),
    ("tashkent", _("Tashkent region")),
    ("andijon", _("Andijan region")),
    ("fargona", _("Fergana region")),
    ("namangan", _("Namangan region")),
    ("sirdaryo", _("Sirdaryo region")),
    ("jizzax", _("Jizzakh region")),
    ("samarqand", _("Samarkand region")),
    ("buxoro", _("Bukhara region")),
    ("navoiy", _("Navoi region")),
    ("qashqadaryo", _("Kashkadarya region")),
    ("surxondaryo", _("Surkhandarya region")),
    ("xorazm", _("Khorezm region")),
    ("qoraqalpogiston", _("Republic of Karakalpakstan")),
]

REGION_CENTERS = {
    "tashkent_city": (41.2995, 69.2401),
    "tashkent": (41.0000, 69.5842),
    "andijon": (40.7821, 72.3442),
    "fargona": (40.3894, 71.7978),
    "namangan": (41.0058, 71.6437),
    "sirdaryo": (40.4897, 68.7844),
    "jizzax": (40.1158, 67.8422),
    "samarqand": (39.6542, 66.9597),
    "buxoro": (39.7747, 64.4286),
    "navoiy": (40.0844, 65.3792),
    "qashqadaryo": (38.8606, 65.7891),
    "surxondaryo": (37.2242, 67.2783),
    "xorazm": (41.5500, 60.6333),
    "qoraqalpogiston": (42.4531, 59.6103),
}
