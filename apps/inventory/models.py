from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.urls import reverse

from apps.core.models import AuditModel


class Category(AuditModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, help_text="Inactive categories (and their laptops) are hidden from the catalog.")

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class LaptopQuerySet(models.QuerySet):
    def public(self):
        """What customers may see: listed, not sold/archived, in an active category."""
        return self.filter(status__in=Laptop.PUBLIC_STATUSES, category__is_active=True)


class Laptop(AuditModel):
    class Condition(models.TextChoices):
        LIKE_NEW = "like_new", "Like new (A+)"
        EXCELLENT = "excellent", "Excellent (A)"
        GOOD = "good", "Good (B)"
        FAIR = "fair", "Fair (C)"

    class StorageType(models.TextChoices):
        SSD = "ssd", "SSD"
        NVME = "nvme", "NVMe SSD"
        HDD = "hdd", "HDD"
        DUAL = "ssd_hdd", "SSD + HDD"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        RESERVED = "reserved", "Reserved"
        SOLD = "sold", "Sold"
        ARCHIVED = "archived", "Archived (hidden)"

    PUBLIC_STATUSES = (Status.AVAILABLE, Status.RESERVED)

    # Identity
    sku = models.CharField(max_length=40, unique=True)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="laptops")
    brand = models.CharField(max_length=60)
    model_name = models.CharField(max_length=120)

    # Specifications
    processor = models.CharField(max_length=120)
    ram_gb = models.PositiveSmallIntegerField("RAM (GB)")
    storage_gb = models.PositiveIntegerField("storage (GB)")
    storage_type = models.CharField(max_length=10, choices=StorageType.choices, default=StorageType.SSD)
    screen_size_in = models.DecimalField("screen size (in)", max_digits=3, decimal_places=1, null=True, blank=True)
    gpu = models.CharField("graphics", max_length=120, blank=True)
    operating_system = models.CharField(max_length=60, blank=True)
    battery_health_pct = models.PositiveSmallIntegerField("battery health (%)", null=True, blank=True)

    # Condition & pricing
    condition = models.CharField(max_length=12, choices=Condition.choices, default=Condition.GOOD)
    warranty_months = models.PositiveSmallIntegerField(default=3)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(
        "MRP / original price", max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Listing
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.AVAILABLE)
    is_featured = models.BooleanField(default=False)

    objects = LaptopQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # Catalog browsing: filter by status, then price / newest.
            models.Index(fields=["status", "price"], name="laptop_status_price_idx"),
            models.Index(fields=["status", "-created_at"], name="laptop_status_new_idx"),
            models.Index(fields=["category", "status"], name="laptop_cat_status_idx"),
            models.Index(fields=["brand", "status"], name="laptop_brand_status_idx"),
            # Spec filters.
            models.Index(fields=["ram_gb", "storage_gb"], name="laptop_ram_storage_idx"),
            models.Index(fields=["condition"], name="laptop_condition_idx"),
            # Fast free-text search (ILIKE '%term%') via pg_trgm.
            GinIndex(fields=["title"], opclasses=["gin_trgm_ops"], name="laptop_title_trgm_idx"),
            GinIndex(fields=["model_name"], opclasses=["gin_trgm_ops"], name="laptop_model_trgm_idx"),
            GinIndex(fields=["processor"], opclasses=["gin_trgm_ops"], name="laptop_cpu_trgm_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="laptop_price_gte_0"),
            models.CheckConstraint(condition=models.Q(ram_gb__gt=0), name="laptop_ram_gt_0"),
            models.CheckConstraint(
                condition=models.Q(battery_health_pct__isnull=True) | models.Q(battery_health_pct__lte=100),
                name="laptop_battery_pct_lte_100",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.sku})"

    def get_absolute_url(self):
        return reverse("inventory:laptop_detail", kwargs={"slug": self.slug})

    @property
    def storage_label(self):
        size = f"{self.storage_gb // 1024} TB" if self.storage_gb >= 1024 and self.storage_gb % 1024 == 0 else f"{self.storage_gb} GB"
        return f"{size} {self.get_storage_type_display()}"

    @property
    def discount_pct(self):
        if self.original_price and self.original_price > self.price:
            return int(round((self.original_price - self.price) / self.original_price * 100))
        return None

    @property
    def cover_image(self):
        """First image by (primary, sort_order). Use prefetch_related('images') in lists."""
        images = list(self.images.all())
        return images[0] if images else None


class Brand(AuditModel):
    """Manufacturer brand with logo, for the brand-browsing section (like
    electronicsbazaar's "BROWSE OUR BRAND")."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    logo = models.ImageField(upload_to="brands/%Y/%m/", blank=True)
    url = models.URLField(blank=True, help_text="External brand store link (optional)")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "brands"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("inventory:brand_laptops", kwargs={"slug": self.slug})


class NewsletterSubscriber(AuditModel):
    """Site-wide newsletter subscribers (footer sign-up)."""

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "newsletter subscribers"

    def __str__(self):
        return self.email


class LaptopImage(AuditModel):
    laptop = models.ForeignKey(Laptop, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="laptops/%Y/%m/")
    alt_text = models.CharField(max_length=160, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-is_primary", "sort_order", "id"]

    def __str__(self):
        return f"Image for {self.laptop_id}"
