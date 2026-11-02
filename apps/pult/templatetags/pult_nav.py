from django import template
from django.urls import reverse

from ..nav import GROUP_HOME, SECTIONS, allowed_pages, section_url_name

register = template.Library()


@register.simple_tag(takes_context=True)
def pult_sections(context, group):
    """Menyu guruhidagi, foydalanuvchiga ruxsat etilgan Pult bo'limlari:
    [{"url", "label", "active"}, ...] — tablar qatorini chizish uchun."""
    request = context["request"]
    allowed = set(allowed_pages(request.user))
    out = []
    for section, (sec_group, _route, label) in SECTIONS.items():
        if sec_group != group or section not in allowed:
            continue
        url = reverse(f"pult:{section_url_name(section)}")
        out.append({"url": url, "label": label, "active": request.path == url})
    return out


@register.inclusion_tag("pult/_tabs.html", takes_context=True)
def pult_tabs(context, group):
    """Tablar qatori: guruhning asosiy sahifasi + uning Pult bo'limlari.
    Ruxsat etilgan bo'lim bo'lmasa, qator umuman chizilmaydi."""
    sections = pult_sections(context, group)
    url_name, label = GROUP_HOME[group]
    home_url = reverse(url_name)
    home = {"url": home_url, "label": label, "active": context["request"].path == home_url}
    return {"tabs": [home, *sections] if sections else []}
