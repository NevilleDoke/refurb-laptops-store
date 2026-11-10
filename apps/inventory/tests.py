from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.inquiries.models import Inquiry

from .models import Category, Laptop


def make_laptop(category, sku, **kw):
    defaults = dict(
        sku=sku, title=f"Laptop {sku}", slug=f"laptop-{sku.lower()}", category=category, brand="Dell",
        model_name="Latitude", processor="Intel Core i5", ram_gb=8, storage_gb=256, price=15000,
    )
    defaults.update(kw)
    return Laptop.objects.create(**defaults)


class CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Business", slug="business")
        cls.hidden_cat = Category.objects.create(name="Hidden", slug="hidden", is_active=False)
        cls.a = make_laptop(cls.cat, "A1", ram_gb=8, price=15000)
        cls.b = make_laptop(cls.cat, "B1", ram_gb=16, price=30000, brand="HP", title="HP EliteBook")
        cls.sold = make_laptop(cls.cat, "S1", status=Laptop.Status.SOLD)
        cls.archived = make_laptop(cls.cat, "R1", status=Laptop.Status.ARCHIVED)
        cls.in_hidden_cat = make_laptop(cls.hidden_cat, "H1")

    def titles(self, **params):
        resp = self.client.get(reverse("inventory:laptop_list"), params)
        self.assertEqual(resp.status_code, 200)
        return {l.sku for l in resp.context["laptops"]}

    def test_only_public_laptops_listed(self):
        self.assertEqual(self.titles(), {"A1", "B1"})

    def test_filters(self):
        self.assertEqual(self.titles(ram=16), {"B1"})
        self.assertEqual(self.titles(brand="HP"), {"B1"})
        self.assertEqual(self.titles(max_price=20000), {"A1"})
        self.assertEqual(self.titles(q="elitebook"), {"B1"})
        self.assertEqual(self.titles(category="business"), {"A1", "B1"})

    def test_sorting(self):
        resp = self.client.get(reverse("inventory:laptop_list"), {"sort": "price_desc"})
        self.assertEqual([l.sku for l in resp.context["laptops"]], ["B1", "A1"])

    def test_invalid_filter_does_not_crash(self):
        self.assertEqual(self.titles(ram="abc", min_price="x"), {"A1", "B1"})

    def test_card_renders_responsive_grid(self):
        resp = self.client.get(reverse("inventory:laptop_list"))
        self.assertContains(resp, "grid-cols-1")
        self.assertContains(resp, "sm:grid-cols-2")
        self.assertContains(resp, "₹15,000")

    def test_sold_detail_is_404(self):
        self.assertEqual(self.client.get(self.sold.get_absolute_url()).status_code, 404)

    def test_list_query_count_is_constant(self):
        for i in range(10):
            make_laptop(self.cat, f"N{i}")
        with self.assertNumQueries(6):  # count, page, images prefetch, categories, filter brands, brand browse
            self.client.get(reverse("inventory:laptop_list"))


class InquiryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Business", slug="business")
        cls.laptop = make_laptop(cls.cat, "A1")
        cls.url = reverse("inquiries:submit", args=[cls.laptop.slug])
        cls.valid = {"name": "Asha", "email": "asha@example.com", "phone": "+91 9820012345", "preferred_contact": "whatsapp", "message": "Is it still available?", "website": ""}

    def setUp(self):
        cache.clear()

    def test_valid_inquiry_is_stored_with_snapshot(self):
        resp = self.client.post(self.url, self.valid)
        self.assertRedirects(resp, self.laptop.get_absolute_url())
        inquiry = Inquiry.objects.get()
        self.assertEqual((inquiry.laptop, inquiry.laptop_title, inquiry.laptop_sku), (self.laptop, self.laptop.title, "A1"))
        self.assertEqual(inquiry.status, Inquiry.Status.NEW)

    def test_inquiry_survives_listing_deletion(self):
        self.client.post(self.url, self.valid)
        self.laptop.delete()
        inquiry = Inquiry.objects.get()
        self.assertIsNone(inquiry.laptop)
        self.assertEqual(inquiry.laptop_sku, "A1")

    def test_honeypot_stores_nothing(self):
        self.client.post(self.url, {**self.valid, "website": "http://spam.example"})
        self.assertEqual(Inquiry.objects.count(), 0)

    def test_invalid_phone_rejected(self):
        resp = self.client.post(self.url, {**self.valid, "phone": "abc"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Inquiry.objects.count(), 0)

    def test_rate_limit(self):
        for _ in range(7):
            self.client.post(self.url, self.valid)
        self.assertEqual(Inquiry.objects.count(), 5)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
