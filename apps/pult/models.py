"""GASTEC Pult: platformadagi vazifalar ustidagi ish oqimi.

Platformaning ``tasks.Task`` modeli o'zgarmaydi — Pultga kerak bo'lgan qo'shimcha
maydonlar (muddat kunlarda, bajarilish foizi, ГИП tasdiqlashlari, qayta ishlashlar soni,
kunlik hisobotlar) alohida ``TaskWorkflow`` jadvalida saqlanadi. Holat Pultning
10 ta holatidan biri; ``Task.status`` har safar unga mos qiymatga sinxronlanadi
(qarang: ``services.PLATFORM_STATUS``), shuning uchun eski kanban ham to'g'ri
ko'rsatadi.
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class WorkflowStatus(models.TextChoices):
    # Qiymatlar Pult interfeysi ishlatadigan matnlar bilan bir xil.
    DRAFT = "Черновик", "Черновик"
    NEW = "Новая", "Новая"
    DAYS_PROPOSED = "На согласовании", "На согласовании"
    IN_PROGRESS = "В работе", "В работе"
    QUESTION = "Есть вопрос", "Есть вопрос"
    APPROVAL = "Согласование", "Согласование"
    REVIEW = "На проверке", "На проверке"
    REVISION = "На доработке", "На доработке"
    ACCEPTED = "Принята", "Принята"
    CANCELLED = "Отменена", "Отменена"


class Flow(models.TextChoices):
    PROJECT = "Проект", "Проект"
    OTHER = "Нестандартная", "Нестандартная"


class TaskWorkflow(models.Model):
    task = models.OneToOneField("tasks.Task", on_delete=models.CASCADE, related_name="workflow")
    # Pultda vazifa "№" bo'yicha tanilgan; UUID foydalanuvchiga ko'rsatilmaydi.
    number = models.PositiveIntegerField(unique=True, verbose_name=_("Number"))
    status = models.CharField(max_length=20, choices=WorkflowStatus.choices, default=WorkflowStatus.NEW)
    type = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Type"))
    days = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Term, days"))
    start_date = models.DateField(null=True, blank=True, verbose_name=_("Start date"))
    hours = models.FloatField(null=True, blank=True, verbose_name=_("Estimated hours"))
    amount = models.FloatField(null=True, blank=True, verbose_name=_("Amount, UZS"))
    done = models.FloatField(default=0, verbose_name=_("Done (0–1)"))
    source_ok = models.BooleanField(default=False, verbose_name=_("Source files handed over"))
    # Dispetcher: 50% da so'raladigan oraliq fayl (isxodnik) topshirildimi.
    mid_file_ok = models.BooleanField(default=False, verbose_name=_("Intermediate file handed over"))
    finished_at = models.DateField(null=True, blank=True, verbose_name=_("Actual finish"))
    reworks = models.PositiveIntegerField(default=0, verbose_name=_("Reworks"))
    missed_reports = models.PositiveIntegerField(default=0, verbose_name=_("Missed reports"))
    flow = models.CharField(max_length=20, choices=Flow.choices, default=Flow.OTHER)
    stage = models.CharField(max_length=50, blank=True, default="", verbose_name=_("Stage"))
    dept = models.CharField(max_length=50, blank=True, default="", verbose_name=_("Department"))
    tz = models.TextField(blank=True, default="", verbose_name=_("Terms of reference"))
    approval_since = models.DateField(null=True, blank=True)
    approver_kind = models.CharField(max_length=20, blank=True, default="")
    # PlanRow.id (Pultdagi «Раздел (ID)»). FK emas: bo'lim o'chirilganda ham
    # bog'lanish qoladi, «Задачи и договоры» shunday vazifani bekor qiladi.
    section = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Plan section ID"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["number"]
        verbose_name = _("Task workflow")
        verbose_name_plural = _("Task workflows")

    def __str__(self):
        return f"№{self.number} {self.task}"


class ProgressReport(models.Model):
    """Kunlik hisobot (foiz) yoki holat o'zgarishi yozuvi — Pultdagi «Прогресс» varag'i."""

    task = models.ForeignKey("tasks.Task", on_delete=models.CASCADE, related_name="pult_reports")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    done = models.FloatField(null=True, blank=True)
    comment = models.TextField(blank=True, default="")
    # Bo'sh emas bo'lsa — bu holat o'zgarishi yozuvi (hisobot emas).
    status = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "created_at"]

    def __str__(self):
        return f"{self.date} {self.task_id} {self.status or self.done}"


class CalendarDay(models.Model):
    """Ish kalendari istisnolari: bayramlar va ko'chirilgan ish kunlari."""

    date = models.DateField(unique=True)
    is_workday = models.BooleanField(default=False, verbose_name=_("Working day"))
    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["date"]
        verbose_name = _("Calendar day")
        verbose_name_plural = _("Calendar")

    def __str__(self):
        return f"{self.date} {'ish kuni' if self.is_workday else 'dam olish'}"


