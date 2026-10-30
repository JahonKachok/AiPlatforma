from django.db import migrations

# Platforma holati -> Pult holati (services.FROM_PLATFORM bilan bir xil;
# migratsiyada ilova kodini import qilmaymiz).
FROM_PLATFORM = {
    "new": "Новая", "in_progress": "В работе", "review": "На проверке",
    "revision": "На доработке", "approved": "Принята", "completed": "Принята",
}


def number_existing_tasks(apps, schema_editor):
    """Mavjud vazifalarga yaratilish tartibida №1, №2... beriladi."""
    Task = apps.get_model("tasks", "Task")
    TaskWorkflow = apps.get_model("pult", "TaskWorkflow")
    rows = []
    for number, task in enumerate(Task.objects.order_by("created_at", "id"), start=1):
        rows.append(TaskWorkflow(
            task_id=task.pk, number=number, status=FROM_PLATFORM.get(task.status, "Новая"),
            flow="Проект" if task.section_id else "Нестандартная",
        ))
    TaskWorkflow.objects.bulk_create(rows, batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("pult", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(number_existing_tasks, migrations.RunPython.noop),
    ]
