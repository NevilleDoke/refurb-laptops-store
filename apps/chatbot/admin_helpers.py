"""Administrative command handling for the AI chat bot.

These handlers let staff use the chat bot to:
  * view store stats / administrative summary
  * list and check customer inquiries
  * add new categories
  * add new laptops (minimal fields, then edit in the dashboard)
All handlers require an authenticated staff user.
"""
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from django.utils.text import slugify

from apps.inventory.models import Category, Laptop
from apps.inquiries.models import Inquiry


def _require_staff(user):
    return user is not None and getattr(user, "is_authenticated", False) and getattr(user, "is_staff", False)


def _format_inquiry_line(inv):
    return (
        f"• #{inv.pk} {inv.name} — {inv.laptop_title}"
        f"{(f' ({inv.laptop_sku})' if inv.laptop_sku else '')}"
        f" <span class=\"font-medium text-slate-700\">[{inv.get_status_display()}]</span>"
    )


def admin_stats():
    """Dashboard-style administrative summary."""
    total_laptops = Laptop.objects.count()
    available = Laptop.objects.filter(status=Laptop.Status.AVAILABLE).count()
    reserved = Laptop.objects.filter(status=Laptop.Status.RESERVED).count()
    sold = Laptop.objects.filter(status=Laptop.Status.SOLD).count()
    total_categories = Category.objects.count()
    active_categories = Category.objects.filter(is_active=True).count()
    total_inquiries = Inquiry.objects.count()
    new_inquiries = Inquiry.objects.filter(status=Inquiry.Status.NEW).count()

    return {
        "text": (
            "<strong>Store summary</strong><br>"
            f"• Laptops: {total_laptops} "
            f"(<span class=\"text-emerald-600\">{available}</span> available, "
            f"<span class=\"text-amber-600\">{reserved}</span> reserved, "
            f"<span class=\"text-slate-500\">{sold}</span> sold)<br>"
            f"• Categories: {total_categories} ({active_categories} active)<br>"
            f"• Inquiries: {total_inquiries} total, {new_inquiries} new"
        ),
        "matches": [],
    }


def admin_inquiries(message):
    """List recent inquiries, optionally filtered to new ones from the last 24h."""
    low = message.lower()
    qs = Inquiry.objects.select_related("laptop", "assigned_to").order_by("-created_at")
    if "new" in low:
        since = timezone.now() - timedelta(hours=24)
        qs = qs.filter(status=Inquiry.Status.NEW, created_at__gte=since)
    qs = qs[:10]

    if not qs:
        if "new" in low:
            return {"text": "No new inquiries in the last 24 hours.", "matches": []}
        return {"text": "No inquiries found.", "matches": []}

    lines = (
        "<strong>Recent inquiries</strong>"
        + (" (new)" if "new" in low else "")
        + "<ul class=\"list-disc pl-4 my-2 text-sm text-slate-700 space-y-1\">"
    )
    for inv in qs:
        lines += _format_inquiry_line(inv) + "<br>"
    lines += "</ul>"
    lines += (
        "<p class=\"mt-2 text-xs text-slate-500\">"
        "Open an inquiry in the dashboard to reply or change its status.</p>"
    )
    return {"text": lines, "matches": []}


def admin_add_category(message, user):
    """Create a category: `add category Gaming Laptops`."""
    if not _require_staff(user):
        return _not_authorized()
    prefix = "add category"
    idx = message.lower().find(prefix)
    name = message[idx + len(prefix):].strip() if idx != -1 else ""
    if not name:
        return {
            "text": "Please specify a category name. Example: <code>add category Gaming Laptops</code>",
            "matches": [],
        }

    base_slug = slugify(name) or name.lower().replace(" ", "-")
    slug = base_slug
    counter = 1
    while Category.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    category = Category(name=name, slug=slug, is_active=True)
    category.set_audit_user(user)
    category.save()
    return {
        "text": (
            f"Category <strong>{category.name}</strong> created (slug: <code>{category.slug}</code>). "
            "You can edit it in the dashboard."
        ),
        "matches": [],
    }


