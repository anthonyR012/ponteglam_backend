import core.models as core_models
from django.db import models
from core import utils


class ServiceCategoryManager(models.Manager):

    def with_available_services(self):
        """Categorías con al menos un servicio visible para los clientes."""
        prefix = 'service_category__'
        hq = f'{prefix}headquarter_service__headquarter__'
        return self.get_queryset().filter(**{
            f'{prefix}is_deleted': False,
            f'{prefix}state__code': 'available',
            f'{hq}is_deleted': False,
            f'{hq}state__code': 'available',
            f'{hq}company__is_deleted': False,
            f'{hq}company__state__code': 'available',
        }).distinct()


class AppointmentManager(models.Manager):

    def owned_by_supplier(self, user):
        """Citas de servicios creados por el proveedor."""
        return self.get_queryset().filter(
            appointment_service__service__created_by_user_id=user.pk
        ).distinct()


class ServiceManager(models.Manager):
    """
    Manager for the Service model.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_closest_position(service_name, user_latitude, user_longitude):

        geo_reference_city = core_models.GeoReferenceCity.objects.filter(
            # city_id=usuario.city
        )

        # Calculate distances from point A to other positions
        distances = []
        for position in geo_reference_city:
            distance = utils.calculate_km_between_two_points(
                (float(user_latitude), float(user_longitude)),
                (float(position.latitude), float(position.longitude)))
            distances.append((position, distance))

        # Sort positions based on distance
        # sorted_positions = sorted(distances, key=lambda x: x[1])
