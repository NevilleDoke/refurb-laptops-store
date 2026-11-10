from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView

from apps.inquiries.forms import InquiryForm

from . import selectors
from .forms import LaptopFilterForm
from .models import Brand, Laptop, NewsletterSubscriber


class LaptopListView(ListView):
    template_name = "inventory/laptop_list.html"
    context_object_name = "laptops"
    paginate_by = 12

    def get_queryset(self):
        self.filter_form = LaptopFilterForm(self.request.GET or None)
        params = self.filter_form.cleaned_data if self.filter_form.is_valid() else {}
        return selectors.catalog(params)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = self.request.GET.copy()
        query.pop("page", None)
        ctx["filter_form"] = self.filter_form
        ctx["querystring"] = query.urlencode()  # keeps filters when paginating
        ctx["filters_active"] = any(v for k, v in query.items() if k != "sort")
        ctx["brands"] = Brand.objects.filter(is_active=True).order_by("name")
        return ctx


class LaptopDetailView(DetailView):
    template_name = "inventory/laptop_detail.html"
    context_object_name = "laptop"

    def get_queryset(self):
        return Laptop.objects.public().select_related("category").prefetch_related("images")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("inquiry_form", InquiryForm())
        return ctx


class DealsView(ListView):
    """Low-price deals: laptops sorted cheapest first (electronicsbazaar
    /low-price-deal equivalent)."""

    template_name = "inventory/deals.html"
    context_object_name = "laptops"
    paginate_by = 12

    def get_queryset(self):
        return (
            Laptop.objects.public()
            .select_related("category")
            .prefetch_related("images")
            .order_by("price", "-created_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Low Price Deals"
        return ctx


class BrandLaptopsView(ListView):
    """Brand browsing page: all laptops of one brand (electronicsbazaar
    "BROWSE OUR BRAND" equivalent)."""

    template_name = "inventory/brand_laptops.html"
    context_object_name = "laptops"
    paginate_by = 12

    def get_queryset(self):
        self.brand = get_object_or_404(Brand, slug=self.kwargs["slug"], is_active=True)
        return (
            Laptop.objects.public()
            .filter(brand__iexact=self.brand.name)
            .select_related("category")
            .prefetch_related("images")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["brand"] = self.brand
        ctx["page_title"] = f"Refurbished {self.brand.name} Laptops"
        return ctx


def newsletter_signup(request):
    """Footer newsletter sign-up."""
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        if email:
            obj, created = NewsletterSubscriber.objects.get_or_create(
                email=email, defaults={"is_active": True}
            )
            if not created and not obj.is_active:
                obj.is_active = True
                obj.save()
                messages.success(request, "You're subscribed again!")
            elif created:
                messages.success(request, "Thanks for subscribing!")
            else:
                messages.info(request, "You're already subscribed.")
        else:
            messages.error(request, "Please enter a valid email.")
    return redirect(request.META.get("HTTP_REFERER", "/") or "/")
