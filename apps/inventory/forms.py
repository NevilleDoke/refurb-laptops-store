from django import forms

from apps.core.forms import style_fields

from .models import Category, Laptop


class LaptopFilterForm(forms.Form):
    SORT_CHOICES = [
        ("featured", "Featured first"),
        ("newest", "Newest"),
        ("price_asc", "Price: low to high"),
        ("price_desc", "Price: high to low"),
    ]

    q = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={"placeholder": "Search model, CPU..."}))
    category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False, to_field_name="slug", empty_label="All categories")
    brand = forms.ChoiceField(required=False)
    ram = forms.TypedChoiceField(
        required=False, coerce=int, empty_value=None,
        choices=[("", "Any RAM"), (4, "4 GB+"), (8, "8 GB+"), (16, "16 GB+"), (32, "32 GB+")],
    )
    storage_type = forms.ChoiceField(required=False, choices=[("", "Any storage"), *Laptop.StorageType.choices])
    condition = forms.ChoiceField(required=False, choices=[("", "Any condition"), *Laptop.Condition.choices])
    min_price = forms.DecimalField(required=False, min_value=0, widget=forms.NumberInput(attrs={"placeholder": "Min price"}))
    max_price = forms.DecimalField(required=False, min_value=0, widget=forms.NumberInput(attrs={"placeholder": "Max price"}))
    sort = forms.ChoiceField(required=False, choices=SORT_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        brands = Laptop.objects.public().order_by("brand").values_list("brand", flat=True).distinct()
        self.fields["brand"].choices = [("", "All brands")] + [(b, b) for b in brands]
        style_fields(self)
