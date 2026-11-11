from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = f"{settings.STORE_NAME} - Back office"
admin.site.site_title = settings.STORE_NAME
admin.site.index_title = "Inventory & inquiries"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("staff/", include("apps.dashboard.urls")),
    path("inquiries/", include("apps.inquiries.urls")),
    path("chatbot/", include("apps.chatbot.urls")),
    path("", include("apps.inventory.urls")),
]

handler403 = "apps.dashboard.views.permission_denied"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
