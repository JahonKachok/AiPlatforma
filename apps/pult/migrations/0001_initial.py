import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("projects", "0014_project_image"),
        ("tasks", "0007_alter_taskattachment_file"),
    ]

    operations = [
        migrations.CreateModel(
            name="CalendarDay",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(unique=True)),
                ("is_workday", models.BooleanField(default=False, verbose_name="Working day")),
                ("note", models.CharField(blank=True, default="", max_length=255)),
            ],
            options={"verbose_name": "Calendar day", "verbose_name_plural": "Calendar", "ordering": ["date"]},
        ),
        migrations.CreateModel(
            name="TaskTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("days", models.PositiveIntegerField(blank=True, null=True)),
                ("hours", models.FloatField(blank=True, null=True)),
                ("dept", models.CharField(blank=True, default="", max_length=50)),
            ],
            options={"verbose_name": "Task template", "verbose_name_plural": "Task templates", "ordering": ["dept", "name"]},
        ),
        migrations.CreateModel(
            name="PultSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("points_early", models.FloatField(default=3)),
                ("points_ontime", models.FloatField(default=2)),
                ("points_late_small", models.FloatField(default=0)),
                ("late_days", models.PositiveIntegerField(default=2, help_text="Up to this many days late counts as 'small' delay.")),
                ("points_late_big", models.FloatField(default=-2)),
                ("points_clean", models.FloatField(default=2, help_text="Bonus when accepted without reworks.")),
                ("points_per_rework", models.FloatField(default=2)),
                ("quality_min", models.FloatField(default=-4)),
                ("points_per_missed", models.FloatField(default=1)),
                ("missed_max", models.FloatField(default=3)),
                ("level_a", models.FloatField(default=5)),
                ("bonus_a", models.FloatField(default=0.2)),
                ("level_b", models.FloatField(default=3)),
                ("bonus_b", models.FloatField(default=0.1)),
                ("level_c", models.FloatField(default=1)),
                ("bonus_c", models.FloatField(default=0.05)),
                ("bonus_d", models.FloatField(default=0)),
                ("min_tasks", models.PositiveIntegerField(default=3)),
                ("work_week_days", models.PositiveSmallIntegerField(choices=[(5, "5"), (6, "6")], default=5)),
                ("internal_project", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+",
                    to="projects.project",
                    help_text="Project used for non-standard tasks that belong to no client project.",
                )),
            ],
            options={"verbose_name": "Pult settings", "verbose_name_plural": "Pult settings"},
        ),
        migrations.CreateModel(
            name="TaskWorkflow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.PositiveIntegerField(unique=True, verbose_name="Number")),
                ("status", models.CharField(choices=[
                    ("Черновик", "Черновик"), ("Новая", "Новая"), ("На согласовании", "На согласовании"),
                    ("В работе", "В работе"), ("Есть вопрос", "Есть вопрос"), ("Согласование", "Согласование"),
                    ("На проверке", "На проверке"), ("На доработке", "На доработке"), ("Принята", "Принята"),
                    ("Отменена", "Отменена"),
                ], default="Новая", max_length=20)),
                ("type", models.CharField(blank=True, default="", max_length=255, verbose_name="Type")),
                ("days", models.PositiveIntegerField(blank=True, null=True, verbose_name="Term, days")),
                ("start_date", models.DateField(blank=True, null=True, verbose_name="Start date")),
                ("hours", models.FloatField(blank=True, null=True, verbose_name="Estimated hours")),
                ("amount", models.FloatField(blank=True, null=True, verbose_name="Amount, UZS")),
                ("done", models.FloatField(default=0, verbose_name="Done (0–1)")),
                ("source_ok", models.BooleanField(default=False, verbose_name="Source files handed over")),
                ("finished_at", models.DateField(blank=True, null=True, verbose_name="Actual finish")),
                ("reworks", models.PositiveIntegerField(default=0, verbose_name="Reworks")),
                ("missed_reports", models.PositiveIntegerField(default=0, verbose_name="Missed reports")),
                ("flow", models.CharField(choices=[("Проект", "Проект"), ("Нестандартная", "Нестандартная")], default="Нестандартная", max_length=20)),
                ("stage", models.CharField(blank=True, default="", max_length=50, verbose_name="Stage")),
                ("dept", models.CharField(blank=True, default="", max_length=50, verbose_name="Department")),
                ("tz", models.TextField(blank=True, default="", verbose_name="Terms of reference")),
                ("approval_since", models.DateField(blank=True, null=True)),
                ("approver_kind", models.CharField(blank=True, default="", max_length=20)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("task", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="workflow", to="tasks.task")),
            ],
            options={"verbose_name": "Task workflow", "verbose_name_plural": "Task workflows", "ordering": ["number"]},
        ),
        migrations.CreateModel(
            name="ProgressReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("done", models.FloatField(blank=True, null=True)),
                ("comment", models.TextField(blank=True, default="")),
                ("status", models.CharField(blank=True, default="", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("author", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pult_reports", to="tasks.task")),
            ],
            options={"ordering": ["date", "created_at"]},
        ),
    ]
