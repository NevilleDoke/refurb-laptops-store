from django.contrib import admin
from django.db.models import Count

from apps.core.admin import AuditedInlineMixin, AuditedModelAdmin, audit_fieldset

from .models import Brand, Category, Laptop, LaptopImage, NewsletterSubscriber


@admin.register(Category)
class CategoryAdmin(AuditedModelAdmin):
    list_display = ("name", "slug", "is_active", "laptop_count", "added_by_on", "modified_by_on")
    list_filter = ("is_active", "created_by", "updated_by", "updated_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    date_hierarchy = "updated_at"
    list_select_related = ("created_by", "updated_by")
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "is_active")}),
        audit_fieldset(),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_laptop_count=Count("laptops"))

    @admin.display(description="Laptops", ordering="_laptop_count")
    def laptop_count(self, obj):
        return obj._laptop_count


class LaptopImageInline(AuditedInlineMixin, admin.TabularInline):
    model = LaptopImage
    extra = 1
    fields = ("image", "alt_text", "is_primary", "sort_order")


@admin.register(Laptop)
class LaptopAdmin(AuditedModelAdmin):
    list_display = (
        "sku", "title", "category", "brand", "ram_gb", "storage_gb", "condition",
        "price", "status", "is_featured", "added_by_on", "modified_by_on",
    )
    list_editable = ("status", "is_featured")
    list_filter = (
        "status", "condition", "category", "brand", "storage_type", "ram_gb",
        "created_by", "updated_by", "created_at", "updated_at",
    )
    search_fields = ("sku", "title", "brand", "model_name", "processor")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category",)
    date_hierarchy = "updated_at"
    list_select_related = ("category", "created_by", "updated_by")
    list_per_page = 50
    inlines = [LaptopImageInline]
    fieldsets = (
        ("Identity", {"fields": ("title", "slug", "sku", "category", "brand", "model_name")}),
        ("Specifications", {"fields": (
            "processor", "ram_gb", "storage_gb", "storage_type",
            "screen_size_in", "gpu", "operating_system", "battery_health_pct",
        )}),
        ("Condition & pricing", {"fields": ("condition", "warranty_months", "price", "original_price")}),
        ("Listing", {"fields": ("status", "is_featured", "description")}),
        audit_fieldset(),
    )


@admin.register(Brand)
class BrandAdmin(AuditedModelAdmin):
    list_display = ("name", "slug", "is_active", "logo", "laptop_count")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_laptop_count=Count("laptops"))

    @admin.display(description="Laptops", ordering="_laptop_count")
    def laptop_count(self, obj):
        return obj._laptop_count


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("email",)
    list_editable = ("is_active",)
