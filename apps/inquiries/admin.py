from django.contrib import admin

from apps.core.admin import AuditedModelAdmin

from .models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(AuditedModelAdmin):
    list_display = ("created_at", "name", "laptop_title", "phone", "preferred_contact", "status", "assigned_to", "updated_by", "updated_at")
    list_filter = ("status", "preferred_contact", "assigned_to", "created_at")
    search_fields = ("name", "email", "phone", "laptop_title", "laptop_sku")
    date_hierarchy = "created_at"
    list_select_related = ("assigned_to", "updated_by")
    # Customer-submitted data is immutable; staff only triage (status / owner / notes).
    readonly_fields = ("name", "email", "phone", "preferred_contact", "message", "laptop", "laptop_title", "laptop_sku", "ip_address")
    fieldsets = (
        ("Customer", {"fields": ("name", "email", "phone", "preferred_contact", "message")}),
        ("Laptop", {"fields": ("laptop", "laptop_title", "laptop_sku")}),
        ("Handling", {"fields": ("status", "assigned_to", "internal_notes")}),
        ("Audit trail", {"fields": ("created_at", "ip_address", "updated_by", "updated_at"), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False  # inquiries only come from the public form
