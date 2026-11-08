import logging
import re

from django.db.models import Q
from django.utils.html import strip_tags
from rest_framework import serializers

from headquarters import models
from companies.api.serializers import CompanyBasicSerializer, sanitize_text
from services.api.serializers import ServiceSerializer
from services.models import Service

logger = logging.getLogger(__name__)


class HeadquarterSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Headquarter
        fields = [f.name for f in models.Headquarter._meta.fields]\
            + ['image_url']
        extra_kwargs = {
            'created_by_user_id': {'required': True},
            'company': {'required': True, 'allow_null': False},
        }

    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj: models.Headquarter):
        request = self.context.get('request')
        host = request.build_absolute_uri('/') if request else None
        return obj.get_company_picture_url(host)

    def validate_name(self, value):
        value = sanitize_text(value)
        if not value:
            raise serializers.ValidationError("El nombre es obligatorio.")
        if len(value) < 3:
            raise serializers.ValidationError(
                "El nombre debe tener al menos 3 caracteres."
            )
        if len(value) > 200:
            raise serializers.ValidationError(
                "El nombre no puede superar los 200 caracteres."
            )
        return value

    def validate_address(self, value):
        if not value:
            return value
        value = sanitize_text(value)
        if len(value) < 5:
            raise serializers.ValidationError(
                "La dirección debe tener al menos 5 caracteres."
            )
        if len(value) > 300:
            raise serializers.ValidationError(
                "La dirección no puede superar los 300 caracteres."
            )
        return value

    def validate_phone_number(self, value):
        if not value:
            return value
        if len(value) > 20:
            raise serializers.ValidationError(
                "El teléfono no puede superar los 20 caracteres."
            )
        if not re.match(r'^[\d\s+\-]+$', value):
            raise serializers.ValidationError(
                "El teléfono solo puede contener números, espacios, + y -"
            )
        return value

    def validate_latitude(self, value):
        try:
            lat = float(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError("Latitud inválida.")
        if not -90 <= lat <= 90:
            raise serializers.ValidationError(
                "Latitud debe estar entre -90 y 90."
            )
        return value

    def validate_longitude(self, value):
        try:
            lng = float(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError("Longitud inválida.")
        if not -180 <= lng <= 180:
            raise serializers.ValidationError(
                "Longitud debe estar entre -180 y 180."
            )
        return value

    def validate(self, data):
        lat = data.get('latitude')
        lng = data.get('longitude')
        if lat is not None and lng is not None:
            try:
                if float(lat) == 0.0 and float(lng) == 0.0:
                    raise serializers.ValidationError(
                        "Selecciona una ubicación válida en el mapa."
                    )
            except (TypeError, ValueError):
                pass
        return data


class HeadquarterWithServicesSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Headquarter
        fields = [
            'id', 'created_at', 'updated_at', 'created_by_user_id',
            'modified_by_user_id', 'name', 'phone_number', 'address',
            'latitude', 'longitude', 'rating_count', 'rating', 'like',
            'geo_reference_city', 'type', 'company', 'company_info',
            'country', 'image_url', 'services'
        ]
        extra_kwargs = {
            'created_by_user_id': {'required': True},
        }

    like = serializers.SerializerMethodField()
    company_info = CompanyBasicSerializer(source='company', read_only=True)
    image_url = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()

    def get_like(self, obj: models.Headquarter):
        return obj.headquarter_like.filter(
            user_id=self.context.get('request').user.id
        ).exists()

    def get_image_url(self, obj: models.Headquarter):
        request = self.context.get('request')
        host = request.build_absolute_uri('/') if request else None

        hq_image = obj.headquarter_file.filter(
            type__code='additional_image'
        ).first()

        if hq_image and hq_image.file:
            url = hq_image.file.url
            if host:
                host = host.rstrip('/')
                return f'{host}{url}'
            return url
        return None

    def get_services(self, obj: models.Headquarter):
        request = self.context.get('request')
        category = self.context.get('category')
        additional_filters = self.context.get('additional_filters')
        search = self.context.get('search')

        services = obj.headquarter_service.values_list('service', flat=True)

        filters = {
            'id__in': services
        }

        if additional_filters:
            filters.update(additional_filters)

        if category:
            filters['service_category__pk'] = category

        if self.context.get('only_available'):
            filters['state__code'] = 'available'

        services_qs = Service.objects.filter(**filters)

        # Si la búsqueda coincide con el nombre de la sede se muestran todos sus servicios.
        if search and search.lower() not in obj.name.lower():
            services_qs = services_qs.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        serialized_services = ServiceSerializer(
            services_qs.distinct(),
            many=True,
            context={'request': request, 'headquarter': obj}
        ).data
        return serialized_services


class HeadquarterFileSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.HeadquarterFile
        fields = '__all__'
        extra_kwargs = {
            'created_by_user_id': {'required': True},
        }


class HeadquarterDetailSerializer(serializers.ModelSerializer):
    """Detalle completo de una sede con servicios y horarios."""

    services = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    name_company = serializers.SerializerMethodField()
    schedules = serializers.SerializerMethodField()

    class Meta:
        model = models.Headquarter
        fields = [
            'id', 'name', 'phone_number', 'address', 'latitude', 'longitude',
            'rating', 'rating_count', 'name_company', 'image_url',
            'services', 'schedules',
        ]

    def get_name_company(self, obj):
        return obj.company.name if obj.company else None

    def get_image_url(self, obj):
        request = self.context.get('request')
        host = request.build_absolute_uri('/') if request else None
        return obj.get_company_picture_url(host)

    def get_services(self, obj):
        from services.api.serializers import ServiceSerializer
        request = self.context.get('request')
        service_ids = obj.headquarter_service.values_list('service', flat=True)
        from services.models import Service
        return ServiceSerializer(
            Service.objects.filter(id__in=service_ids),
            many=True,
            context={'request': request}
        ).data

    def get_schedules(self, obj):
        from core.models import HourWeekDayTimeConfiguration
        schedules = []
        configs = obj.headquater_week_day_time_configuration.select_related(
            'week_day_time_configuration__week_day'
        ).all()
        for config in configs:
            wdtc = config.week_day_time_configuration
            if wdtc and wdtc.week_day:
                hours = HourWeekDayTimeConfiguration.objects.filter(
                    week_day_time_configuration=wdtc
                ).values('start_time', 'end_time')
                schedules.append({
                    'day': wdtc.week_day.code,
                    'hours': list(hours),
                })
        return schedules
