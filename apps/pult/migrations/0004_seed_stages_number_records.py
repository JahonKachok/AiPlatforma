from django.db import migrations

# Pultdagi «Этапы» varag'ining boshlang'ich qiymatlari (pult.js dagi STAGE_DEF bilan bir xil).
STAGES = [
    ("Проектирование", 70, None, "Специалист", 1),
    ("Смета", 10, 5, "Сметчик", 2),
    ("Оформление", 15, 3, "Оформитель", 3),
    ("Печать", 5, 1, "Печать", 4),
]


def seed(apps, schema_editor):
    StageConfig = apps.get_model("pult", "StageConfig")
    for name, weight, days, role, order in STAGES:
        StageConfig.objects.get_or_create(name=name, defaults={"weight": weight, "days": days, "role": role, "order": order})

    # Mavjud moliyaviy yozuvlarga sana tartibida № beriladi.
    FinancialRecord = apps.get_model("finance", "FinancialRecord")
    OperationInfo = apps.get_model("pult", "OperationInfo")
    OperationInfo.objects.bulk_create([
        OperationInfo(record_id=r.pk, number=n)
        for n, r in enumerate(FinancialRecord.objects.order_by("date", "created_at", "id"), start=1)
    ], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("pult", "0003_plan_finance"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