class TaskTemplate(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    days = models.PositiveIntegerField(null=True, blank=True)
    hours = models.FloatField(null=True, blank=True)
    dept = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        ordering = ["dept", "name"]
        verbose_name = _("Task template")
        verbose_name_plural = _("Task templates")

    def __str__(self):
        return self.name


class PultSettings(models.Model):
    """Yagona yozuv (pk=1): KPI ballari, ish haftasi, ichki ishlar loyihasi."""

    points_early = models.FloatField(default=3)
    points_ontime = models.FloatField(default=2)
    points_late_small = models.FloatField(default=0)
    late_days = models.PositiveIntegerField(default=2, help_text=_("Up to this many days late counts as 'small' delay."))
    points_late_big = models.FloatField(default=-2)
    points_clean = models.FloatField(default=2, help_text=_("Bonus when accepted without reworks."))
    points_per_rework = models.FloatField(default=2)
    quality_min = models.FloatField(default=-4)
    points_per_missed = models.FloatField(default=1)
    missed_max = models.FloatField(default=3)
    level_a = models.FloatField(default=5)
    bonus_a = models.FloatField(default=0.2)
    level_b = models.FloatField(default=3)
    bonus_b = models.FloatField(default=0.1)
    level_c = models.FloatField(default=1)
    bonus_c = models.FloatField(default=0.05)
    bonus_d = models.FloatField(default=0)
    min_tasks = models.PositiveIntegerField(default=3)
    work_week_days = models.PositiveSmallIntegerField(default=5, choices=[(5, "5"), (6, "6")])
    # Состав проекта har saqlanganda oshadi: ikki kishi bir vaqtda o'zgartirsa,
    # keyingisi eski ma'lumot ustiga yozib yubormasligi uchun.
    plan_version = models.PositiveIntegerField(default=0, editable=False)
    internal_project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text=_("Project used for non-standard tasks that belong to no client project."),
    )
    # Adminlardan tashqari kim ТКП'ga direktor imzosi va muhrini qo'ya oladi.
    signers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="+", verbose_name=_("May sign and seal"),
        help_text=_("Besides admins: who may put the director's signature and seal on a PDF."),
    )

    class Meta:
        verbose_name = _("Pult settings")
        verbose_name_plural = _("Pult settings")

    def __str__(self):
        return "Pult settings"

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


# ---------------------------------------------------------------- stage 2: состав и график проекта

