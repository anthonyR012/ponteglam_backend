# Third-party Libraries
from django.db import models
# from datetime import datetime

# Local Modules
from core.models import MixinAudit


# Create your models here.
class Worker(MixinAudit):
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='worker',
        null=True, blank=True
    )
    name = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Nombre para trabajadores anónimos"
    )
    status = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='status_worker'
    )
    type = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='type_worker'
    )

    def __str__(self):
        return self.name if self.name else str(self.user)


class WorkerAvailability(models.Model):
    worker = models.ForeignKey('workers.Worker', on_delete=models.CASCADE)
    weekday = models.IntegerField()  # 0=Lunes, ..., 6=Domingo
    start_time = models.TimeField()
    end_time = models.TimeField()


class WorkerLevel(MixinAudit):

    worker = models.ForeignKey(
        Worker, on_delete=models.CASCADE, related_name='worker_level'
    )
    level = models.ForeignKey(
        'core.Level', on_delete=models.CASCADE,
        related_name='worker_level'
    )

    def __str__(self):
        return str(self.worker)


class WorkerInvitation(MixinAudit):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('accepted', 'Aceptada'),
        ('rejected', 'Rechazada'),
        ('expired', 'Expirada'),
    ]
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    headquarter = models.ForeignKey(
        'headquarters.Headquarter', on_delete=models.CASCADE,
        related_name='invitations'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    invited_user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='worker_invitations'
    )

    def __str__(self):
        return f"Inv: {self.email or self.phone} to {self.headquarter}"


class WorkerBlock(MixinAudit):
    worker = models.ForeignKey(
        Worker, on_delete=models.CASCADE, related_name='blocks'
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    reason = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Block: {self.worker} ({self.start_time})"
