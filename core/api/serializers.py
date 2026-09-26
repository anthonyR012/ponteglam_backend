# Python Standard Library
from cities_light import models as cities_light_models
from rest_framework import serializers

from core import models


class TypeSerializer(serializers.ModelSerializer):

    category_type_code = serializers.CharField(
        source='category_type.code', read_only=True
    )

    class Meta:
        model = models.Type
        fields = ('id', 'code', 'description', 'category_type_code')


class CountrySerializer(serializers.ModelSerializer):

    class Meta:
        model = cities_light_models.Country
        fields = ('id', 'code3', 'name', 'phone')


class CitySerializer(serializers.ModelSerializer):

    class Meta:
        model = cities_light_models.City
        fields = ('id', 'display_name', 'name')


class GeoReferenceCitySerializer(serializers.ModelSerializer):
    """Serializer públíco que expone las ciudades soportadas por Ponteglam."""

    class Meta:
        model = models.GeoReferenceCity
        fields = ('id', 'name', 'latitude', 'longitude')

class MobileAppLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.MobileAppLog
        fields = (
            'id', 'device_info', 'description', 'source', 'created_at',
            'created_by_user_id'
        )
        read_only_fields = ['id']


class AmenitySerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Amenity
        fields = '__all__'


class LegalContentSerializer(serializers.ModelSerializer):
    type_code = serializers.CharField(source='type.code', read_only=True)

    class Meta:
        model = models.LegalContent
        fields = ('id', 'title', 'content', 'version', 'type_code')
        read_only_fields = ('id', 'type_code')
