import core.models as core_models
from django.db import models
from core import utils


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
