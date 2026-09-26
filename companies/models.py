from django.db import models
from django.utils import timezone

from core.models import MixinAudit, FileMixin
from core import constants


class CompanyActiveManager(models.Manager):
    """Manager que retorna únicamente empresas activas (no eliminadas)."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Company(MixinAudit):
    """Modelo que representa una empresa registrada en la plataforma."""

    name = models.TextField()
    description = models.TextField()
    type = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='type_company'
    )
    state = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='state_company'
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    nequi_number = models.CharField(max_length=20, null=True, blank=True)

    objects = CompanyActiveManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.name

    def get_users_liked(self):
        from headquarters.models import HeadquarterLike
        return HeadquarterLike.objects.filter(
            headquarter__company=self).values_list('user_id', flat=True)


class CompanyFile(FileMixin):
    """Archivos multimedia pertenecientes a una empresa."""

    @staticmethod
    def generate_file_name(instance, filename):
        company_name = instance.company.name if instance.company else "unknown_company"
        path = 'companies/{0}/{1}'.format(
            company_name,
            filename
        )
        return path

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, blank=True,
        related_name='company_file'
    )

    def __str__(self):
        return self.file.name


class CompanyDeletionAudit(models.Model):
    """Registro de auditoría permanente para el borrado diferido de empresas."""

    company_id = models.PositiveIntegerField()
    company_name = models.CharField(max_length=255)
    requested_by_user_id = models.PositiveIntegerField()
    requested_by_user_email = models.CharField(max_length=255)
    requested_at = models.DateTimeField(default=timezone.now)
    scheduled_deletion_date = models.DateTimeField()
    is_permanently_deleted = models.BooleanField(default=False)
    purged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Audit {self.company_name} (ID: {self.company_id}) deleted by {self.requested_by_user_email}"
