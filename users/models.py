# Python Standard Library
import random
from datetime import timedelta

# Third-party Libraries
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

# Local Modules
from core.models import MixinAudit, GeoReferenceCity
from core.validators import validate_file_size, validate_image_extension


# Create your models here.
class User(AbstractUser):

    def generate_file_name(instance, filename):
        date = timezone.now()
        return f'user/{date.year}/{date.month}/{date.day}/{filename}'

    full_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=100, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    identification = models.CharField(max_length=100, blank=True, null=True)
    uuid_google = models.CharField(max_length=100, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    # add additional foreign fields in here
    city = models.ForeignKey(
        GeoReferenceCity, on_delete=models.SET_NULL, null=True, blank=True
    )
    picture = models.ImageField(
        upload_to=generate_file_name, null=True, blank=True,
        validators=[validate_file_size, validate_image_extension]
    )
    gender = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='gender_user'
    )
    type = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='type_user'
    )
    state = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='state_user'
    )
    login = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='login_user'
    )

    def __str__(self):
        return self.username


class UserLevel(MixinAudit):

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='user_level'
    )
    level = models.ForeignKey(
        'core.Level', on_delete=models.CASCADE, related_name='user_level'
    )


class UserVerificationCode(MixinAudit):

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='user_verification_code'
    )
    code = models.CharField(max_length=5, blank=True, null=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    def generate_code_and_set_valid_until(self):
        self.code = random.randint(10000, 99999)
        self.valid_until = timezone.now() + timedelta(minutes=15)
        self.save()


class UserAddress(MixinAudit):

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='user_address'
    )
    address = models.CharField(max_length=100, null=True, blank=True)
    latitude = models.CharField(max_length=100, null=True, blank=True)
    longitude = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.address


class UserTermsAndConditionsManager(models.Manager):

    def accepted_users(self):
        """Usuarios que han aceptado los términos y condiciones."""
        return self.filter(accepted=True).select_related('user')

    def has_accepted(self, user):
        """Verifica si el usuario ha aceptado los términos y condiciones."""
        return self.filter(user=user, accepted=True).exists()


class UserTermsAndConditions(models.Model):
    """Registro de aceptación de términos y condiciones por usuario."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='terms_and_conditions'
    )
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    objects = UserTermsAndConditionsManager()

    class Meta:
        verbose_name = 'Términos y Condiciones de Usuario'
        verbose_name_plural = 'Términos y Condiciones de Usuarios'

    def __str__(self):
        return f'{self.user} - accepted={self.accepted} at {self.accepted_at}'
