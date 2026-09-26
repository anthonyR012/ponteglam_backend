from django.contrib import admin

from ratings import models


admin.site.register(models.HeadquarterRating)
admin.site.register(models.HeadquarterServiceRating)
