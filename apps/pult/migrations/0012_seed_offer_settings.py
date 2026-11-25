"""«Справочник ТКП»ning «Настройка» qatorlari (Pult HTML'idagi standart qiymatlar).
Pozitsiya va narxlar kompaniyaning Excel faylidan ko'chiriladi yoki adminda kiritiladi."""
from django.db import migrations

SETTINGS = [
    ("Ставка НДС, %", "12"),
    ("Приветствие", "ООО «GASTEC PROJECT» приветствует Вас и предлагает следующее коммерческое предложение"),
    ("Подпись: должность", "Директор"),
    ("Подпись: организация", "ООО «GASTEC PROJECT»"),
    ("Подпись: ФИО", "А.А. Саидходжаев"),
]


def seed(apps, schema_editor):
    Item = apps.get_model("pult", "OfferLibraryItem")
    for order, (text, value) in enumerate(SETTINGS, start=1):
        Item.objects.get_or_create(section="Настройка", text=text, defaults={"value": value, "order": order})


class Migration(migrations.Migration):
    dependencies = [("pult", "0011_commercial_requests")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
