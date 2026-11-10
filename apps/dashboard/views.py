"""Staff dashboard views: categories, inventory (laptops + images), inquiries."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.inventory.models import Category, Laptop, LaptopImage
from apps.inquiries.models import Inquiry

from .forms import CategoryForm, InquiryHandlingForm, LaptopForm
from .mixins import PermRequiredMixin, StaffRequiredMixin


class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total_laptops"] = Laptop.objects.count()
        ctx["available_laptops"] = Laptop.objects.filter(status=Laptop.Status.AVAILABLE).count()
        ctx["total_categories"] = Category.objects.count()
        ctx["new_inquiries"] = Inquiry.objects.filter(status=Inquiry.Status.NEW).count()
        ctx["recent_inquiries"] = Inquiry.objects.select_related("assigned_to").order_by("-created_at")[:5]
        ctx["recent_laptops"] = Laptop.objects.select_related("category").order_by("-created_at")[:5]
        return ctx


# --------------------------------------------------------------------------- #
# Categories
# --------------------------------------------------------------------------- #
class CategoryListView(PermRequiredMixin, ListView):
    model = Category
    template_name = "dashboard/category_list.html"
    context_object_name = "categories"
    paginate_by = 25
    required_perms = ("inventory.view_category",)

    def get_queryset(self):
        return Category.objects.annotate_laptop_count().order_by("name") if False else (
            Category.objects.annotate(laptop_count=Count("laptops")).order_by("name")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["can_add"] = user.has_perm("inventory.add_category")
        ctx["can_delete"] = user.has_perm("inventory.delete_category")
        return ctx


class CategoryCreateView(PermRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "dashboard/category_form.html"
    required_perms = ("inventory.add_category",)

    def form_valid(self, form):
        form.instance.set_audit_user(self.request.user)
        messages.success(self.request, "Category created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("dashboard:category_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Add category"
        return ctx


class CategoryUpdateView(PermRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "dashboard/category_form.html"
    required_perms = ("inventory.change_category",)
    slug_url_kwarg = "slug"
    slug_field = "slug"

    def form_valid(self, form):
        laptop = form.save(commit=False)
        laptop.set_audit_user(self.request.user)
        laptop.save()
        messages.success(self.request, "Category saved.")
        return redirect("dashboard:category_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f'Edit "{self.object.name}"'
        ctx["object"] = self.object
        return ctx


class CategoryDeleteView(PermRequiredMixin, DeleteView):
    model = Category
    template_name = "dashboard/category_confirm_delete.html"
    required_perms = ("inventory.delete_category",)
    slug_url_kwarg = "slug"
    slug_field = "slug"
    success_url = reverse_lazy("dashboard:category_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Category deleted.")
        return super().delete(request, *args, **kwargs)


# --------------------------------------------------------------------------- #
# Inventory (laptops)
# --------------------------------------------------------------------------- #
class LaptopListView(PermRequiredMixin, ListView):
    model = Laptop
    template_name = "dashboard/laptop_list.html"
    context_object_name = "laptops"
    paginate_by = 25
    required_perms = ("inventory.view_laptop",)

    def get_queryset(self):
        qs = Laptop.objects.select_related("category").prefetch_related("images").order_by("-created_at")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(sku__icontains=q) | Q(brand__icontains=q))
        status = self.request.GET.get("status")
        if status in dict(Laptop.Status.choices):
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["status_choices"] = Laptop.Status.choices
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["q"] = self.request.GET.get("q", "")
        ctx["can_add"] = user.has_perm("inventory.add_laptop")
        ctx["can_delete"] = user.has_perm("inventory.delete_laptop")
        return ctx


class LaptopCreateView(PermRequiredMixin, CreateView):
    model = Laptop
    form_class = LaptopForm
    template_name = "dashboard/laptop_form.html"
    required_perms = ("inventory.add_laptop",)

    def form_valid(self, form):
        laptop = form.save(commit=False)
        laptop.set_audit_user(self.request.user)
        laptop.save()
        image = self.request.FILES.get("cover_image")
        if image:
            img = LaptopImage(laptop=laptop, image=image, is_primary=True, alt_text=laptop.title)
            img.set_audit_user(self.request.user)
            img.save()
        messages.success(self.request, "Laptop added.")
        return redirect("dashboard:laptop_detail", slug=laptop.slug)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Add laptop"
        return ctx


class LaptopDetailView(PermRequiredMixin, DetailView):
    model = Laptop
    template_name = "dashboard/laptop_detail.html"
    context_object_name = "laptop"
    required_perms = ("inventory.view_laptop",)
    slug_url_kwarg = "slug"
    slug_field = "slug"

    def get_queryset(self):
        return Laptop.objects.select_related("category").prefetch_related("images")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["inquiries"] = self.object.inquiries.order_by("-created_at")[:10]
        ctx["can_edit"] = user.has_perm("inventory.change_laptop")
        ctx["can_delete"] = user.has_perm("inventory.delete_laptop")
        return ctx


class LaptopUpdateView(PermRequiredMixin, UpdateView):
    model = Laptop
    form_class = LaptopForm
    template_name = "dashboard/laptop_form.html"
    required_perms = ("inventory.change_laptop",)
    slug_url_kwarg = "slug"
    slug_field = "slug"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        laptop = form.save(commit=False)
        laptop.set_audit_user(self.request.user)
        laptop.save()

        for key in self.request.POST:
            if key.startswith("del_image_"):
                image_id = key[len("del_image_"):]
                LaptopImage.objects.filter(id=image_id, laptop=laptop).delete()

        image = self.request.FILES.get("new_image")
        if image:
            img = LaptopImage(laptop=laptop, image=image, alt_text=laptop.title)
            img.set_audit_user(self.request.user)
            img.save()

        messages.success(self.request, "Laptop updated.")
        return redirect("dashboard:laptop_detail", slug=laptop.slug)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f'Edit "{self.object.title}"'
        ctx["object"] = self.object
        ctx["images"] = self.object.images.all()
        return ctx


class LaptopDeleteView(PermRequiredMixin, DeleteView):
    model = Laptop
    template_name = "dashboard/laptop_confirm_delete.html"
    required_perms = ("inventory.delete_laptop",)
    slug_url_kwarg = "slug"
    slug_field = "slug"
    success_url = reverse_lazy("dashboard:laptop_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Laptop deleted.")
        return super().delete(request, *args, **kwargs)


# --------------------------------------------------------------------------- #
# Inquiries
# --------------------------------------------------------------------------- #
class InquiryListView(PermRequiredMixin, ListView):
    model = Inquiry
    template_name = "dashboard/inquiry_list.html"
    context_object_name = "inquiries"
    paginate_by = 25
    required_perms = ("inquiries.view_inquiry",)

    def get_queryset(self):
        qs = Inquiry.objects.select_related("laptop", "assigned_to").order_by("-created_at")
        status = self.request.GET.get("status")
        if status in dict(Inquiry.Status.choices):
            qs = qs.filter(status=status)
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q) | Q(laptop_title__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Inquiry.Status.choices
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class InquiryDetailView(StaffRequiredMixin, DetailView):
    model = Inquiry
    template_name = "dashboard/inquiry_detail.html"
    context_object_name = "inquiry"
    pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (user.is_authenticated and user.is_staff):
            return self.handle_no_permission()
        if request.method == "POST" and not user.has_perm("inquiries.change_inquiry"):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = InquiryHandlingForm(request.POST, instance=self.object)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.set_audit_user(request.user)
            inquiry.save()
            messages.success(request, "Inquiry updated.")
            return redirect("dashboard:inquiry_detail", pk=inquiry.pk)
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("form", InquiryHandlingForm(instance=self.object))
        ctx["can_change"] = self.request.user.has_perm("inquiries.change_inquiry")
        return ctx


def permission_denied(request, exception=None):
    return render(request, "dashboard/403.html", status=403)
