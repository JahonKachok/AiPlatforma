import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_alter_section_options_remove_section_code_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='section',
            name='discipline',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sections', to='accounts.discipline'),
        ),
    ]
