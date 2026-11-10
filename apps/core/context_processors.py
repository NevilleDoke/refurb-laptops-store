from django.conf import settings


def store(request):
    return {"STORE_NAME": settings.STORE_NAME, "CURRENCY": settings.CURRENCY_SYMBOL}
