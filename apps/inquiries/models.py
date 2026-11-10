from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(r"^\+?[0-9][0-9\s-]{7,17}$", "Enter a valid phone number (8-18 digits).")


class Inquiry(models.Model):
    """A customer's interest in one laptop. Customers are anonymous, so there is no
    created_by; staff handling is tracked in updated_by / updated_at instead.

    The laptop's title and SKU are snapshotted so the inquiry stays meaningful even if
    the listing is later deleted (FK is SET_NULL).
    """

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        NEGOTIATING = "negotiating", "Negotiating"
        WON = "won", "Closed - sold"
        LOST = "lost", "Closed - lost"
        SPAM = "spam", "Spam"

    class ContactMethod(models.TextChoices):
        PHONE = "phone", "Phone call"
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "Email"

    laptop = models.ForeignKey("inventory.Laptop", null=True, blank=True, on_delete=models.SET_NULL, related_name="inquiries")
    laptop_title = models.CharField(max_length=200)
    laptop_sku = models.CharField(max_length=40, blank=True)

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20, validators=[phone_validator])
    preferred_contact = models.CharField(max_length=10, choices=ContactMethod.choices, default=ContactMethod.PHONE)
    message = models.TextField(max_length=2000)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW, db_index=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_inquiries")
    internal_notes = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.PROTECT, related_name="inquiries_updated", verbose_name="last handled by",
    )

    class Meta:
        verbose_name_plural = "inquiries"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"], name="inquiry_status_new_idx")]

    def __str__(self):
        return f"{self.name} - {self.laptop_title}"

    def set_audit_user(self, user):
        if user is not None and getattr(user, "is_authenticated", False):
            self.updated_by = user
