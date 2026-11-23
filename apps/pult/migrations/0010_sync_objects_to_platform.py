"""Состав'da avval qo'shilgan «Объект»larni loyiha sahifasidagi «Объекты»ga bir marta ko'chirish.

Bundan keyin har bir saqlashda plan.sync_objects_to_platform o'zi bajaradi.
"""
from django.db import migrations


def sync(apps, schema_editor):
    from apps.pult.plan import sync_objects_to_platform

    PlanRow = apps.get_model("pult", "PlanRow")
    project_ids = set(PlanRow.objects.filter(kind="Объект").values_list("project_id", flat=True))
    if project_ids:
        sync_objects_to_platform(project_ids)


class Migration(migrations.Migration):
    dependencies = [
        ("pult", "0009_seed_composition_template"),
        ("projects", "0015_project_confirmation"),
    ]
    operations = [migrations.RunPython(sync, migrations.RunPython.noop)]
