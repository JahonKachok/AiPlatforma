"""HTML ``<script>`` blokiga xavfsiz joylanadigan JSON."""
import json

from django.utils.safestring import mark_safe

# Django'ning o'z ``json_script`` filtri ishlatadigan qochirish jadvali.
# ``json.dumps`` ``<`` va ``>`` ni qochirmaydi, shuning uchun ma'lumot ichidagi
# ``</script>`` satri script blokidan chiqib ketib, saqlanuvchi XSS beradi
# (masalan, obyekt nomi yoki xodim ismi shunday yozilgan bo'lsa).
_SCRIPT_ESCAPES = {
    ord(">"): "\\u003E",
    ord("<"): "\\u003C",
    ord("&"): "\\u0026",
    # JS satrini uzib yuboradigan Unicode belgilar.
    0x2028: "\\u2028",
    0x2029: "\\u2029",
}


def script_json(data) -> str:
    """``data`` ni ``<script>`` ichida ``|safe`` bilan chiqarish uchun JSON."""
    return mark_safe(json.dumps(data).translate(_SCRIPT_ESCAPES))
