from django.urls import path

from . import views

app_name = "chatbot"

urlpatterns = [
    path("", views.chatbot_demo, name="demo"),
    path("message/", views.chat_message, name="message"),
    path("admin/message/", views.admin_chat_message, name="admin_message"),
]
