"""AI-agent servislari (Claude yoki Gemini bilan ishlaydi).

Barcha agentlar bitta `ask_ai()` chaqiruv nuqtasidan foydalanadi. Provayder
GEMINI_API_KEY / ANTHROPIC_API_KEY kalitlariga qarab avtomatik tanlanadi
(AI_PROVIDER bilan majburan belgilash ham mumkin). Hech qaysi kalit
o'rnatilmagan bo'lsa `is_configured()` False qaytaradi va agentlar hech narsa
qilmay o'tkazib yuboriladi — platforma AI'siz ham ishlayveradi.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def get_provider() -> str | None:
    """Ishlatiladigan provayderni qaytaradi: "gemini", "anthropic" yoki None."""
    forced = settings.AI_PROVIDER
    if forced:
        key = settings.GEMINI_API_KEY if forced == "gemini" else settings.ANTHROPIC_API_KEY
        return forced if key else None
    if settings.GEMINI_API_KEY:
        return "gemini"
    if settings.ANTHROPIC_API_KEY:
        return "anthropic"
    return None


def is_configured() -> bool:
    return get_provider() is not None


def ask_ai(system: str, prompt: str, max_tokens: int = 16000, agent: str = "") -> str:
    """Sozlangan provayderga bitta so'rov yuborib, javob matnini qaytaradi.

    Har bir chaqiruv (muvaffaqiyatli, bo'sh yoki xatoli) AILog'ga yoziladi;
    log yozishdagi xato agent ishini to'xtatmaydi."""
    import time

    from .models import AILog

    provider = get_provider()
    model = settings.GEMINI_MODEL if provider == "gemini" else settings.AI_MODEL
    start = time.monotonic()
    status, text, error = AILog.Status.SUCCESS, "", ""
    try:
        if provider == "gemini":
            text = ask_gemini(system, prompt, max_tokens)
        else:
            text = ask_claude(system, prompt, max_tokens)
        if not text:
            status = AILog.Status.EMPTY
    except Exception as exc:
        status, error = AILog.Status.ERROR, str(exc)
        raise
    finally:
        try:
            AILog.objects.create(
                agent=agent,
                provider=provider or "",
                model=model,
                system=system,
                prompt=prompt,
                response=text,
                status=status,
                error=error,
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception:
            logger.exception("AILog yozishda xato")
    return text


def ask_claude(system: str, prompt: str, max_tokens: int = 16000) -> str:
    """Claude'ga bitta so'rov yuborib, javob matnini qaytaradi."""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.AI_MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        logger.warning("Claude so'rovni rad etdi (stop_reason=refusal)")
        return ""
    return "".join(block.text for block in response.content if block.type == "text").strip()


def ask_gemini(system: str, prompt: str, max_tokens: int = 16000) -> str:
    """Gemini'ga bitta so'rov yuborib, javob matnini qaytaradi."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
        ),
    )
    return (response.text or "").strip()


# ---------------------------------------------------------------------------
# Telegram chat-yordamchi
# ---------------------------------------------------------------------------

TELEGRAM_CHAT_SYSTEM = """\
Sen "AiPlatforma" — qurilish kompaniyasining loyiha boshqaruv platformasidagi \
Telegram AI-yordamchisisan. Foydalanuvchi senga botda oddiy xabar yozadi.

Qoidalar:
- Faqat o'zbek tilida, qisqa va aniq javob ber (odatda 100 so'zdan oshmasin).
- Oddiy matn ishlat: Markdown, HTML yoki emoji ishlatma.
- Quyida platformadagi joriy holat surati beriladi — javoblaringni faqat shu \
ma'lumotlarga asosla. Suratda yo'q narsani to'qib chiqarma; ma'lumot yetmasa, \
buni ochiq ayt va saytdagi tegishli bo'limni tavsiya qil.
- Foydalanuvchi roli suratda ko'rsatilgan — javobni shunga moslashtir.
"""


def collect_chat_context(user) -> str:
    """Foydalanuvchi ko'ra oladigan loyihalar va ochiq vazifalarning matnli
    surati (AI javoblari uchun kontekst)."""
    from django.utils import timezone

    from apps.projects.permissions import visible_projects_for
    from apps.tasks.models import Task

    today = timezone.now().date()
    projects = visible_projects_for(user).select_related(None)
    open_tasks = (
        Task.objects.filter(project__in=projects)
        .exclude(status__in=[Task.Status.COMPLETED, Task.Status.APPROVED])
        .select_related("project", "assignee")
        .order_by("deadline")[:60]
    )

    parts = [
        f"Bugungi sana: {today}",
        f"Foydalanuvchi: {user.full_name} (rol: {user.get_role_display()})",
        "",
        "LOYIHALAR:",
    ]
    for p in projects[:30]:
        parts.append(
            f"- {p.name} | holat: {p.get_status_display()} | muddat: {p.deadline or '—'}"
        )
    parts.append("")
    parts.append("OCHIQ VAZIFALAR:")
    for t in open_tasks:
        assignee = t.assignee.full_name if t.assignee else "biriktirilmagan"
        overdue = " (MUDDATI O'TGAN)" if t.deadline and t.deadline < today else ""
        parts.append(
            f"- {t.title} | loyiha: {t.project.name} | mas'ul: {assignee}"
            f" | muddat: {t.deadline or '—'}{overdue} | holat: {t.get_status_display()}"
        )
    return "\n".join(parts)


def answer_telegram(user, text: str) -> str:
    """Telegram'dagi oddiy xabarga platforma konteksti asosida AI javobi."""
    context = collect_chat_context(user)
    prompt = f"{context}\n\nFOYDALANUVCHI XABARI:\n{text[:2000]}"
    return ask_ai(TELEGRAM_CHAT_SYSTEM, prompt, agent="telegram")


# ---------------------------------------------------------------------------
# Muddat nazorati agenti
# ---------------------------------------------------------------------------

DEADLINE_AGENT_SYSTEM = """\
Sen "AiPlatforma" — qurilish kompaniyasining loyiha boshqaruv platformasidagi \
muddat nazorati AI-agentisan. Senga muddati o'tgan va muddati yaqinlashayotgan \
vazifalar ro'yxati beriladi.

Vazifang: rahbariyat uchun qisqa, amaliy kunlik hisobot yozish.

Qoidalar:
- Faqat o'zbek tilida yoz.
- Oddiy matn ishlat: Markdown, HTML yoki emoji ishlatma (xabar Telegram va emailga ham yuboriladi).
- Eng muhimidan boshla: avval kritik/yuqori prioritetli va eng ko'p kechikkan vazifalar.
- Har bir muammoli vazifa uchun bitta qatorda: vazifa, loyiha, mas'ul, necha kun kechikkan.
- Oxirida 1-3 ta aniq tavsiya ber (masalan, qaysi vazifani qayta taqsimlash yoki kim bilan gaplashish kerak).
- Butun hisobot 200 so'zdan oshmasin.
"""


def collect_deadline_context() -> str | None:
    """Muddati o'tgan va 3 kun ichida muddati keladigan ochiq vazifalar
    bo'yicha matnli suratni qaytaradi; xabar beradigan narsa bo'lmasa None."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.tasks.models import Task

    today = timezone.now().date()
    soon = today + timedelta(days=3)
    open_tasks = (
        Task.objects.exclude(status__in=[Task.Status.COMPLETED, Task.Status.APPROVED])
        .filter(deadline__isnull=False)
        .select_related("project", "assignee")
    )

    overdue = list(open_tasks.filter(deadline__lt=today).order_by("deadline"))
    due_soon = list(open_tasks.filter(deadline__gte=today, deadline__lte=soon).order_by("deadline"))
    if not overdue and not due_soon:
        return None

    def line(task):
        assignee = task.assignee.full_name if task.assignee else "biriktirilmagan"
        return (
            f"- {task.title} | loyiha: {task.project.name} | mas'ul: {assignee}"
            f" | muddat: {task.deadline} | holat: {task.get_status_display()}"
            f" | prioritet: {task.get_priority_display()}"
        )

    parts = [f"Bugungi sana: {today}"]
    if overdue:
        parts.append("")
        parts.append("MUDDATI O'TGAN VAZIFALAR:")
        parts.extend(line(t) for t in overdue)
    if due_soon:
        parts.append("")
        parts.append("3 KUN ICHIDA MUDDATI KELADIGAN VAZIFALAR:")
        parts.extend(line(t) for t in due_soon)
    return "\n".join(parts)


def run_deadline_agent() -> str | None:
    """Kontekstni yig'ib AI'dan hisobot oladi. Hisobot matnini yoki
    (xabar beradigan narsa bo'lmasa) None qaytaradi."""
    context = collect_deadline_context()
    if context is None:
        return None
    return ask_ai(DEADLINE_AGENT_SYSTEM, context, agent="deadline") or None
