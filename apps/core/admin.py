from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.utils import timezone

from apps.accounts.roles import is_admin_role

AUDIT_FIELDS = ("created_by", "created_at", "updated_by", "updated_at")
AUDIT_FIELDSET_TITLE = "Audit trail"


def audit_fieldset():
    """Drop-in fieldset for ModelAdmin.fieldsets."""
    return (AUDIT_FIELDSET_TITLE, {"fields": AUDIT_FIELDS, "classes": ("collapse",)})


def _stamp(user, when):
    if when is None:
        return "-"
    who = (user.get_full_name() or user.get_username()) if user else "unknown"
    return f"{who} · {timezone.localtime(when):%d %b %Y, %H:%M}"


class AdminOnlyDeleteMixin:
    """Deleting is reserved for the `admin` role (and superusers).

    This is defence in depth: the inventory_manager group is never granted `delete_*`
    permissions, *and* this override refuses deletion even if somebody later grants
    them by mistake.  Django's `delete_selected` action disappears automatically when
    has_delete_permission is False.  Works for ModelAdmin and for inlines.
    """

    def has_delete_permission(self, request, obj=None):
        return is_admin_role(request.user) and super().has_delete_permission(request, obj)


class AuditedModelAdmin(AdminOnlyDeleteMixin, admin.ModelAdmin):
    """Fills in created_by / updated_by and shows the audit trail in list + form views."""

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        model_fields = {f.name for f in self.model._meta.get_fields()}
        readonly += [f for f in AUDIT_FIELDS if f in model_fields and f not in readonly]
        return readonly

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:  # nothing to audit yet on the "add" page
            fieldsets = [fs for fs in fieldsets if fs[0] != AUDIT_FIELDSET_TITLE]
        return fieldsets

    def save_model(self, request, obj, form, change):
        obj.set_audit_user(request.user)
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            if hasattr(instance, "set_audit_user"):
                instance.set_audit_user(request.user)
            instance.save()
        formset.save_m2m()

    # Compact "who · when" columns that sort by the underlying timestamp.
    @admin.display(description="Added by / on", ordering="created_at")
    def added_by_on(self, obj):
        return _stamp(obj.created_by, obj.created_at)

    @admin.display(description="Last modified by / on", ordering="updated_at")
    def modified_by_on(self, obj):
        return _stamp(obj.updated_by, obj.updated_at)


class AuditedInlineMixin(AdminOnlyDeleteMixin):
    """Use on inlines whose model extends AuditModel."""


@admin.register(LogEntry)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only, admin-only view of Django's built-in change log.

    Every add / change / delete made through the admin (including changed field names)
    is stored in LogEntry automatically; this page lets an administrator review the
    inventory managers' work across all models in one place.
    """

    list_display = ("action_time", "user", "content_type", "object_repr", "action", "summary")
    list_filter = ("user", "action_flag", "content_type")
    search_fields = ("object_repr", "change_message", "user__username")
    date_hierarchy = "action_time"
    list_select_related = ("user", "content_type")
    list_per_page = 50

    @admin.display(description="Action")
    def action(self, obj):
        return obj.get_action_flag_display()

    @admin.display(description="What changed")
    def summary(self, obj):
        return obj.get_change_message()

    def has_view_permission(self, request, obj=None):
        return is_admin_role(request.user)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
