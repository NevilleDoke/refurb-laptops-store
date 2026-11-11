"""Rule-based laptop matching for the AI chat bot.

No external LLM / API key is required: the bot parses the shopper's free-text
question for brands, budget, RAM, storage, screen size and usage, then filters
the public laptop catalog.  It is intentionally simple and easy to extend or
replace with a real LLM later.
"""
import re
from decimal import Decimal, InvalidOperation

from django.db.models import Q

from apps.inventory.models import Laptop

# Brands the bot recognises (matched case-insensitively).
KNOWN_BRANDS = [
    "hp", "dell", "lenovo", "apple", "asus", "acer", "msi", "samsung",
    "microsoft", "toshiba", "ibm",
]

# Usage hints the bot uses to bias results.
USAGE_KEYWORDS = {
    "gaming": ["gaming", "game", "games", "fps", "gtx", "rtx", "graphics"],
    "office": ["office", "business", "work", "document", "excel", "word"],
    "student": ["student", "college", "school", "studies", "assignments"],
    "programming": ["programming", "coding", "developer", "code", "python", "java"],
    "video_editing": ["video editing", "editing", "render", "premiere"],
}


def _extract_brands(text):
    return [b for b in KNOWN_BRANDS if b in text]


def _extract_ram(text):
    rams = set()
    for m in re.finditer(r"(\d+)\s*gb\b", text):
        rams.add(int(m.group(1)))
    return sorted(rams)


def _extract_storage(text):
    storages = set()
    for m in re.finditer(r"(\d+)\s*(?:gb|tb)\b", text):
        size = int(m.group(1))
        unit = m.group(0)[-2:]
        if unit == "tb":
            size *= 1024
        storages.add(size)
    return sorted(storages)


def _extract_price(text):
    """Return (min_price, max_price) in Decimal, or (None, None)."""
    min_p = None
    max_p = None

    # "under / below / less than / max / up to / within ₹50000"
    m = re.search(
        r"(?:under|below|less than|max|maximum|upto|up to|within)\s*₹?\s*([\d,]+)",
        text,
    )
    if m:
        max_p = Decimal(m.group(1).replace(",", ""))

    # "₹30000-₹60000", "30000 to 60000"
    m = re.search(r"₹?\s*([\d,]+)\s*(?:-|to|to)\s*₹?\s*([\d,]+)", text)
    if m:
        min_p = Decimal(m.group(1).replace(",", ""))
        max_p = Decimal(m.group(2).replace(",", ""))

    # "above / over / min / starting from ₹40000"
    m = re.search(
        r"(?:above|over|min|minimum|starting from)\s*₹?\s*([\d,]+)", text
    )
    if m and min_p is None:
        min_p = Decimal(m.group(1).replace(",", ""))

    return min_p, max_p


def _extract_screen(text):
    screens = set()
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:inch|in)\b", text):
        screens.add(float(m.group(1)))
    return sorted(screens)


def match_laptops(query, limit=6):
    """Return public laptops matching the free-text `query`, ordered by relevance."""
    low = query.lower()
    qs = (
        Laptop.objects.public()
        .select_related("category")
        .prefetch_related("images")
    )

    brand_q = Q()
    for b in _extract_brands(low):
        brand_q |= Q(brand__iexact=b)
    if brand_q:
        qs = qs.filter(brand_q)

    rams = _extract_ram(low)
    if rams:
        qs = qs.filter(ram_gb__gte=min(rams))

    storages = _extract_storage(low)
    if storages:
        qs = qs.filter(storage_gb__gte=min(storages))

    screens = _extract_screen(low)
    if screens:
        qs = qs.filter(screen_size_in__gte=min(screens))

    min_p, max_p = _extract_price(low)
    if min_p is not None:
        qs = qs.filter(price__gte=min_p)
    if max_p is not None:
        qs = qs.filter(price__lte=max_p)

    # Usage-based soft signals (kept as ordering hints rather than hard filters
    # so we still return results when the spec is light).
    if any(k in low for k in USAGE_KEYWORDS["gaming"]):
        qs = qs.exclude(gpu="").order_by("-ram_gb", "-price", "-created_at")
    else:
        qs = qs.order_by("-is_featured", "price", "-created_at")

    return list(qs[:limit])


def build_reply(message, matches):
    """Build the bot's text reply for a user message and matched laptops."""
    if not matches:
        return (
            "I couldn't find any laptops matching that. Try a different budget or "
            "spec (e.g. \"gaming laptop under ₹50000\"), or tap 'Send inquiry' "
            "below and our team will suggest options."
        )
    if len(matches) == 1:
        return (
            f"I found one laptop that fits your needs: <strong>{matches[0].title}</strong>. "
            "Tap it to view details or send an enquiry."
        )
    return (
        f"I found <strong>{len(matches)}</strong> laptops that match your needs. "
        "Tap one to view details, or send an enquiry and we'll help you pick."
    )
