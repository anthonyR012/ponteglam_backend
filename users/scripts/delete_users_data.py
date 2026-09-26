from chats import models as chats_models
from users import models as users_models

from django.db import transaction

with transaction.atomic():

    try:
        # Delete all tokens
        from rest_framework.authtoken.models import Token
        Token.objects.all().delete()

        # Delete all chats
        chats_models.ChatRoomUser.objects.all().delete()
        chats_models.ChatUserChannel.objects.all().delete()
        chats_models.Message.objects.all().delete()
        chats_models.ChatRoom.objects.all().delete()

        # Delete all users
        users_models.UserVerificationCode.objects.all().delete()
        users_models.UserLevel.objects.all().delete()
        users_models.User.objects.all().delete()

        print('Data deleted successfully')

    except Exception as e:
        print(e)
        transaction.set_rollback(True)
