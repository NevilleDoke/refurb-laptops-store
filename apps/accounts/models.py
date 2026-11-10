from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user from day one (painful to retrofit later).

    Roles are Django groups (see roles.py); `is_staff` lets a person into the admin.
    """

    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.get_full_name() or self.get_username()
