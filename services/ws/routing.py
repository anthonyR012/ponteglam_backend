from django.urls import re_path
from services.ws import consumers


websocket_urlpatterns = [
    re_path(r'ws/schedule/', consumers.ScheduleConsumer.as_asgi()),
]
