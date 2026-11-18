from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from apps.accounts.models import Discipline
from apps.finance.models import FinancialRecord
from apps.tasks.models import Task


@receiver(post_save, sender=Task)
def create_task_workflow(sender, instance, created, **kwargs):
    """Platformaning istalgan joyida yaratilgan vazifa ham Pultda raqam bilan ko'rinadi."""
    if created and not kwargs.get("raw"):
        from .services import ensure_workflow
        ensure_workflow(instance)


@receiver(pre_delete, sender=Task)
def unlink_plan_rows(sender, instance, **kwargs):
    """O'chirilgan vazifa Состав'da «Задача №» bo'lib qolib ketmasin — keyingi
    «Задачи и договоры» bo'limga yangi qoralama qo'ya oladi."""
    from .models import PlanRow, TaskWorkflow

    number = TaskWorkflow.objects.filter(task=instance).values_list("number", flat=True).first()
    if number:
        PlanRow.objects.filter(task=number).update(task=None)


@receiver(post_save, sender=Discipline)
def create_discipline_config(sender, instance, created, **kwargs):
    """«Пользователи → Дисциплины»da qo'shilgan fan Состав проекта ustunlarida ham chiqadi."""
    if created and not kwargs.get("raw"):
        from .plan import ensure_discipline_config
        ensure_discipline_config(instance)


@receiver(post_save, sender=FinancialRecord)
def create_operation_info(sender, instance, created, **kwargs):
    """Moliya sahifasida kiritilgan operatsiya ham Pultda № bilan ko'rinadi."""
    if created and not kwargs.get("raw"):
        from .finance import ensure_op_info
        ensure_op_info(instance)
