import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0007_alter_user_avatar"),
        ("finance", "0008_financialrecord_exchange_rate"),
        ("projects", "0014_project_image"),
        ("pult", "0002_number_existing_tasks"),
    ]

    operations = [
        migrations.AddField(
            model_name="taskworkflow",
            name="section",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="Plan section ID"),
        ),
        migrations.AddField(
            model_name="pultsettings",
            name="plan_version",
            field=models.PositiveIntegerField(default=0, editable=False),
        ),
        migrations.CreateModel(
            name="PlanRow",
            fields=[
                ("id", models.PositiveIntegerField(primary_key=True, serialize=False)),
                ("wbs", models.CharField(blank=True, default="", max_length=50)),
                ("code", models.CharField(blank=True, default="", max_length=50)),
                ("name", models.CharField(blank=True, default="", max_length=500)),
                ("kind", models.CharField(blank=True, default="", max_length=20)),
                ("owner", models.CharField(blank=True, default="", max_length=255)),
                ("dur", models.FloatField(blank=True, null=True)),
                ("preds", models.CharField(blank=True, default="", max_length=500)),
                ("snet", models.DateField(blank=True, null=True)),
                ("actual_start", models.DateField(blank=True, null=True)),
                ("actual_finish", models.DateField(blank=True, null=True)),
                ("pct", models.FloatField(blank=True, null=True)),
                ("calc_start", models.DateField(blank=True, null=True)),
                ("calc_finish", models.DateField(blank=True, null=True)),
                ("base_start", models.DateField(blank=True, null=True)),
                ("base_finish", models.DateField(blank=True, null=True)),
                ("client", models.CharField(blank=True, default="", max_length=10)),
                ("comment", models.TextField(blank=True, default="")),
                ("in_plan", models.CharField(blank=True, default="", max_length=10)),
                ("doc", models.CharField(blank=True, default="", max_length=255)),
                ("pay", models.CharField(blank=True, default="", max_length=20)),
                ("price", models.FloatField(blank=True, null=True)),
                ("cur", models.CharField(blank=True, default="", max_length=10)),
                ("contract", models.CharField(blank=True, default="", max_length=50)),
                ("task", models.PositiveIntegerField(blank=True, null=True)),
                ("closed", models.DateField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pult_plan_rows", to="projects.project")),
            ],
            options={"verbose_name": "Plan row", "verbose_name_plural": "Project composition", "ordering": ["project", "wbs", "id"]},
        ),
        migrations.CreateModel(
            name="DisciplineConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("duration", models.PositiveIntegerField(default=10, verbose_name="Default duration, work days")),
                ("links", models.CharField(blank=True, default="", help_text="Typical links by codes, e.g. «AR SS+10; TX».", max_length=255)),
                ("order", models.PositiveIntegerField(default=100)),
                ("latin_code", models.CharField(blank=True, default="", help_text="Discipline code used in document ciphers (AR, EL…).", max_length=10)),
                ("doc_type", models.CharField(blank=True, default="DWG", max_length=10)),
                ("needs_estimate", models.BooleanField(default=True, verbose_name="Needs estimate stage")),
                ("discipline", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="pult_config", to="accounts.discipline")),
            ],
            options={"ordering": ["order"]},
        ),
        migrations.CreateModel(
            name="CipherRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("prefix", models.CharField(max_length=20)),
                ("stage", models.CharField(max_length=10)),
                ("code", models.CharField(max_length=20)),
                ("digits", models.PositiveSmallIntegerField(default=5)),
                ("common", models.CharField(default="ZZ01", max_length=10)),
                ("project", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="pult_cipher", to="projects.project")),
            ],
        ),
        migrations.CreateModel(
            name="StageConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, unique=True)),
                ("weight", models.FloatField(default=0, verbose_name="Weight, %")),
                ("days", models.PositiveIntegerField(blank=True, null=True)),
                ("role", models.CharField(blank=True, default="", max_length=50)),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["order"]},
        ),
        migrations.CreateModel(
            name="PersonSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pay_type", models.CharField(choices=[("Оклад", "Оклад"), ("Договор", "Договор")], default="Оклад", max_length=20)),
                ("norm_hours", models.PositiveSmallIntegerField(default=40)),
                ("stage_role", models.CharField(blank=True, choices=[("", "—"), ("Сметчик", "Сметчик"), ("Оформитель", "Оформитель"), ("Печать", "Печать")], default="", max_length=20)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="pult_settings", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Employee settings", "verbose_name_plural": "Employee settings"},
        ),
        migrations.CreateModel(
            name="Contract",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20, unique=True, verbose_name="ID")),
                ("side", models.CharField(choices=[("Исполнитель", "Исполнитель"), ("Заказчик", "Заказчик"), ("Налог", "Налог")], default="Исполнитель", max_length=20)),
                ("name", models.CharField(max_length=255)),
                ("section", models.CharField(blank=True, default="", max_length=50)),
                ("currency", models.CharField(choices=[("USD", "USD"), ("UZS", "UZS")], default="USD", max_length=3)),
                ("amount", models.FloatField(default=0)),
                ("status", models.CharField(choices=[("Открыт", "Открыт"), ("Закрыт", "Закрыт")], default="Открыт", max_length=10)),
                ("note", models.TextField(blank=True, default="")),
                ("source", models.CharField(blank=True, default="", max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("employee_contract", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pult_contract", to="finance.employeecontract")),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pult_contracts", to="projects.project")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pult_contracts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Contract", "verbose_name_plural": "Contracts", "ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="OperationInfo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.PositiveIntegerField(unique=True)),
                ("counterparty", models.CharField(blank=True, default="", max_length=255)),
                ("category", models.CharField(blank=True, default="", max_length=100)),
                ("method", models.CharField(blank=True, default="", max_length=30)),
                ("offset", models.FloatField(blank=True, null=True, verbose_name="Offset in contract currency")),
                ("contract", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="operations", to="pult.contract")),
                ("record", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="pult_info", to="finance.financialrecord")),
            ],
            options={"ordering": ["number"]},
        ),
    ]
