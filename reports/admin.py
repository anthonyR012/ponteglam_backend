# Third-party Libraries
from django.contrib import admin

# Local Modules
from reports import models

# Register your models here.
admin.site.register(models.UserReport)
admin.site.register(models.PostReport)
admin.site.register(models.CommentReport)
admin.site.register(models.CompanyReport)