class PlanRow(models.Model):
    """«Состав проекта» qatori: obyekt, bosqich, bo'lim yoki veha.

    ``id`` brauzer tomonidan beriladi (yangi qatorlar bir saqlashda bir-biriga
    «Связи» orqali murojaat qiladi), shuning uchun avtomatik emas."""

    id = models.PositiveIntegerField(primary_key=True)
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="pult_plan_rows")
    wbs = models.CharField(max_length=50, blank=True, default="")
    code = models.CharField(max_length=50, blank=True, default="")
    name = models.CharField(max_length=500, blank=True, default="")
    kind = models.CharField(max_length=20, blank=True, default="")
    owner = models.CharField(max_length=255, blank=True, default="")
    dur = models.FloatField(null=True, blank=True)
    preds = models.CharField(max_length=500, blank=True, default="")
    snet = models.DateField(null=True, blank=True)
    actual_start = models.DateField(null=True, blank=True)
    actual_finish = models.DateField(null=True, blank=True)
    pct = models.FloatField(null=True, blank=True)
    calc_start = models.DateField(null=True, blank=True)
    calc_finish = models.DateField(null=True, blank=True)
    base_start = models.DateField(null=True, blank=True)
    base_finish = models.DateField(null=True, blank=True)
    client = models.CharField(max_length=10, blank=True, default="")
    comment = models.TextField(blank=True, default="")
    in_plan = models.CharField(max_length=10, blank=True, default="")
    doc = models.CharField(max_length=255, blank=True, default="")
    pay = models.CharField(max_length=20, blank=True, default="")
    price = models.FloatField(null=True, blank=True)
    cur = models.CharField(max_length=10, blank=True, default="")
    contract = models.CharField(max_length=50, blank=True, default="")
    task = models.PositiveIntegerField(null=True, blank=True)
    closed = models.DateField(null=True, blank=True)
    # Platformadan ko'chirilgan qator: «so:<SubObject id>» yoki «sod:<SubObjectDiscipline id>».
    # Qayta ko'chirishda shu bo'yicha takror qo'shilmaydi.
    source_key = models.CharField(max_length=64, blank=True, default="", db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project", "wbs", "id"]
        verbose_name = _("Plan row")
        verbose_name_plural = _("Project composition")

    def __str__(self):
        return f"{self.project} · {self.wbs} {self.code} {self.name}"


class DisciplineConfig(models.Model):
    """Platforma fanlari (accounts.Discipline) uchun Pult sozlamalari."""

    discipline = models.OneToOneField("accounts.Discipline", on_delete=models.CASCADE, related_name="pult_config")
    duration = models.PositiveIntegerField(default=10, verbose_name=_("Default duration, work days"))
    links = models.CharField(max_length=255, blank=True, default="", help_text=_("Typical links by codes, e.g. «AR SS+10; TX»."))
    order = models.PositiveIntegerField(default=100)
    latin_code = models.CharField(max_length=10, blank=True, default="", help_text=_("Discipline code used in document ciphers (AR, EL…)."))
    doc_type = models.CharField(max_length=10, blank=True, default="DWG")
    needs_estimate = models.BooleanField(default=True, verbose_name=_("Needs estimate stage"))

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.discipline.code} config"


class CipherRule(models.Model):
    """Shifr: ИСПОЛНИТЕЛЬ_ЗАКАЗЧИК_ДОГОВОР_ОБЪЕКТ_ДИСЦИПЛИНА_№, masalan
    GTP_MIM_D125_OF_AR_001. Obyekt kodi obyektning o'zidan, distsiplina —
    loyiha tarkibidan (DisciplineConfig.latin_code) olinadi."""

    project = models.OneToOneField("projects.Project", on_delete=models.CASCADE, related_name="pult_cipher")
    prefix = models.CharField(max_length=20, verbose_name=_("Contractor prefix"))
    client = models.CharField(max_length=20, blank=True, default="", verbose_name=_("Customer code"))
    code = models.CharField(max_length=20, verbose_name=_("Contract number / project code"))
    # Eski formatdan (FGCBAS_...) qolgan; yangi shifrga kirmaydi.
    stage = models.CharField(max_length=10, blank=True, default="")
    digits = models.PositiveSmallIntegerField(default=3)
    common = models.CharField(max_length=10, default="ZZ01")

    def __str__(self):
        return "_".join(x for x in (self.prefix, self.client, self.code) if x)


