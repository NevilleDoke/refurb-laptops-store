"""Access mixins for the staff dashboard.

The back office is gated behind Django's `is_staff` flag, and each action
requires the matching model permission (add / change / delete / view).  That
mirrors `apps.accounts.roles`, so `inventory_manager` users can add/change/view
but never delete, while `admin` users (and superusers) can do everything.
"""

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied


class StaffRequiredMixin(AccessMixin):
    """Signed-in staff members only."""

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (user.is_authenticated and user.is_staff):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class PermRequiredMixin(StaffRequiredMixin):
    """Require one or more model permissions, e.g. ``inventory.add_category``."""

    required_perms = ()

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if self.required_perms and not all(user.has_perm(p) for p in self.required_perms):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
