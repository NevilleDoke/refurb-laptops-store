"""Read-side query logic, kept out of views so a future DRF viewset can reuse it as-is."""
from django.db.models import Q

from .models import Laptop

SORTS = {
    "featured": ("-is_featured", "-created_at"),
    "newest": ("-created_at",),
    "price_asc": ("price", "id"),
    "price_desc": ("-price", "id"),
}


def catalog(params):
    """Public catalog queryset filtered by already-validated `params` (a dict)."""
    qs = Laptop.objects.public().select_related("category").prefetch_related("images")

    q = (params.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(model_name__icontains=q) | Q(processor__icontains=q))
    if params.get("category"):
        qs = qs.filter(category=params["category"])
    if params.get("brand"):
        qs = qs.filter(brand=params["brand"])
    if params.get("ram"):
        qs = qs.filter(ram_gb__gte=params["ram"])
    if params.get("storage_type"):
        qs = qs.filter(storage_type=params["storage_type"])
    if params.get("condition"):
        qs = qs.filter(condition=params["condition"])
    if params.get("min_price") is not None:
        qs = qs.filter(price__gte=params["min_price"])
    if params.get("max_price") is not None:
        qs = qs.filter(price__lte=params["max_price"])

    return qs.order_by(*SORTS.get(params.get("sort") or "featured", SORTS["featured"]))
