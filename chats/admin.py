# Third-party Libraries
from django.contrib import admin

# Local Modules
from chats import models


# Register your models here.
admin.site.register(models.ChatUserChannel)
admin.site.register(models.ChatRoom)
admin.site.register(models.Message)
admin.site.register(models.ChatRoomUser)
