# Python Standard Library
from django.db import models
from cities_light.models import City
# Local Modules
from core import managers
from core.validators import validate_file_size, validate_image_extension


# Create your models here.
class MixinAudit(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_user_id = models.PositiveIntegerField()
    modified_by_user_id = models.PositiveIntegerField(
        default=None, null=True, blank=True
    )

    class Meta:
        abstract = True


class Category(MixinAudit):

    code = models.CharField(max_length=100)
    description = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.description


class Type(MixinAudit):

    category_type = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='category_type'
    )
    code = models.CharField(max_length=100)
    description = models.CharField(max_length=100, null=True, blank=True)

    objects = managers.TypeManager()

    def __str__(self):
        return self.description


class WeekDay(MixinAudit):

    code = models.CharField(max_length=100)
    description = models.CharField(max_length=100)

    def __str__(self):
        return self.description


class TimeConfiguration(MixinAudit):

    hours = models.PositiveIntegerField()
    minutes = models.PositiveIntegerField()

    def __str__(self):
        return f"Hours {self.hours} Minutes {self.minutes}"


class WeekDayTimeConfiguration(MixinAudit):

    week_day = models.ForeignKey(
        WeekDay, on_delete=models.CASCADE,
        related_name='week_day_time_configuration'
    )
    time_configuration = models.ForeignKey(
        TimeConfiguration, on_delete=models.CASCADE,
        related_name='week_day_time_configuration'
    )
    aditional_fee = models.DecimalField(
        null=True, blank=True, max_digits=10, decimal_places=2
    )

    def __str__(self):
        return self.week_day


class HourWeekDayTimeConfiguration(MixinAudit):

    week_day_time_configuration = models.ForeignKey(
        WeekDayTimeConfiguration, on_delete=models.CASCADE,
        related_name='hour_week_day_time_configuration'
    )
    aditional_fee = models.DecimalField(
        null=True, blank=True, max_digits=10, decimal_places=2
    )
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return self.week_day_time_configuration


class Level(MixinAudit):

    point = models.PositiveIntegerField()
    color = models.CharField(max_length=100)
    type = models.ForeignKey(
        Type, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='type_level'
    )

    def __str__(self):
        return self.point


class FileMixin(MixinAudit):
    """
    Abstract class for models that need a file field.
    """

    @staticmethod
    def generate_file_name(instance, filename):
        raise NotImplementedError(
            "Subclasses must implement generate_file_name method."
        )

    def get_upload_to(instance, filename):
        return instance.generate_file_name(instance, filename)

    file = models.ImageField(
        upload_to=get_upload_to, null=True, blank=True,
        validators=[validate_file_size, validate_image_extension]
    )
    type = models.ForeignKey(
        Type, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='type_%(class)s'
    )

    class Meta:
        abstract = True


class Amenity(MixinAudit):
    """
    Model that store information of something that helps
    to provide comfort, convenience, or enjoyment.
    """

    code = models.CharField(max_length=100)
    description = models.CharField(max_length=100, null=True, blank=True)
    color = models.CharField(max_length=100)
    icon_name = models.CharField(max_length=100)

    def __str__(self):
        return self.description


class GeoReferenceCity(MixinAudit):

    name = models.CharField(max_length=100)
    city = models.ForeignKey(
        City, on_delete=models.SET_NULL, null=True, blank=True
    )
    latitude = models.CharField(max_length=50)
    longitude = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class MobileAppLog(MixinAudit):
    """
    Model for PonteGlam mobile app logs.
    """

    device_info = models.TextField()
    description = models.TextField()
    source = models.TextField()


class LegalContent(MixinAudit):
    """
    Model that store legal information like terms and conditions,
    privacy policy, etc.
    """

    title = models.CharField(max_length=200)
    content = models.TextField()
    version = models.CharField(max_length=50)
    type = models.ForeignKey(
        Type, on_delete=models.CASCADE, related_name='legal_contents'
    )
    state = models.ForeignKey(
        Type, on_delete=models.CASCADE, related_name='legal_contents_state'
    )

    def __str__(self):
        return f"{self.title} ({self.version})"
