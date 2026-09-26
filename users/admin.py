# Third-party Libraries
from django.contrib import admin

# Local Modules
from users import models

# Register your models here.
admin.site.register(models.User)
admin.site.register(models.UserLevel)
admin.site.register(models.UserVerificationCode)
