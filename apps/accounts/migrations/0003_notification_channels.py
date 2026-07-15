# Bildirishnoma sozlamalari: 9 ta boolean maydon -> bitta `channels` JSON
# matritsasi (hodisa turi x sayt/email/telegram kanal). Eski qiymatlar
# ko'chirilib saqlanadi.
from django.db import migrations, models

TYPES = ["task", "deadline", "approval", "comment", "finance", "document", "system"]


def forwards(apps, schema_editor):
    NotificationPreference = apps.get_model("accounts", "NotificationPreference")
    for prefs in NotificationPreference.objects.all():
        prefs.channels = {
            ntype: {
                "site": getattr(prefs, f"notify_{ntype}", True),
                "email": getattr(prefs, f"notify_{ntype}", True) and prefs.email_enabled,
                "telegram": getattr(prefs, f"notify_{ntype}", True) and prefs.telegram_enabled,
            }
            for ntype in TYPES
        }
        prefs.save(update_fields=["channels"])


def backwards(apps, schema_editor):
    pass  # eski maydonlar qayta yaratilganda default True bilan qoladi


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_alter_user_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificationpreference",
            name="channels",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(model_name="notificationpreference", name="notify_task"),
        migrations.RemoveField(model_name="notificationpreference", name="notify_deadline"),
        migrations.RemoveField(model_name="notificationpreference", name="notify_approval"),
        migrations.RemoveField(model_name="notificationpreference", name="notify_comment"),
        migrations.RemoveField(model_name="notificationpreference", name="notify_finance"),
        migrations.RemoveField(model_name="notificationpreference", name="notify_document"),
        migrations.RemoveField(model_name="notificationpreference", name="notify_system"),
        migrations.RemoveField(model_name="notificationpreference", name="email_enabled"),
        migrations.RemoveField(model_name="notificationpreference", name="telegram_enabled"),
    ]
