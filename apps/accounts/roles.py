"""Single source of truth for roles and their permissions.

`python manage.py setup_roles` materialises this into Django groups (idempotent).
Note that inventory_manager is deliberately granted NO delete_* permission.
"""

ROLE_ADMIN = "admin"
ROLE_INVENTORY_MANAGER = "inventory_manager"

# app_label -> model_name -> allowed actions
MANAGER_PERMISSIONS = {
    "inventory": {
        "category": ("add", "change", "view"),
        "laptop": ("add", "change", "view"),
        "laptopimage": ("add", "change", "view"),
    },
    # Managers can triage inquiries (status / notes) but never create or delete them.
    "inquiries": {"inquiry": ("view", "change")},
}

# The admin role gets every permission (incl. delete) on these apps, plus the audit log.
ADMIN_APP_LABELS = ("accounts", "inventory", "inquiries")
ADMIN_EXTRA_PERMISSIONS = (("admin", "view_logentry"),)


def get_roles(user):
    if not (user.is_authenticated and user.is_active):
        return frozenset()
    cached = getattr(user, "_role_cache", None)
    if cached is None:
        cached = frozenset(user.groups.values_list("name", flat=True))
        user._role_cache = cached
    return cached


def is_admin_role(user):
    """Superusers always count as administrators."""
    return bool(user.is_active and (user.is_superuser or ROLE_ADMIN in get_roles(user)))


def is_inventory_manager(user):
    return ROLE_INVENTORY_MANAGER in get_roles(user)
