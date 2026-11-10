from django.contrib import messages
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.inventory.models import Laptop

from .forms import InquiryForm

MAX_INQUIRIES_PER_HOUR = 5


def _client_ip(request):
    # If you deploy behind a proxy, configure it to set REMOTE_ADDR (or read X-Forwarded-For from a trusted hop).
    return request.META.get("REMOTE_ADDR") or None


def _rate_limited(ip):
    if not ip:
        return False
    key = f"inquiry-rate:{ip}"
    cache.add(key, 0, 3600)
    return cache.incr(key) > MAX_INQUIRIES_PER_HOUR


@require_POST
def submit_inquiry(request, slug):
    laptop = get_object_or_404(
        Laptop.objects.public().select_related("category").prefetch_related("images"), slug=slug
    )
    form = InquiryForm(request.POST)

    if not form.is_valid():
        return render(request, "inventory/laptop_detail.html", {"laptop": laptop, "inquiry_form": form}, status=400)

    thanks = "Thanks! We've received your inquiry and will contact you shortly."
    if form.cleaned_data["website"]:  # honeypot tripped: pretend success, store nothing
        messages.success(request, thanks)
        return redirect(laptop)

    ip = _client_ip(request)
    if _rate_limited(ip):
        messages.error(request, "Too many inquiries from your network. Please try again later.")
        return redirect(laptop)

    inquiry = form.save(commit=False)
    inquiry.laptop = laptop
    inquiry.laptop_title = laptop.title
    inquiry.laptop_sku = laptop.sku
    inquiry.ip_address = ip
    inquiry.save()

    messages.success(request, thanks)
    return redirect(laptop)
