from django.db import models
from django.utils import timezone

from core.models import MixinAudit, FileMixin
from core import constants


class HeadquarterActiveManager(models.Manager):
    """Manager que retorna únicamente sedes activas (no eliminadas)."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Headquarter(MixinAudit):
    """Modelo que representa una sede de una empresa en la plataforma."""

    name = models.TextField()
    phone_number = models.TextField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    latitude = models.CharField(max_length=100, null=True, blank=True)
    longitude = models.CharField(max_length=100, null=True, blank=True)
    rating_count = models.IntegerField(default=0)
    rating = models.FloatField(default=0)
    geo_reference_city = models.ForeignKey(
        'core.GeoReferenceCity', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    type = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='type_headquarter'
    )
    state = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='state_headquarter'
    )
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE, null=True, blank=True,
        related_name='headquarter'
    )
    country = models.ForeignKey(
        'cities_light.Country', on_delete=models.SET_NULL, null=True,
        blank=True
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = HeadquarterActiveManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.name

    def get_company_picture_url(self, host=None):
        """Retorna la URL de la imagen de la sede o de perfil de la empresa."""
        hq_image = self.headquarter_file.filter(
            type__code='additional_image'
        ).first()

        if hq_image and hq_image.file:
            url = hq_image.file.url
            if host:
                host = host.rstrip('/')
                return f'{host}{url}'
            return url

        from companies.models import CompanyFile
        image = CompanyFile.objects.filter(
            company=self.company,
            type__code=constants.PROFILE_IMAGE
        ).first()

        if image and image.file:
            url = image.file.url
            if host:
                host = host.rstrip('/')
                return f'{host}{url}'
            return url

        return None


class HeadquarterService(MixinAudit):

    headquarter = models.ForeignKey(
        Headquarter, on_delete=models.CASCADE,
        related_name='headquarter_service'
    )
    service = models.ForeignKey(
        'services.Service', on_delete=models.CASCADE,
        related_name='headquarter_service'
    )
    rating_count = models.IntegerField(default=0)
    rating = models.FloatField(default=0)

    def __str__(self) -> str:
        return f'Hq: {self.headquarter} - Service: {self.service}'


class HeadquarterWorker(MixinAudit):

    headquarter = models.ForeignKey(
        Headquarter, on_delete=models.CASCADE, null=True, blank=True,
        related_name='headquarter_worker'
    )
    worker = models.ForeignKey(
        'workers.Worker', on_delete=models.CASCADE, null=True, blank=True,
        related_name='headquarter_worker'
    )


class HeadquaterWeekDayTimeConfiguration(MixinAudit):

    headquarter = models.ForeignKey(
        Headquarter, on_delete=models.CASCADE, null=True, blank=True,
        related_name='headquater_week_day_time_configuration'
    )
    week_day_time_configuration = models.ForeignKey(
        'core.WeekDayTimeConfiguration', on_delete=models.CASCADE,
        null=True, blank=True
    )


class HeadquarterFile(FileMixin):

    @staticmethod
    def generate_file_name(instance, filename):
        hq_name = "unknown_headquarter"
        company_name = "unknown_company"

        if instance.headquarter:
            hq_name = instance.headquarter.name
            if instance.headquarter.company:
                company_name = instance.headquarter.company.name

        path = 'companies/{0}/{1}/{2}'.format(
            company_name,
            hq_name,
            filename
        )
        return path

    headquarter = models.ForeignKey(
        Headquarter, on_delete=models.CASCADE, null=True, blank=True,
        related_name='headquarter_file'
    )

    def __str__(self):
        return self.file.name


class HeadquarterLike(MixinAudit):

    headquarter = models.ForeignKey(
        Headquarter, on_delete=models.CASCADE, null=True, blank=True,
        related_name='headquarter_like'
    )
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, null=True, blank=True,
    )

    def __str__(self):
        return f'{self.headquarter} - {self.user}'


class HeadquarterDeletionAudit(models.Model):
    """Registro de auditoría permanente para el borrado diferido de sedes."""

    headquarter_id = models.PositiveIntegerField()
    headquarter_name = models.CharField(max_length=255)
    company_id = models.PositiveIntegerField()
    requested_by_user_id = models.PositiveIntegerField()
    requested_by_user_email = models.CharField(max_length=255)
    requested_at = models.DateTimeField(default=timezone.now)
    scheduled_deletion_date = models.DateTimeField()
    is_permanently_deleted = models.BooleanField(default=False)
    purged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Audit {self.headquarter_name} (ID: {self.headquarter_id}) deleted by {self.requested_by_user_email}"
