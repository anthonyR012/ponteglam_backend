# Third-party Libraries
from django.db import models

# Local Modules
from core import models as core_models


# Create your models here.
class ChatUserChannel(core_models.MixinAudit):

    channel_name = models.CharField(max_length=256)
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='chat_user_channel'
    )

    def __str__(self):
        return self.channel_name


class ChatRoom(core_models.MixinAudit):

    last_message = models.CharField(max_length=256, null=True, blank=True)
    last_sent_user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        null=True, blank=True
    )


class ChatRoomUser(core_models.MixinAudit):

    chat_room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE,
        related_name='chat_room_user'
    )
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='chat_room_user'
    )


class Message(core_models.MixinAudit):

    chat_room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE,
        related_name='message'
    )
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='message'
    )
    content = models.TextField()

    def __str__(self):
        return self.content
