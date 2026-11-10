from django.conf import settings
from django.db import models


class AuditModel(models.Model):
    """Abstract base that records who created / last modified a row, and when.

    The *_by columns use PROTECT: a user who has created or edited records can't be
    hard-deleted (deactivate them instead), so the audit trail can never silently lose
    its author.  The fields are editable=False; the admin shows them read-only and
    fills them in automatically (see apps.core.admin.AuditedModelAdmin).  Any future
    API layer should call ``set_audit_user(request.user)`` before ``save()``.
    """

    created_at = models.DateTimeField(auto_now_add=True, editable=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, editable=False, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_created",
        verbose_name="added by",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_updated",
        verbose_name="last modified by",
    )

    class Meta:
        abstract = True

    def set_audit_user(self, user):
        if user is None or not getattr(user, "is_authenticated", False):
            return
        if self._state.adding and self.created_by_id is None:
            self.created_by = user
        self.updated_by = user
