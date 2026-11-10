from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.accounts import roles


class Command(BaseCommand):
    help = "Create or refresh the `inventory_manager` and `admin` groups with their permissions (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        manager_perms = self._manager_permissions()
        admin_perms = self._admin_permissions()

        manager, _ = Group.objects.get_or_create(name=roles.ROLE_INVENTORY_MANAGER)
        manager.permissions.set(manager_perms)

        admin, _ = Group.objects.get_or_create(name=roles.ROLE_ADMIN)
        admin.permissions.set(admin_perms)

        self.stdout.write(self.style.SUCCESS(
            f"{roles.ROLE_INVENTORY_MANAGER}: {len(manager_perms)} permissions | "
            f"{roles.ROLE_ADMIN}: {len(admin_perms)} permissions"
        ))

    def _manager_permissions(self):
        found = []
        for app_label, models_ in roles.MANAGER_PERMISSIONS.items():
            for model, actions in models_.items():
                codenames = [f"{action}_{model}" for action in actions]
                perms = list(Permission.objects.filter(content_type__app_label=app_label, codename__in=codenames))
                if len(perms) != len(codenames):
                    raise CommandError(f"Missing permissions for {app_label}.{model}. Run `migrate` first.")
                found += perms
        return found

    def _admin_permissions(self):
        query = Q(content_type__app_label__in=roles.ADMIN_APP_LABELS)
        for app_label, codename in roles.ADMIN_EXTRA_PERMISSIONS:
            query |= Q(content_type__app_label=app_label, codename=codename)
        perms = list(Permission.objects.filter(query))
        if not perms:
            raise CommandError("No permissions found. Run `migrate` first.")
        return perms