class StageConfig(models.Model):
    """Bo'lim bosqichlari: Проектирование → Смета → Оформление → Печать."""

    name = models.CharField(max_length=50, unique=True)
    weight = models.FloatField(default=0, verbose_name=_("Weight, %"))
    days = models.PositiveIntegerField(null=True, blank=True)
    role = models.CharField(max_length=50, blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class PersonSettings(models.Model):
    """Xodimning Pultdagi ish sharoiti: to'lov turi, haftalik norma, bosqich roli."""

    PAY_CHOICES = [("Оклад", "Оклад"), ("Договор", "Договор")]
    STAGE_ROLES = [("", "—"), ("Сметчик", "Сметчик"), ("Оформитель", "Оформитель"), ("Печать", "Печать")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pult_settings")
    pay_type = models.CharField(max_length=20, choices=PAY_CHOICES, default="Оклад")
    norm_hours = models.PositiveSmallIntegerField(default=40)
    stage_role = models.CharField(max_length=20, choices=STAGE_ROLES, blank=True, default="")

    class Meta:
        verbose_name = _("Employee settings")
        verbose_name_plural = _("Employee settings")

    def __str__(self):
        return f"{self.user} · {self.pay_type}"


# ---------------------------------------------------------------- stage 3: финансы и договоры

class Contract(models.Model):
    SIDE_CHOICES = [("Исполнитель", "Исполнитель"), ("Заказчик", "Заказчик"), ("Налог", "Налог")]
    STATUS_CHOICES = [("Открыт", "Открыт"), ("Закрыт", "Закрыт")]

    code = models.CharField(max_length=20, unique=True, verbose_name="ID")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="pult_contracts")
    side = models.CharField(max_length=20, choices=SIDE_CHOICES, default="Исполнитель")
    name = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="pult_contracts")
    section = models.CharField(max_length=50, blank=True, default="")
    currency = models.CharField(max_length=3, choices=[("USD", "USD"), ("UZS", "UZS")], default="USD")
    amount = models.FloatField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Открыт")
    note = models.TextField(blank=True, default="")
    source = models.CharField(max_length=100, blank=True, default="")
    # Ijrochi platforma xodimi bo'lsa — platformadagi xodim shartnomasi bilan sinxron.
    employee_contract = models.OneToOneField(
        "finance.EmployeeContract", on_delete=models.SET_NULL, null=True, blank=True, related_name="pult_contract",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]
        verbose_name = _("Contract")
        verbose_name_plural = _("Contracts")

    def __str__(self):
        return f"{self.code} {self.name}"


class OperationInfo(models.Model):
    """FinancialRecord'ga Pult maydonlari: № , kontragent, Pult kategoriyasi, shartnoma bo'yicha zachyot."""

    record = models.OneToOneField("finance.FinancialRecord", on_delete=models.CASCADE, related_name="pult_info")
    number = models.PositiveIntegerField(unique=True)
    counterparty = models.CharField(max_length=255, blank=True, default="")
    category = models.CharField(max_length=100, blank=True, default="")
    method = models.CharField(max_length=30, blank=True, default="")
    contract = models.ForeignKey(Contract, on_delete=models.SET_NULL, null=True, blank=True, related_name="operations")
    offset = models.FloatField(null=True, blank=True, verbose_name=_("Offset in contract currency"))

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"№{self.number}"

class CompositionTemplate(models.Model):
    """«Типовой состав»: yangi loyiha tarkibini bir bosishda yaratish uchun shablon.

    ``items`` — qatorlar ro'yxati: ``{"wbs", "code", "name", "kind", "dur", "preds"}``.
    ``preds`` shu shablon ichidagi WBS raqamlariga ishora qiladi: ``"2.1НН+5; 3.1"``.
    """

    name = models.CharField(max_length=200, unique=True, verbose_name=_("Name"))
    order = models.PositiveIntegerField(default=0)
    items = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = _("Composition template")
        verbose_name_plural = _("Composition templates")

    def __str__(self):
        return self.name


# ---------------------------------------------------------------- «Запросы»: so'rovlar, ТКП, imzo va muhr

