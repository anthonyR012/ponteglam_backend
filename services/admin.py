# Third-party Libraries
from django.contrib import admin

# Local Modules
from services import models


# Register your models here.
admin.site.register(models.Service)
admin.site.register(models.ServiceFile)
admin.site.register(models.ServiceCategory)
admin.site.register(models.Appointment)
admin.site.register(models.AppointmentService)
admin.site.register(models.TimeConfigurationService)
admin.site.register(models.WorkerService)
admin.site.register(models.ServiceAmenity)
admin.site.register(models.CancellationRule)
