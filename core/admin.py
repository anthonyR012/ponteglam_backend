# Python Standard Library
from django.contrib import admin

# Local Modules
from core import models


# Register your models here.
admin.site.register(models.Category)
admin.site.register(models.Type)
admin.site.register(models.WeekDay)
admin.site.register(models.TimeConfiguration)
admin.site.register(models.WeekDayTimeConfiguration)
admin.site.register(models.HourWeekDayTimeConfiguration)
admin.site.register(models.Level)
admin.site.register(models.Amenity)
admin.site.register(models.GeoReferenceCity)
@admin.register(models.MobileAppLog)
class MobileAppLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'source', 'device_info', 'short_description')
    list_filter = ('source', 'created_at')
    search_fields = ('description', 'device_info', 'source')
    readonly_fields = ('created_at', 'updated_at', 'created_by_user_id', 'modified_by_user_id')
    ordering = ('-created_at',)

    def short_description(self, obj):
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
    short_description.short_description = 'Description'
