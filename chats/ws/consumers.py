import json
from urllib.parse import parse_qs

from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync

from chats import models


class ChatConsumer(WebsocketConsumer):

    def connect(self):

        url_params = parse_qs(self.scope['query_string'].decode('utf-8'))
        dict_params = {k: v[0] for k, v in url_params.items()}

        self.user = self.scope['user']
        self.user_id_origin = self.user.pk
        self.chat_room_id = dict_params.get('chat_room_id')
        self.user_id_destination = dict_params.get('user_id_destination')

        if self.user.is_anonymous:
            self.close()

        self.set_chat_room()
        self.create_chat_user_channel_origin()
        self.set_chat_users_channel_destination()

        async_to_sync(self.channel_layer.group_add)(
            f'chatroom{self.chat_room_id}',
            self.channel_name
        )

        if self.chat_user_channel_destination:
            async_to_sync(self.channel_layer.group_add)(
                f'chatroom{self.chat_room_id}',
                self.chat_user_channel_destination.channel_name
            )

        async_to_sync(self.channel_layer.group_send)(
            f'chatroom{self.chat_room_id}',
            {
                'type': 'chat.message',
                'text': f'User {self.user} has connected to the group \
                          chatroom{self.chat_room_id}'
            }
        )

        self.accept()

    def disconnect(self, close_code):

        async_to_sync(self.channel_layer.group_discard)(
            f'chatroom{self.chat_room_id}',
            self.channel_name
        )

        async_to_sync(self.channel_layer.group_send)(
            f'chatroom{self.chat_room_id}',
            {
                'type': 'chat.message',
                'text': f'User {self.user_id_origin} has disconnected from \
                          the group chatroom{self.chat_room_id}'

            }
        )

        self.delete_chat_user_channel_origin()
        self.close()

    def receive(self, text_data):

        message_response = self.save_message(text_data)

        async_to_sync(self.channel_layer.group_send)(
            f'chatroom{self.chat_room_id}',
            {
                'type': 'chat.message',
                'text': message_response
            }
        )

    def chat_message(self, event):
        self.send(text_data=json.dumps(event))

    def create_chat_user_channel_origin(self):

        models.ChatUserChannel.objects.create(
            user_id=self.user_id_origin,
            channel_name=self.channel_name,
            created_by_user_id=self.user_id_origin
        )

    def set_chat_users_channel_destination(self):
        self.chat_user_channel_destination = \
            models.ChatUserChannel.objects.filter(
                user=self.user_id_destination
            ).last()

    def delete_chat_user_channel_origin(self):
        models.ChatUserChannel.objects.filter(
            user=self.user_id_origin
        ).delete()

    def set_chat_room(self):

        self.chat_room = models.ChatRoom.objects.filter(
            pk=self.chat_room_id
        ).first()

        if not self.chat_room:
            self.create_chat_room()

    def create_chat_room(self):
        chat_room = models.ChatRoom.objects.create(
            created_by_user_id=self.user_id_origin
        )
        self.chat_room_id = chat_room.id
        models.ChatRoomUser.objects.create(
            chat_room_id=self.chat_room_id,
            user_id=self.user_id_origin,
            created_by_user_id=self.user_id_origin
        )
        models.ChatRoomUser.objects.create(
            chat_room_id=self.chat_room_id,
            user_id=self.user_id_destination,
            created_by_user_id=self.user_id_origin
        )

    def save_message(self, content):
        self.chat_room.last_message = content
        self.chat_room.last_sent_user = self.user

        message = models.Message.objects.create(
            chat_room_id=self.chat_room_id,
            user_id=self.user_id_origin,
            content=content,
            created_by_user_id=self.user_id_origin
        )

        response = {
            'id': message.id,
            'chat_room': self.chat_room_id,
            'user': self.user_id_origin,
            'content': content,
            # 'created_at': message.created_at
        }

        return response
