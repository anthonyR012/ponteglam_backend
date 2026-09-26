"""
File for the API views of the chats application
"""
# Third-party Libraries
from django.http import HttpRequest
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response

# Local Modules
from chats import models


class ListChatRoomMessagesView(viewsets.ModelViewSet):
    """
    ViewSet for the chat room messages
    """

    authentication_classes = [TokenAuthentication]

    def list(self, request: HttpRequest, *args, **kwargs):
        """
        List all the room messages
        """

        user_id_origin = request.user.pk
        user_id_destination = request.query_params.get('user_id_destination')
        chat_room_id = request.query_params.get('chat_room_id')

        if not chat_room_id:
            chat_room = models.ChatRoom.objects.filter(
                chatroomuser__user__pk=user_id_origin
            ).filter(
                chatroomuser__user__pk=user_id_destination
            ).first()
            chat_room_id = chat_room.id if chat_room else None

        messages = models.Message.objects.filter(
            chat_room__id=chat_room_id
        ).values(
            'id', 'chat_room', 'user', 'content', 'created_at'
        ) if chat_room_id else []

        return Response(messages, status=status.HTTP_200_OK)
