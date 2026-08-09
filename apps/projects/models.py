import uuid

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .uz_regions import REGION_CHOICES

stir_validator = RegexValidator(r"^\d+$", _("STIR must contain digits only."))


class Project(models.Model):
    class Stage(models.TextChoices):
        CONCEPT = "concept", _("Concept")
        PRELIMINARY = "preliminary", _("Preliminary design")
        WORKING_DOCS = "working_docs", _("Working documentation")
        EXPERTISE = "expertise", _("Expertise")
        CONSTRUCTION = "construction", _("Construction")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        ON_HOLD = "on_hold", _("On hold")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    class ConstructionType(models.TextChoices):
        NEW = "new", _("New construction")
        RECONSTRUCTION = "reconstruction", _("Reconstruction")
        CAPITAL_REPAIR = "capital_repair", _("Capital repair")
        EXPANSION = "expansion", _("Expansion")

    class FundingSource(models.TextChoices):
        OWN_FUNDS = "own_funds", _("Client's own funds")
        STATE_BUDGET = "state_budget", _("State budget")
        LOAN = "loan", _("Loan funds")
        INVESTMENT = "investment", _("Investment")
        OTHER = "other", _("Other")

    class ClientType(models.TextChoices):
        LEGAL_ENTITY = "legal_entity", _("Legal entity")
        INDIVIDUAL = "individual", _("Individual")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    description = models.CharField(max_length=2000, blank=True, null=True, verbose_name=_("Description"))
    client_name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Client name"))
    client_contact = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Client contact"))
    client_type = models.CharField(
        max_length=20, choices=ClientType.choices, blank=True, null=True, verbose_name=_("Client type"),
    )
    client_stir = models.CharField(
        max_length=20, blank=True, null=True, validators=[stir_validator], verbose_name=_("STIR"),
    )
    client_email = models.EmailField(blank=True, null=True, verbose_name=_("Email"))
    client_contact_person = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_("Client contact person"),
    )
    client_position = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Client position"))
    client_notes = models.CharField(max_length=2000, blank=True, null=True, verbose_name=_("Client notes"))
    address = models.CharField(max_length=500, blank=True, null=True, verbose_name=_("Address"))
    region = models.CharField(max_length=30, choices=REGION_CHOICES, blank=True, null=True, verbose_name=_("Region"))
    district = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("District"))
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    construction_type = models.CharField(
        max_length=20, choices=ConstructionType.choices, blank=True, null=True,
        verbose_name=_("Construction type"),
    )
    sector = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Sector"))
    object_type = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Object type"))
    funding_source = models.CharField(
        max_length=20, choices=FundingSource.choices, blank=True, null=True, verbose_name=_("Funding source"),
    )
    construction_area = models.FloatField(blank=True, null=True, verbose_name=_("Construction area"))
    land_area = models.FloatField(blank=True, null=True, verbose_name=_("Land area"))
    construction_volume = models.FloatField(blank=True, null=True, verbose_name=_("Construction volume"))
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.CONCEPT, verbose_name=_("Stage"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, verbose_name=_("Status"))
    start_date = models.DateField(blank=True, null=True, verbose_name=_("Start date"))
    deadline = models.DateField(blank=True, null=True, verbose_name=_("Deadline"))
    budget = models.FloatField(default=0, verbose_name=_("Budget"))
    paid_amount = models.FloatField(default=0, verbose_name=_("Paid amount"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_projects"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def paid_percentage(self):
        if not self.budget:
            return 0
        return min(100, round(self.paid_amount / self.budget * 100))


class SectionStatus(models.TextChoices):
    NOT_STARTED = "not_started", _("Not started")
    IN_PROGRESS = "in_progress", _("In progress")
    REVIEW = "review", _("Review")
    COMPLETED = "completed", _("Completed")


class Priority(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class SubObject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="sub_objects")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="pod_objects", verbose_name=_("Pod object of"),
    )
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    description = models.CharField(max_length=2000, blank=True, null=True, verbose_name=_("Description"))
    address = models.CharField(max_length=500, blank=True, null=True, verbose_name=_("Address"))
    gip = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="gip_sub_objects", verbose_name=_("GIP"),
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.MEDIUM, verbose_name=_("Priority"),
    )
    status = models.CharField(
        max_length=20, choices=SectionStatus.choices, default=SectionStatus.NOT_STARTED, verbose_name=_("Status"),
    )
    start_date = models.DateField(blank=True, null=True, verbose_name=_("Start date"))
    deadline = models.DateField(blank=True, null=True, verbose_name=_("Deadline"))
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "name"]

    def __str__(self):
        return f"{self.project.name} / {self.name}"


class SubObjectDiscipline(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_object = models.ForeignKey(SubObject, on_delete=models.CASCADE, related_name="disciplines")
    discipline = models.ForeignKey(
        "accounts.Discipline", on_delete=models.CASCADE, related_name="sub_object_disciplines",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_sub_object_disciplines", verbose_name=_("Assignee"),
    )
    deadline = models.DateField(blank=True, null=True, verbose_name=_("Deadline"))
    status = models.CharField(
        max_length=20, choices=SectionStatus.choices, default=SectionStatus.NOT_STARTED, verbose_name=_("Status"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["sub_object", "discipline"], name="unique_sub_object_discipline"),
        ]
        ordering = ["discipline__code"]

    def __str__(self):
        return f"{self.discipline.code} @ {self.sub_object}"


class Section(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="sections")
    sub_object = models.ForeignKey(
        SubObject, on_delete=models.SET_NULL, null=True, blank=True, related_name="sections",
        verbose_name=_("Sub-object"),
    )
    discipline = models.ForeignKey(
        "accounts.Discipline", on_delete=models.PROTECT, related_name="sections", verbose_name=_("Discipline"),
    )
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    gip = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="gip_sections", verbose_name=_("GIP"),
    )
    status = models.CharField(
        max_length=20, choices=SectionStatus.choices, default=SectionStatus.NOT_STARTED, verbose_name=_("Status"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["discipline__code"]

    def __str__(self):
        return f"{self.discipline.code} — {self.name}"


class ProjectMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships",
        verbose_name=_("User"),
    )
    role_in_project = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Role in project"))
    can_edit = models.BooleanField(default=True, verbose_name=_("Can edit"))
    expires_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Expires at"))
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="unique_project_member"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.project}"

    def is_active(self):
        from django.utils import timezone
        return self.expires_at is None or self.expires_at > timezone.now()
