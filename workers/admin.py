# Third-party Libraries
from django.contrib import admin

# Local Modules
from workers import models


# Register your models here.
admin.site.register(models.Worker)
admin.site.register(models.WorkerLevel)
