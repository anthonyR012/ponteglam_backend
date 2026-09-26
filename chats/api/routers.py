"""
File for the API routes of the chats application
"""

# Third-party Libraries
from rest_framework import routers

# Local Modules
from chats.api import views


router = routers.SimpleRouter()

router.register(
    r'list-chat-room-messages', views.ListChatRoomMessagesView,
    basename='list-chat-room-messages'
)
