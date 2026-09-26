# Third-party Libraries
from django.contrib import admin

# Local Modules
from blogs import models

# Register your models here.
admin.site.register(models.Post)
admin.site.register(models.PostComment)
admin.site.register(models.PostInteraction)
admin.site.register(models.InteractionToPostComment)
