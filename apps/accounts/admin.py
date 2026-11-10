from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "get_full_name", "email", "roles", "is_staff", "is_active", "last_login")
    list_filter = ("groups", "is_staff", "is_active")
    fieldsets = DjangoUserAdmin.fieldsets + (("Contact", {"fields": ("phone",)}),)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("groups")

    @admin.display(description="Roles")
    def roles(self, obj):
        return ", ".join(sorted(g.name for g in obj.groups.all())) or "-"

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            # An `admin`-role user must not be able to mint superusers or hand out raw permissions.
            readonly += ["is_superuser", "user_permissions"]
        return readonly
