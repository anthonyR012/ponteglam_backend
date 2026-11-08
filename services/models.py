# Third-party Libraries
from django.db import models
from django.utils import timezone
from services.managers import ServiceCategoryManager, ServiceManager

# Local Modules
from core.models import MixinAudit
from core.validators import validate_file_size, validate_image_extension


# Create your models here.
class Service(MixinAudit):
    """Modelo que representa un servicio ofrecido en la plataforma."""

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=100)
    confirmation_in = models.IntegerField()
    remember_in = models.IntegerField()
    only_home_service = models.BooleanField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    home_service_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
    )
    state = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='state_service'
    )
    gender = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='gender_service'
    )
    service_category = models.ForeignKey(
        'ServiceCategory', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='service_category'
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ServiceManager()
    all_objects = models.Manager()

    def __str__(self) -> str:
        return self.name

    def get_url_images(self, host):
        files = self.service_file.all()
        url_images = []
        host = host.rstrip('/') if host else None
        
        for sf in files:
            if sf.file:
                url = sf.file.url
                if host:
                    url_images.append(f'{host}{url}')
                else:
                    url_images.append(url)
        
        return url_images

    def get_amenities(self):
        amenities = ServiceAmenity.objects.filter(
            service=self
        ).values_list('amenity', flat=True)
        return amenities


class ServiceFile(MixinAudit):

    def generate_file_name(instance, filename):
        date = timezone.now()
        return f'services/{date.year}/{date.month}/{date.day}/' +\
               f'{instance.service.pk}/{filename}'

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, null=True, blank=True,
        related_name='service_file'
    )
    file = models.ImageField(
        upload_to=generate_file_name, null=True, blank=True,
        validators=[validate_file_size, validate_image_extension]
    )
    type = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='type_service_file'
    )


class ServiceCategory(MixinAudit):

    def generate_file_name(instance, filename):
        return f'service_category/{filename}'

    description = models.CharField(max_length=100)
    color = models.CharField(max_length=100)
    picture = models.ImageField(
        upload_to=generate_file_name, null=True, blank=True,
        validators=[validate_file_size, validate_image_extension]
    )
    state = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='state_service_category'
    )

    objects = ServiceCategoryManager()

    def __str__(self):
        return self.description


class Appointment(MixinAudit):

    STATUS_PENDING = 'pending'
    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pendiente de pago'),
        (STATUS_ACTIVE, 'Activa'),
        (STATUS_CANCELLED, 'Cancelada'),
        (STATUS_COMPLETED, 'Completada'),
    ]

    PAYMENT_CARD = 'card'
    PAYMENT_CASH = 'cash'

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_CARD, 'Tarjeta'),
        (PAYMENT_CASH, 'Efectivo'),
    ]

    confirmation_in = models.DateTimeField()
    remember_in = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    payment_method = models.CharField(
        max_length=10, choices=PAYMENT_METHOD_CHOICES, default=PAYMENT_CARD
    )
    cancellation_reason = models.TextField(null=True, blank=True)
    refund_pending = models.BooleanField(default=False)
    cancellation_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0
    )
    cancellation_fee_level = models.CharField(
        max_length=20, null=True, blank=True
    )
    reschedule_count = models.PositiveIntegerField(default=0)
    is_home_service = models.BooleanField(default=False)
    home_address = models.ForeignKey(
        'users.UserAddress',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointments',
    )
    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='appointments'
    )
    state = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='state_appointment'
    )
    type = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='type_appointment'
    )


class AppointmentService(MixinAudit):

    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE,
        related_name='appointment_service'
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name='appointment_service'
    )
    worker = models.ForeignKey(
        'workers.Worker', on_delete=models.CASCADE,
        related_name='appointment_service'
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()


class TimeConfigurationService(MixinAudit):

    time_configuration = models.ForeignKey(
        'core.TimeConfiguration', on_delete=models.CASCADE,
        related_name='time_configuration_service'
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE,
        related_name='time_configuration_service'
    )


class WorkerService(MixinAudit):

    worker = models.ForeignKey(
        'workers.Worker', on_delete=models.CASCADE,
        related_name='worker_service'
    )
    service = models.ForeignKey(
        'services.Service', on_delete=models.CASCADE,
        related_name='worker_service'
    )

    is_pending_removal = models.BooleanField(
        default=False,
        help_text="Indica si el trabajador está en proceso de desvinculación"
    )
    removal_date = models.DateTimeField(
        null=True, blank=True,
        help_text="Fecha efectiva de desvinculación (después de la última cita)"
    )

    def __str__(self):
        return str(self.worker)


class ServiceAmenity(MixinAudit):

    amenity = models.ForeignKey(
        'core.Amenity', on_delete=models.CASCADE,
        related_name='service_amenity'
    )
    service = models.ForeignKey(
        'services.Service', on_delete=models.CASCADE,
        related_name='service_amenity'
    )


class Slot(MixinAudit):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_reserved = models.BooleanField(default=False)


class TraceabilityAppointment(MixinAudit):
    """
    Records every state change and significant event for an appointment.
    """
    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE,
        related_name='traceability'
    )
    previous_state = models.CharField(max_length=100, null=True, blank=True)
    new_state = models.CharField(max_length=100)
    change_reason = models.TextField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Traceability {self.appointment_id}: {self.new_state}"


class CancellationRule(MixinAudit):
    """
    Parametrizable rules for cancellation fees.
    Examples:
    - Rule: > 24 hours -> 0% penalty (low)
    - Rule: > 10 hours -> 10% penalty (low)
    """
    FEE_LEVEL_CHOICES = [
        ('low', 'Bajo'),
        ('middle', 'Medio'),
        ('high', 'Alto'),
    ]

    min_hours = models.PositiveIntegerField(
        help_text="Mínimo de horas restantes para aplicar esta regla."
    )
    penalty_pct = models.FloatField(
        help_text="Porcentaje de multa (ej: 0.20 para 20%)."
    )
    fee_level = models.CharField(
        max_length=20, choices=FEE_LEVEL_CHOICES, default='low'
    )
    description = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-min_hours']
        verbose_name = "Regla de Cancelación"
        verbose_name_plural = "Reglas de Cancelación"

    def __str__(self):
        return f">{self.min_hours}h: {int(self.penalty_pct*100)}% ({self.fee_level})"


class ServiceDeletionAudit(models.Model):
    """Registro de auditoría permanente para el borrado diferido de servicios."""

    service_id = models.PositiveIntegerField()
    service_name = models.CharField(max_length=255)
    requested_by_user_id = models.PositiveIntegerField()
    requested_by_user_email = models.CharField(max_length=255)
    requested_at = models.DateTimeField(default=timezone.now)
    scheduled_deletion_date = models.DateTimeField()
    is_permanently_deleted = models.BooleanField(default=False)
    purged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Audit {self.service_name} (ID: {self.service_id}) deleted by {self.requested_by_user_email}"
