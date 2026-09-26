# Third-party Libraries
from rest_framework import serializers

# Local Modules
from chats import models


class ChatRoomSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.ChatRoom
        fields = (
            'last_message', 'last_sent_user', 'created_by_user_id'
        )
        extra_kwargs = {
            'created_by_user_id': {'required': True},
        }


class ChatRoomUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.ChatRoomUser
        fields = (
            'user', 'room', 'created_by_user_id'
        )
        extra_kwargs = {
            'created_by_user_id': {'required': True},
        }
