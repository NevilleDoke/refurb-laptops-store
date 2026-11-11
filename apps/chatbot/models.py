from django.conf import settings
from django.db import models

from apps.core.models import AuditModel


class ChatSession(AuditModel):
    """A chatbot conversation session, keyed by the Django session key so the
    conversation survives across page loads for the same visitor."""
    session_key = models.CharField(max_length=40, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="chatbot_sessions",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["session_key", "-created_at"])]

    def __str__(self):
        return f"Chat {self.session_key[:8]}"


class ChatMessage(AuditModel):
    """One message in a chatbot session."""
    class Role(models.TextChoices):
        USER = "user", "User"
        BOT = "bot", "Bot"

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    # Snapshot of laptops the bot matched for this turn (ids, slugs, titles).
    matched_laptops = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"
