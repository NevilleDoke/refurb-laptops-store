from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import StaffLoginForm

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="dashboard/login.html",
            form_class=StaffLoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/add/", views.CategoryCreateView.as_view(), name="category_add"),
    path(
        "categories/<slug:slug>/edit/",
        views.CategoryUpdateView.as_view(),
        name="category_edit",
    ),
    path(
        "categories/<slug:slug>/delete/",
        views.CategoryDeleteView.as_view(),
        name="category_delete",
    ),
    path("laptops/", views.LaptopListView.as_view(), name="laptop_list"),
    path("laptops/add/", views.LaptopCreateView.as_view(), name="laptop_add"),
    path("laptops/<slug:slug>/", views.LaptopDetailView.as_view(), name="laptop_detail"),
    path(
        "laptops/<slug:slug>/edit/",
        views.LaptopUpdateView.as_view(),
        name="laptop_edit",
    ),
    path(
        "laptops/<slug:slug>/delete/",
        views.LaptopDeleteView.as_view(),
        name="laptop_delete",
    ),
    path("inquiries/", views.InquiryListView.as_view(), name="inquiry_list"),
    path("inquiries/<int:pk>/", views.InquiryDetailView.as_view(), name="inquiry_detail"),
]
