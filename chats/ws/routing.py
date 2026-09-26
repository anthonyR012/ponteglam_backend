from django.urls import path
from chats.ws import consumers


websocket_urlpatterns = [
    path(r'chat/', consumers.ChatConsumer.as_asgi()),
]