class CommercialRequest(models.Model):
    """«Запросы» reyestri: buyurtmachidan kelgan so'rov (tijorat taklifigacha va undan keyin)."""

    class Status(models.TextChoices):
        NEW = "Новый", "Новый"
        PREPARING = "Готовим ТКП", "Готовим ТКП"
        SENT = "ТКП отправлено", "ТКП отправлено"
        TALKS = "Переговоры", "Переговоры"
        WAITING = "Ожидание", "Ожидание"
        WON = "Выигран", "Выигран"
        LOST = "Проигран", "Проигран"
        DECLINED = "Отказались", "Отказались"

    number = models.CharField(max_length=20, unique=True, verbose_name="№")  # R001
    received = models.DateField(null=True, blank=True)
    short = models.CharField(max_length=255, blank=True, default="")
    client = models.CharField(max_length=255, blank=True, default="")
    title = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    owner = models.CharField(max_length=255, blank=True, default="")
    due = models.DateField(null=True, blank=True)
    kind = models.CharField(max_length=255, blank=True, default="")
    basis = models.CharField(max_length=500, blank=True, default="")
    place = models.CharField(max_length=255, blank=True, default="")
    folder = models.CharField(max_length=1000, blank=True, default="")
    tz = models.CharField(max_length=1000, blank=True, default="")
    offer_no = models.CharField(max_length=50, blank=True, default="")
    offer_date = models.DateField(null=True, blank=True)
    amount = models.FloatField(null=True, blank=True)
    currency = models.CharField(max_length=3, choices=[("UZS", "UZS"), ("USD", "USD")], default="UZS")
    vat = models.CharField(max_length=50, blank=True, default="")
    offer_text = models.TextField(blank=True, default="")
    offer2_date = models.DateField(null=True, blank=True)
    offer2_text = models.TextField(blank=True, default="")
    reason = models.CharField(max_length=500, blank=True, default="")
    note = models.TextField(blank=True, default="")
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="commercial_requests",
    )
    # Ikki kishi bir vaqtda o'zgartirsa, keyingisi eski ma'lumot ustiga yozmasin.
    version = models.PositiveIntegerField(default=1, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )

    class Meta:
        ordering = ["-number"]
        verbose_name = _("Inquiry")
        verbose_name_plural = _("Inquiries")

    def __str__(self):
        return f"{self.number} {self.short}"


class RequestContact(models.Model):
    request = models.ForeignKey(CommercialRequest, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=255, blank=True, default="")
    role = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=100, blank=True, default="")
    email = models.CharField(max_length=255, blank=True, default="")
    telegram = models.CharField(max_length=100, blank=True, default="")
    note = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class CommercialOffer(models.Model):
    """Saqlangan ТКП versiyasi. ``data`` — konstruktor holati, undan ТКП qayta ochiladi."""

    request = models.ForeignKey(CommercialRequest, on_delete=models.CASCADE, related_name="offers")
    number = models.CharField(max_length=50)
    version = models.PositiveIntegerField(default=1)
    date = models.DateField(null=True, blank=True)
    net = models.FloatField(default=0)
    vat = models.FloatField(default=0)
    total = models.FloatField(default=0)
    currency = models.CharField(max_length=3, default="UZS")
    data = models.JSONField(default=dict, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    author_name = models.CharField(max_length=255, blank=True, default="")  # Excel'dan ko'chirilganlarda
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["request", "number", "version"], name="pult_offer_version")]

    def __str__(self):
        return f"№{self.number} v{self.version}"


class OfferLibraryItem(models.Model):
    """«Справочник ТКП»: konstruktordagi pozitsiyalar, to'lov shartlari, izohlar, standart qiymatlar."""

    SECTIONS = [(s, s) for s in ("Позиция", "Группа", "Оплата", "Примечание", "Приложение", "Настройка")]

    section = models.CharField(max_length=20, choices=SECTIONS, verbose_name=_("Section"))
    group = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Group"))
    text = models.TextField(verbose_name=_("Text"))
    # Pozitsiyada — QQSsiz narx (so'm), «Настройка»da — qiymat matni.
    value = models.CharField(max_length=500, blank=True, default="", verbose_name=_("Price without VAT / setting value"))
    days = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Days"))
    is_default = models.BooleanField(default=False, verbose_name=_("On by default"))
    order = models.PositiveIntegerField(default=999)

    class Meta:
        ordering = ["section", "order", "id"]
        verbose_name = _("Offer library item")
        verbose_name_plural = _("Offer library")

    def __str__(self):
        return f"{self.section}: {self.text[:60]}"


class RequestLog(models.Model):
    request = models.ForeignKey(CommercialRequest, on_delete=models.CASCADE, related_name="log")
    date = models.DateField()
    text = models.CharField(max_length=500)
    author = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["date", "id"]

    def __str__(self):
        return f"{self.date} {self.text}"


class SealImage(models.Model):
    """Direktor imzosi va muhri (PNG). Media papkada emas, bazada shifrlangan
    holda turadi: fayl havolasi orqali olib bo'lmaydi (``inquiries.can_sign``)."""

    KINDS = [("seal", "Печать"), ("sign", "Подпись")]

    kind = models.CharField(max_length=10, choices=KINDS, unique=True)
    encrypted = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )

    def __str__(self):
        return self.get_kind_display()
