from django.contrib import admin

from headquarters import models


admin.site.register(models.Headquarter)
admin.site.register(models.HeadquarterService)
admin.site.register(models.HeadquarterWorker)
admin.site.register(models.HeadquaterWeekDayTimeConfiguration)
admin.site.register(models.HeadquarterFile)
admin.site.register(models.HeadquarterLike)
