from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pult", "0004_seed_stages_number_records"),
    ]

    operations = [
        migrations.AddField(
            model_name="planrow",
            name="source_key",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
    ]
