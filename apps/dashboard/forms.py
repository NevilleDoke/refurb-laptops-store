from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from apps.core.forms import style_fields

from apps.inventory.models import Category, Laptop
from apps.inquiries.models import Inquiry


class StaffLoginForm(AuthenticationForm):
    """Login form for the staff dashboard, styled like the rest of the app."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "slug", "description", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class LaptopForm(forms.ModelForm):
    cover_image = forms.ImageField(required=False, label="Cover photo")

    class Meta:
        model = Laptop
        fields = (
            "title",
            "slug",
            "sku",
            "category",
            "brand",
            "model_name",
            "processor",
            "ram_gb",
            "storage_gb",
            "storage_type",
            "screen_size_in",
            "gpu",
            "operating_system",
            "battery_health_pct",
            "condition",
            "warranty_months",
            "price",
            "original_price",
            "description",
            "status",
            "is_featured",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        self.fields["ram_gb"].widget.attrs.update({"min": "1"})
        self.fields["price"].widget.attrs.update({"step": "0.01", "min": "0"})
        self.fields["original_price"].widget.attrs.update({"step": "0.01", "min": "0"})


class InquiryHandlingForm(forms.ModelForm):
    """Staff-only triage form: status, owner, internal notes. Customer data is
    immutable once submitted."""

    class Meta:
        model = Inquiry
        fields = ("status", "assigned_to", "internal_notes")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
        self.fields["assigned_to"].queryset = (
            get_user_model().objects.filter(is_staff=True, is_active=True).order_by("username")
        )
        self.fields["assigned_to"].empty_label = "Unassigned"
