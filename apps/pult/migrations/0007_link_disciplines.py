"""«Пользователи → Дисциплины» va «Состав проекта»ni bitta ma'lumotnomaga bog'lash.

1. Sozlamasi yo'q fanlarga (Пользователи sahifasida qo'shilganlar) Pult sozlamasi
   — tartib va lotin shifr kodi — yoziladi.
2. Состав bo'limlarining kodlari ma'lumotnomadagi ko'rinishga keltiriladi:
   kirillcha «АР» lotincha «AR» fani bor bo'lsa «AR» bo'ladi (bir fan ikki
   ustunga bo'linib, bir joyda ko'rinib boshqasida «Нет данных» chiqmasin).
3. Shundan keyin ham ma'lumotnomada yo'q kodlar (ИД, ТХ, ГП…) fan sifatida qo'shiladi.
"""
from django.db import migrations
from django.db.models import Max


def link(apps, schema_editor):
    from apps.pult.plan import _section_name, latin_code

    Discipline = apps.get_model("accounts", "Discipline")
    DisciplineConfig = apps.get_model("pult", "DisciplineConfig")
    PlanRow = apps.get_model("pult", "PlanRow")

    order = DisciplineConfig.objects.aggregate(m=Max("order"))["m"] or 0
    for d in Discipline.objects.filter(pult_config__isnull=True).order_by("code"):
        order += 1
        DisciplineConfig.objects.create(discipline=d, order=order, latin_code=latin_code(d.code))

    def build_index():
        index = {}
        configs = dict(DisciplineConfig.objects.values_list("discipline_id", "latin_code"))
        disciplines = list(Discipline.objects.order_by("code"))
        for d in disciplines:
            index.setdefault(("=", d.code.upper()), d.code)
        for d in disciplines:
            for key in (latin_code(d.code), latin_code(configs.get(d.pk, ""))):
                if key:
                    index.setdefault(key, d.code)
        return index

    index = build_index()
    for row in PlanRow.objects.filter(kind__in=("Раздел", "")).exclude(code="").order_by("project_id", "wbs", "id"):
        code = row.code.strip().upper()
        canonical = index.get(("=", code)) or index.get(latin_code(code))
        if canonical is None:
            if len(code) > 20 or row.kind != "Раздел":
                continue
            d = Discipline.objects.create(code=code, name=_section_name(code, row.name))
            order += 1
            DisciplineConfig.objects.create(discipline=d, order=order, latin_code=latin_code(code))
            index = build_index()
            canonical = code
        if canonical != row.code:
            PlanRow.objects.filter(pk=row.pk).update(code=canonical)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_alter_user_avatar"),
        ("pult", "0006_cipher_six_parts"),
    ]

    operations = [migrations.RunPython(link, migrations.RunPython.noop)]
