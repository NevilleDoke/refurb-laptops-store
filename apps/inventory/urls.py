from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.LaptopListView.as_view(), name="laptop_list"),
    path("deals/", views.DealsView.as_view(), name="deals"),
    path("brands/<slug:slug>/", views.BrandLaptopsView.as_view(), name="brand_laptops"),
    path("newsletter/signup/", views.newsletter_signup, name="newsletter_signup"),
    path("laptops/<slug:slug>/", views.LaptopDetailView.as_view(), name="laptop_detail"),
]
