from rest_framework import serializers

from ratings import models


class HeadquarterRatingSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.HeadquarterRating
        fields = '__all__'
        extra_kwargs = {
            'created_by_user_id': {'required': True},
        }


class HeadquarterServiceRatingSerializer(serializers.ModelSerializer):
    """Serializer para calificaciones de servicios en sedes."""

    user_name = serializers.SerializerMethodField()
    user_picture = serializers.SerializerMethodField()

    response = serializers.SerializerMethodField()

    class Meta:
        model = models.HeadquarterServiceRating
        fields = (
            'id', 'headquarter_service', 'user', 'user_name', 'user_picture',
            'rating', 'comment', 'created_at', 'response'
        )
        read_only_fields = ('id', 'user', 'user_name', 'user_picture', 'created_at', 'response')

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.full_name or obj.user.username
        return None

    def get_user_picture(self, obj):
        request = self.context.get('request')
        if obj.user and obj.user.picture:
            url = obj.user.picture.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None

    def get_response(self, obj):
        if obj.supplier_reply:
            request = self.context.get('request')
            hq = obj.headquarter_service.headquarter
            host = request.build_absolute_uri('/')[:-1] if request else None
            hq_image = hq.get_company_picture_url(host=host)
            
            return {
                "message": obj.supplier_reply,
                "replied_at": obj.replied_at.isoformat() if obj.replied_at else None,
                "headquarter_name": hq.name,
                "headquarter_image": hq_image
            }
        return None


class CreateHeadquarterServiceRatingSerializer(serializers.Serializer):
    """Serializer para crear una calificación de servicio."""

    service_id = serializers.IntegerField(required=True)
    appointment_id = serializers.IntegerField(required=False, allow_null=True)
    rating = serializers.IntegerField(required=True, min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, default='')


class CreateHeadquarterRatingSerializer(serializers.Serializer):
    """Serializer para crear una calificación de sede."""

    headquarter_id = serializers.IntegerField(required=True)
    appointment_id = serializers.IntegerField(required=True)
    rating = serializers.IntegerField(required=True, min_value=1, max_value=5)

class ReplyHeadquarterServiceRatingSerializer(serializers.Serializer):
    """Serializer para que un proveedor responda a una calificación de servicio."""
    reply = serializers.CharField(required=True, allow_blank=False)
