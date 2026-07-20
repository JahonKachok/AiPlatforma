"""Telegram AI-agent uchun platforma amallari (Gemini function calling).

`build_telegram_tools(user)` foydalanuvchi roliga qarab AI chaqira oladigan
funksiyalar ro'yxatini qaytaradi. O'qish vositalari hammaga, o'zgartiruvchi
vositalar faqat admin/menejerga beriladi — shunda oddiy foydalanuvchining
AI'si bu amallarni umuman "ko'rmaydi".

Har bir funksiya natijani AI o'qiydigan qisqa matn sifatida qaytaradi; AI uni
foydalanuvchiga o'z tilida yetkazadi. Xato/noaniqlik ham matn sifatida
qaytariladi (exception emas) — AI foydalanuvchidan aniqlashtirishni so'raydi.
"""
import logging
from datetime import date

from django.conf import settings

logger = logging.getLogger(__name__)

MAX_RESULTS = 10


def _parse_date(value: str):
    """'' -> None; noto'g'ri format -> ValueError."""
    if not value:
        return None
    return date.fromisoformat(value)


def _can_mutate(user) -> bool:
    from apps.accounts.models import User

    return user.is_superuser or user.role in (User.Role.ADMIN, User.Role.MANAGER)


def build_telegram_tools(user, found_documents: list | None = None):
    """Foydalanuvchi uchun ruxsat etilgan AI vositalari ro'yxati.

    `found_documents` berilsa (bo'sh list), `find_documents` topgan va faylga
    ega hujjatlarning {"id", "name"} yozuvlarini shu ro'yxatga qo'shadi —
    chaqiruvchi tomon (Telegram handler) shu asosda haqiqiy fayllarni
    foydalanuvchiga yuborishi mumkin."""
    from apps.documents.models import AuditLog, Document
    from apps.notifications.services import notify_user
    from apps.projects.models import Project
    from apps.projects.permissions import can_create_project, ensure_project_member, visible_projects_for
    from apps.tasks.models import Task

    def _find_project(name: str):
        """Ko'rinadigan loyihalar orasidan nom bo'yicha bittasini topadi.
        (project, None) yoki (None, xato_matni) qaytaradi."""
        qs = visible_projects_for(user).filter(name__icontains=name.strip())
        matches = list(qs[:5])
        if not matches:
            return None, f"'{name}' nomli loyiha topilmadi."
        if len(matches) > 1:
            names = "; ".join(p.name for p in matches)
            return None, f"Bir nechta loyiha mos keldi: {names}. Qaysi birini aniq ayting."
        return matches[0], None

    # --- O'qish vositalari (hamma uchun) ---------------------------------

    def find_documents(query: str) -> str:
        """Hujjatlarni qidiradi (nomi yoki tegishli loyiha nomi bo'yicha)
        va havolalari bilan ro'yxat qaytaradi.

        query: hujjat nomining yoki loyiha nomining bir qismi (masalan,
        "shartnoma" yoki "45-maktab binosi" — ikkalasi ham ishlaydi).
        """
        from django.db.models import Q

        q = query.strip()
        docs = list(Document.objects.filter(project__in=visible_projects_for(user))
            .filter(Q(name__icontains=q) | Q(project__name__icontains=q))
            .select_related("project")[:MAX_RESULTS])
        if not docs:
            return f"'{q}' bo'yicha hujjat topilmadi."
        if found_documents is not None:
            found_documents.extend(
                {"id": str(d.pk), "name": d.name} for d in docs if d.file
            )
        lines = [
            f"- {d.name} (loyiha: {d.project.name}, holat: {d.get_status_display()}) "
            f"{settings.FRONTEND_URL}/documents/{d.pk}/"
            for d in docs
        ]
        return "Topilgan hujjatlar:\n" + "\n".join(lines)

    def find_tasks(query: str) -> str:
        """Vazifalarni sarlavhasi bo'yicha qidiradi (holati va mas'uli bilan).

        query: vazifa sarlavhasining bir qismi.
        """
        tasks = (Task.objects.filter(
            project__in=visible_projects_for(user), title__icontains=query.strip())
            .select_related("project", "assignee")[:MAX_RESULTS])
        if not tasks:
            return f"'{query}' bo'yicha vazifa topilmadi."
        lines = [
            f"- {t.title} | loyiha: {t.project.name} | holat: {t.get_status_display()}"
            f" | mas'ul: {t.assignee.full_name if t.assignee else 'biriktirilmagan'}"
            f" | muddat: {t.deadline or '—'}"
            for t in tasks
        ]
        return "Topilgan vazifalar:\n" + "\n".join(lines)

    def list_projects() -> str:
        """Foydalanuvchi ko'ra oladigan barcha loyihalar ro'yxati (holati va muddati bilan)."""
        projects = visible_projects_for(user).order_by("-created_at")[:20]
        if not projects:
            return "Loyihalar yo'q."
        lines = [
            f"- {p.name} | holat: {p.get_status_display()} | muddat: {p.deadline or '—'}"
            for p in projects
        ]
        return "Loyihalar:\n" + "\n".join(lines)

    def list_overdue_tasks() -> str:
        """Muddati o'tgan va 3 kun ichida muddati keladigan ochiq vazifalar ro'yxati."""
        from datetime import timedelta

        from django.utils import timezone

        today = timezone.now().date()
        tasks = (Task.objects.filter(
            project__in=visible_projects_for(user),
            deadline__isnull=False, deadline__lte=today + timedelta(days=3))
            .exclude(status__in=[Task.Status.COMPLETED, Task.Status.APPROVED])
            .select_related("project", "assignee").order_by("deadline")[:20])
        if not tasks:
            return "Muddati o'tgan yoki yaqin muddatli ochiq vazifa yo'q."
        lines = [
            f"- {t.title} | loyiha: {t.project.name}"
            f" | mas'ul: {t.assignee.full_name if t.assignee else 'biriktirilmagan'}"
            f" | muddat: {t.deadline}{' (MUDDATI O´TGAN)' if t.deadline < today else ''}"
            f" | holat: {t.get_status_display()}"
            for t in tasks
        ]
        return "Muddati o'tgan/yaqin vazifalar:\n" + "\n".join(lines)

    tools = [find_documents, find_tasks, list_projects, list_overdue_tasks]

    if not _can_mutate(user):
        return tools

    # --- O'zgartiruvchi vositalar (faqat admin/menejer) -------------------

    def create_project(name: str, description: str = "", deadline: str = "") -> str:
        """Yangi loyiha yaratadi.

        name: loyiha nomi (majburiy).
        description: qisqa tavsif (ixtiyoriy).
        deadline: topshirish muddati, YYYY-MM-DD formatida (ixtiyoriy).
        """
        if not can_create_project(user):
            return "Sizning rolingizda loyiha yaratish huquqi yo'q."
        name = name.strip()
        if not name:
            return "Loyiha nomi bo'sh bo'lishi mumkin emas."
        if visible_projects_for(user).filter(name__iexact=name).exists():
            return f"'{name}' nomli loyiha allaqachon mavjud."
        try:
            deadline_date = _parse_date(deadline)
        except ValueError:
            return f"Muddat formati noto'g'ri: '{deadline}'. YYYY-MM-DD bo'lishi kerak."
        project = Project.objects.create(
            name=name, description=description or None,
            deadline=deadline_date, created_by=user,
        )
        ensure_project_member(project, user)
        AuditLog.log(obj=project, action="created", user=user, details={"source": "telegram-ai"})
        return (f"Loyiha yaratildi: {project.name}"
                f" (muddat: {project.deadline or 'belgilanmagan'})."
                f" Havola: {settings.FRONTEND_URL}/projects/{project.pk}/")

    def update_project_status(project_name: str, status: str) -> str:
        """Loyiha holatini o'zgartiradi.

        project_name: loyiha nomi (yoki bir qismi).
        status: yangi holat — active, on_hold, completed yoki cancelled.
        """
        if status not in Project.Status.values:
            return f"Noto'g'ri holat: '{status}'. Mumkin: {', '.join(Project.Status.values)}."
        project, err = _find_project(project_name)
        if err:
            return err
        old = project.get_status_display()
        project.status = status
        project.save(update_fields=["status", "updated_at"])
        AuditLog.log(obj=project, action="status_changed", user=user,
                     details={"source": "telegram-ai", "from": old, "to": status})
        return f"'{project.name}' holati o'zgartirildi: {old} -> {project.get_status_display()}."

    def create_task(project_name: str, title: str, assignee_name: str = "",
                    deadline: str = "", priority: str = "medium", description: str = "") -> str:
        """Loyihada yangi vazifa yaratadi va xohlasa mas'ul biriktiradi.

        project_name: loyiha nomi (yoki bir qismi).
        title: vazifa sarlavhasi (majburiy).
        assignee_name: mas'ul xodim ismi (ixtiyoriy).
        deadline: muddat, YYYY-MM-DD formatida (ixtiyoriy).
        priority: low, medium, high yoki critical (standart: medium).
        description: vazifa tavsifi (ixtiyoriy).
        """
        from apps.accounts.models import User

        project, err = _find_project(project_name)
        if err:
            return err
        if not title.strip():
            return "Vazifa sarlavhasi bo'sh bo'lishi mumkin emas."
        if priority not in Task.Priority.values:
            return f"Noto'g'ri prioritet: '{priority}'. Mumkin: {', '.join(Task.Priority.values)}."
        try:
            deadline_date = _parse_date(deadline)
        except ValueError:
            return f"Muddat formati noto'g'ri: '{deadline}'. YYYY-MM-DD bo'lishi kerak."

        assignee = None
        if assignee_name.strip():
            candidates = list(User.objects.filter(
                is_active=True, full_name__icontains=assignee_name.strip())[:5])
            if not candidates:
                return f"'{assignee_name}' ismli faol xodim topilmadi."
            if len(candidates) > 1:
                names = "; ".join(u.full_name for u in candidates)
                return f"Bir nechta xodim mos keldi: {names}. Qaysi birini aniq ayting."
            assignee = candidates[0]

        task = Task.objects.create(
            title=title.strip(), description=description or None, project=project,
            assignee=assignee, creator=user, priority=priority, deadline=deadline_date,
        )
        if assignee:
            ensure_project_member(project, assignee)
            notify_user(
                assignee, "task", "Yangi vazifa",
                f"Sizga vazifa biriktirildi: {task.title} ({project.name})",
                link=f"/tasks/{task.pk}/",
            )
        AuditLog.log(obj=task, action="created", user=user, details={"source": "telegram-ai"})
        masul = assignee.full_name if assignee else "biriktirilmagan"
        return (f"Vazifa yaratildi: '{task.title}' | loyiha: {project.name}"
                f" | mas'ul: {masul} | muddat: {task.deadline or 'belgilanmagan'}"
                f" | prioritet: {task.get_priority_display()}.")

    def update_task_status(task_title: str, status: str, project_name: str = "") -> str:
        """Vazifa holatini o'zgartiradi.

        task_title: vazifa sarlavhasi (yoki bir qismi).
        status: yangi holat — new, in_progress, review, revision, approved yoki completed.
        project_name: bir xil nomli vazifalar bo'lsa, loyiha nomi bilan aniqlashtirish (ixtiyoriy).
        """
        if status not in Task.Status.values:
            return f"Noto'g'ri holat: '{status}'. Mumkin: {', '.join(Task.Status.values)}."
        qs = Task.objects.filter(
            project__in=visible_projects_for(user), title__icontains=task_title.strip()
        ).select_related("project")
        if project_name.strip():
            qs = qs.filter(project__name__icontains=project_name.strip())
        matches = list(qs[:5])
        if not matches:
            return f"'{task_title}' nomli vazifa topilmadi."
        if len(matches) > 1:
            names = "; ".join(f"{t.title} ({t.project.name})" for t in matches)
            return f"Bir nechta vazifa mos keldi: {names}. Loyiha nomi bilan aniqlashtiring."
        task = matches[0]
        old = task.get_status_display()
        task.status = status
        task.save(update_fields=["status", "updated_at"])
        AuditLog.log(obj=task, action="status_changed", user=user,
                     details={"source": "telegram-ai", "from": old, "to": status})
        if task.assignee and task.assignee != user:
            notify_user(
                task.assignee, "task", "Vazifa holati o'zgardi",
                f"'{task.title}' holati: {task.get_status_display()}",
                link=f"/tasks/{task.pk}/",
            )
        return f"'{task.title}' holati o'zgartirildi: {old} -> {task.get_status_display()}."

    tools.extend([create_project, update_project_status, create_task, update_task_status])
    return tools
