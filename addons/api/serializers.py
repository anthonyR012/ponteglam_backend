from rest_framework import serializers

from addons.models import ServiceAddon, ServiceAddonLink, AppointmentAddon


class ServiceAddonSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        required=True,
        min_length=2,
        max_length=100
    )

    class Meta:
        model = ServiceAddon
        fields = [
            'id',
            'name',
            'description',
            'price',
            'duration_minutes'
        ]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "El precio no puede ser negativo."
            )
        return value

    def validate_duration_minutes(self, value):
        if value < 10:
            raise serializers.ValidationError(
                "La duración mínima es de 10 minutos."
            )
        return value


class ServiceAddonLinkSerializer(serializers.ModelSerializer):
    addon_id = serializers.IntegerField(source='addon.id', read_only=True)
    service_id = serializers.IntegerField(source='service.id', read_only=True)

    class Meta:
        model = ServiceAddonLink
        fields = ['id', 'addon_id', 'service_id']


class AppointmentAddonSerializer(serializers.ModelSerializer):
    addon = ServiceAddonSerializer(read_only=True)

    class Meta:
        model = AppointmentAddon
        fields = [
            'id',
            'addon',
            'price_at_booking',
            'duration_at_booking'
        ]


class CreateAppointmentAddonSerializer(serializers.Serializer):
    addon_id = serializers.IntegerField()
