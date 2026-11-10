"""RBAC + audit-trail tests: these encode the business rules from the spec."""
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.accounts.roles import ROLE_ADMIN, ROLE_INVENTORY_MANAGER
from apps.inventory.models import Category, Laptop

User = get_user_model()


def laptop_payload(category, **overrides):
    data = {
        "title": "ThinkPad T480", "slug": "thinkpad-t480", "sku": "TP-T480-001",
        "category": category.pk, "brand": "Lenovo", "model_name": "T480",
        "processor": "Intel Core i5-8350U", "ram_gb": 16, "storage_gb": 512, "storage_type": "nvme",
        "screen_size_in": "14.0", "gpu": "", "operating_system": "Windows 11 Pro",
        "battery_health_pct": 85, "condition": "excellent", "warranty_months": 6,
        "price": "24999.00", "original_price": "", "description": "", "status": "available",
        "images-TOTAL_FORMS": 0, "images-INITIAL_FORMS": 0, "images-MIN_NUM_FORMS": 0, "images-MAX_NUM_FORMS": 1000,
        "_save": "Save",
    }
    data.update(overrides)
    return data


class RoleTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", verbosity=0)
        cls.manager = User.objects.create_user("mgr", password="x", is_staff=True)
        cls.manager.groups.add(Group.objects.get(name=ROLE_INVENTORY_MANAGER))
        cls.admin_user = User.objects.create_user("boss", password="x", is_staff=True)
        cls.admin_user.groups.add(Group.objects.get(name=ROLE_ADMIN))
        cls.category = Category.objects.create(name="Business", slug="business")
        cls.laptop = Laptop.objects.create(
            sku="X1", title="Existing", slug="existing", category=cls.category, brand="Dell",
            model_name="Latitude", processor="i5", ram_gb=8, storage_gb=256, price=10000,
        )


class AuditTrailTests(RoleTestCase):
    def test_manager_create_records_created_and_updated_by(self):
        self.client.force_login(self.manager)
        resp = self.client.post(reverse("admin:inventory_laptop_add"), laptop_payload(self.category))
        self.assertEqual(resp.status_code, 302, getattr(resp, "context", None) and resp.context["adminform"].form.errors)
        laptop = Laptop.objects.get(sku="TP-T480-001")
        self.assertEqual(laptop.created_by, self.manager)
        self.assertEqual(laptop.updated_by, self.manager)
        self.assertIsNotNone(laptop.created_at)

    def test_later_edit_by_admin_changes_updated_by_only(self):
        self.client.force_login(self.manager)
        self.client.post(reverse("admin:inventory_laptop_add"), laptop_payload(self.category))
        laptop = Laptop.objects.get(sku="TP-T480-001")

        self.client.force_login(self.admin_user)
        resp = self.client.post(
            reverse("admin:inventory_laptop_change", args=[laptop.pk]),
            laptop_payload(self.category, title="ThinkPad T480 (updated)"),
        )
        self.assertEqual(resp.status_code, 302)
        laptop.refresh_from_db()
        self.assertEqual(laptop.created_by, self.manager)
        self.assertEqual(laptop.updated_by, self.admin_user)
        self.assertTrue(LogEntry.objects.filter(user=self.admin_user, object_id=str(laptop.pk)).exists())

    def test_category_create_is_audited(self):
        self.client.force_login(self.manager)
        resp = self.client.post(
            reverse("admin:inventory_category_add"),
            {"name": "Gaming", "slug": "gaming", "description": "", "is_active": "on", "_save": "Save"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Category.objects.get(slug="gaming").created_by, self.manager)

    def test_changelist_shows_audit_columns(self):
        self.laptop.set_audit_user(self.manager)
        self.laptop.save()
        self.client.force_login(self.admin_user)
        resp = self.client.get(reverse("admin:inventory_laptop_changelist"))
        self.assertContains(resp, "mgr ·")


class ManagerCannotDeleteTests(RoleTestCase):
    def setUp(self):
        self.client.force_login(self.manager)

    def test_laptop_delete_view_forbidden(self):
        url = reverse("admin:inventory_laptop_delete", args=[self.laptop.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {"post": "yes"}).status_code, 403)
        self.assertTrue(Laptop.objects.filter(pk=self.laptop.pk).exists())

    def test_category_delete_view_forbidden(self):
        empty = Category.objects.create(name="Empty", slug="empty")
        url = reverse("admin:inventory_category_delete", args=[empty.pk])
        self.assertEqual(self.client.post(url, {"post": "yes"}).status_code, 403)
        self.assertTrue(Category.objects.filter(pk=empty.pk).exists())

    def test_bulk_delete_action_unavailable(self):
        resp = self.client.post(
            reverse("admin:inventory_laptop_changelist"),
            {"action": "delete_selected", "_selected_action": [self.laptop.pk], "post": "yes"},
        )
        self.assertNotIn(b"delete_selected", resp.content)
        self.assertTrue(Laptop.objects.filter(pk=self.laptop.pk).exists())

    def test_manager_can_still_edit(self):
        resp = self.client.get(reverse("admin:inventory_laptop_change", args=[self.laptop.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "deletelink")

    def test_manager_has_no_delete_permissions_at_all(self):
        perms = {p for p in self.manager.get_all_permissions() if p.split(".")[1].startswith("delete_")}
        self.assertEqual(perms, set())

    def test_manager_cannot_see_audit_log_or_users(self):
        self.assertEqual(self.client.get(reverse("admin:admin_logentry_changelist")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:accounts_user_changelist")).status_code, 403)


class AdminRoleTests(RoleTestCase):
    def setUp(self):
        self.client.force_login(self.admin_user)

    def test_admin_can_delete_laptop(self):
        resp = self.client.post(reverse("admin:inventory_laptop_delete", args=[self.laptop.pk]), {"post": "yes"})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Laptop.objects.filter(pk=self.laptop.pk).exists())

    def test_admin_can_delete_empty_category(self):
        empty = Category.objects.create(name="Empty", slug="empty")
        self.client.post(reverse("admin:inventory_category_delete", args=[empty.pk]), {"post": "yes"})
        self.assertFalse(Category.objects.filter(pk=empty.pk).exists())

    def test_admin_can_review_audit_log(self):
        resp = self.client.get(reverse("admin:admin_logentry_changelist"))
        self.assertEqual(resp.status_code, 200)

    def test_audit_log_is_read_only(self):
        self.assertEqual(self.client.get(reverse("admin:admin_logentry_add")).status_code, 403)

    def test_admin_role_cannot_grant_superuser(self):
        resp = self.client.get(reverse("admin:accounts_user_change", args=[self.manager.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'name="is_superuser"')
