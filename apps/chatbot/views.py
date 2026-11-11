import json

from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.shortcuts import render

from .models import ChatSession, ChatMessage
from .selectors import match_laptops, build_reply
from .admin_helpers import handle_admin_command


def chatbot_demo(request):
    """Optional standalone demo page: /chatbot/"""
    return render(request, "chatbot/demo.html")


@require_POST
@csrf_protect
def chat_message(request):
    """AJAX endpoint: receive a shopper message, reply with matched laptops."""
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = (data.get("message") or "").strip()
    session_key = data.get("session_key") or request.session.session_key
    if not session_key:
        request.session.cycle_key()
        session_key = request.session.session_key

    if not message:
        return JsonResponse({"error": "Message is required"}, status=400)

    session, _ = ChatSession.objects.get_or_create(
        session_key=session_key,
        defaults={
            "is_active": True,
            "user": request.user if request.user.is_authenticated else None,
        },
    )

    ChatMessage.objects.create(
        session=session, role=ChatMessage.Role.USER, content=message
    )

    matches = match_laptops(message)
    reply = build_reply(message, matches)

    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.BOT,
        content=reply,
        matched_laptops=[
            {
                "id": m.id,
                "slug": m.slug,
                "title": m.title,
                "brand": m.brand,
                "price": str(m.price),
                "url": m.get_absolute_url(),
            }
            for m in matches
        ],
    )

    return JsonResponse(
        {
            "session_key": session.session_key,
            "reply": reply,
            "matches": [
                {
                    "id": m.id,
                    "slug": m.slug,
                    "title": m.title,
                    "brand": m.brand,
                    "price": str(m.price),
                    "url": m.get_absolute_url(),
                    "image": m.cover_image.image.url if m.cover_image else None,
                    "inquiry_url": m.get_absolute_url() + "#inquiry",
                }
                for m in matches
            ],
        }
    )


@user_passes_test(lambda u: u.is_staff)
@require_POST
@csrf_protect
def admin_chat_message(request):
    """Staff-only AJAX endpoint for the admin assistant."""
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = (data.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "Message is required"}, status=400)

    result = handle_admin_command(message, request.user)
    return JsonResponse(result)

