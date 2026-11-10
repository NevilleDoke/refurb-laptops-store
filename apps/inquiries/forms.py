from django import forms

from apps.core.forms import style_fields

from .models import Inquiry


class InquiryForm(forms.ModelForm):
    # Honeypot: hidden from humans via CSS; bots that fill every input give themselves away.
    website = forms.CharField(required=False, label="Website", widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    class Meta:
        model = Inquiry
        fields = ["name", "email", "phone", "preferred_contact", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4, "placeholder": "Questions, preferred visit time, offer..."}),
            "phone": forms.TextInput(attrs={"inputmode": "tel", "placeholder": "+91 98xxxxxxxx"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
