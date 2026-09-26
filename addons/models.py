from django.db import models
from django.core.validators import MinValueValidator

from core.models import MixinAudit

class ServiceAddon(MixinAudit):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=300, null=True, blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    duration_minutes = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(10)]
    )
    created_by_user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='created_addons'
    )

    def __str__(self):
        return self.name

class ServiceAddonLink(MixinAudit):
    addon = models.ForeignKey(
        ServiceAddon,
        on_delete=models.CASCADE,
        related_name='addon_services'
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        related_name='service_addons'
    )

    class Meta:
        unique_together = ('addon', 'service')

    def __str__(self):
        return f"{self.addon.name} -> {self.service.name}"

class AppointmentAddon(MixinAudit):
    appointment = models.ForeignKey(
        'services.Appointment',
        on_delete=models.CASCADE,
        related_name='appointment_addons'
    )
    addon = models.ForeignKey(
        ServiceAddon,
        on_delete=models.CASCADE,
        related_name='appointment_addons'
    )
    price_at_booking = models.DecimalField(max_digits=10, decimal_places=2)
    duration_at_booking = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.addon.name} (Appt #{self.appointment_id})"
