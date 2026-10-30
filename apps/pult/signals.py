from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.finance.models import FinancialRecord
from apps.tasks.models import Task


@receiver(post_save, sender=Task)
def create_task_workflow(sender, instance, created, **kwargs):
    """Platformaning istalgan joyida yaratilgan vazifa ham Pultda raqam bilan ko'rinadi."""
    if created and not kwargs.get("raw"):
        from .services import ensure_workflow
        ensure_workflow(instance)


@receiver(post_save, sender=FinancialRecord)
def create_operation_info(sender, instance, created, **kwargs):
    """Moliya sahifasida kiritilgan operatsiya ham Pultda № bilan ko'rinadi."""
    if created and not kwargs.get("raw"):
        from .finance import ensure_op_info
        ensure_op_info(instance)