def admin_add_laptop(message, user):
    """Create a laptop from minimal info: `add laptop <title> | <brand> | <price> | <category> | <ram> | <storage>`.

    Falls back to pointing the admin at the add-laptop form when parsing fails.
    """
    if not _require_staff(user):
        return _not_authorized()
    prefix = "add laptop"
    idx = message.lower().find(prefix)
    payload = message[idx + len(prefix):].strip() if idx != -1 else ""
    if not payload:
        return {
            "text": (
                "Use the <a href=\"/staff/laptops/add/\" class=\"text-indigo-600 underline hover:text-indigo-700\">"
                "Add laptop form</a> in the dashboard, or try:\n"
                "<code>add laptop Dell Latitude 7490 | Dell | 45000 | business | 16 | 512</code>"
            ),
            "matches": [],
        }

    parts = [p.strip() for p in payload.split("|")]
    if len(parts) < 3:
        return {
            "text": (
                "Not enough details. Provide: title | brand | price | category | ram | storage<br>"
                "Example: <code>add laptop Dell Latitude 7490 | Dell | 45000 | business | 16 | 512</code>"
            ),
            "matches": [],
        }

    title, brand = parts[0], parts[1]
    try:
        price = float(parts[2].replace("₹", "").replace(",", "").strip())
    except ValueError:
        return {"text": "Invalid price. Example: <code>45000</code>", "matches": []}

    category = None
    if len(parts) >= 4 and parts[3]:
        category = Category.objects.filter(slug=parts[3]).first() or Category.objects.filter(name__iexact=parts[3]).first()

    ram_gb = int(parts[4]) if len(parts) >= 5 and parts[4] else 8
    storage_gb = int(parts[5]) if len(parts) >= 6 and parts[5] else 256

    from django.utils.text import slugify as _slugify
    slug = _slugify(title)
    base_slug = slug
    counter = 1
    while Laptop.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    laptop = Laptop(
        title=title,
        slug=slug,
        sku=f"LT-{slug.upper()[:12]}",
        brand=brand,
        model_name=title,
        processor="Intel Core i5",
        ram_gb=ram_gb,
        storage_gb=storage_gb,
        storage_type=Laptop.StorageType.SSD,
        price=price,
        condition=Laptop.Condition.GOOD,
        status=Laptop.Status.AVAILABLE,
        warranty_months=3,
        is_featured=False,
    )
    laptop.set_audit_user(user)
    laptop.save()
    if category:
        laptop.category = category
        laptop.save()

    return {
        "text": (
            f"Laptop <strong>{laptop.title}</strong> added (SKU: <code>{laptop.sku}</code>, "
            f"₹{laptop.price}). "
            f"<a href=\"/staff/laptops/{laptop.slug}/edit/\" class=\"text-indigo-600 underline hover:text-indigo-700\">"
            "Edit specs &amp; add photos →</a>"
        ),
        "matches": [],
    }


def admin_list_laptops(message):
    """List recent laptops: `laptops` or `inventory`."""
    low = message.lower()
    qs = Laptop.objects.select_related("category").order_by("-created_at")[:10]
    if "available" in low:
        qs = qs.filter(status=Laptop.Status.AVAILABLE)
    if not qs:
        return {"text": "No laptops found.", "matches": []}
    lines = "<strong>Recent laptops</strong><ul class=\"list-disc pl-4 my-2 text-sm text-slate-700 space-y-1\">"
    for lap in qs:
        lines += (
            f"• <a href=\"/staff/laptops/{lap.slug}/\" class=\"text-indigo-600 underline hover:text-indigo-700\">"
            f"{lap.title}</a> — {lap.brand} · ₹{lap.price} · {lap.get_status_display()}<br>"
        )
    lines += "</ul>"
    return {"text": lines, "matches": []}


def admin_help():
    return {
        "text": (
            "<strong>Admin assistant commands:</strong><br>"
            "• <code>stats</code> — store summary<br>"
            "• <code>inquiries</code> / <code>new inquiries</code> — check customer inquiries<br>"
            "• <code>add category &lt;name&gt;</code> — create a category<br>"
            "• <code>add laptop &lt;title&gt; | &lt;brand&gt; | &lt;price&gt; | &lt;category&gt; | &lt;ram&gt; | &lt;storage&gt;</code> — add a laptop<br>"
            "• <code>laptops</code> — list recent laptops<br>"
            "• <code>help</code> — show this menu"
        ),
        "matches": [],
    }


def handle_admin_command(message, user):
    """Route an admin message to the right handler."""
    low = message.lower().strip()

    if low in ("help", "commands", "menu"):
        return admin_help()
    if low in ("stats", "summary", "dashboard", "admin summary"):
        return admin_stats()
    if low.startswith("inquiry") or low in ("new inquiries", "check inquiries"):
        return admin_inquiries(low)
    if low.startswith("add category"):
        return admin_add_category(message, user)
    if low.startswith("add laptop"):
        return admin_add_laptop(message, user)
    if low.startswith("laptop") or low == "inventory":
        return admin_list_laptops(low)

    return admin_help()


def _not_authorized():
    return {"text": "You must be signed in as staff to use admin commands.", "matches": []}
