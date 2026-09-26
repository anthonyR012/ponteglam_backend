import logging

from rest_framework import serializers
from django.utils.html import strip_tags

from companies import models

logger = logging.getLogger(__name__)


def sanitize_text(value: str) -> str:
    """Strip HTML tags and reject injection characters: < > { }"""
    if not value:
        return value
    cleaned = strip_tags(value).strip()
    forbidden = set('<>{}')
    if any(c in forbidden for c in cleaned):
        raise serializers.ValidationError(
            "El campo contiene caracteres no permitidos."
        )
    return cleaned


class CompanySerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Company
        fields = '__all__'
        extra_kwargs = {
            'created_by_user_id': {'required': True},
        }

    def validate_name(self, value):
        value = sanitize_text(value)
        if not value:
            raise serializers.ValidationError("El nombre es obligatorio.")
        if len(value) < 3:
            raise serializers.ValidationError(
                "El nombre debe tener al menos 3 caracteres."
            )
        if len(value) > 100:
            raise serializers.ValidationError(
                "El nombre no puede superar los 100 caracteres."
            )
        return value

    def validate_description(self, value):
        value = sanitize_text(value)
        if not value:
            raise serializers.ValidationError(
                "La descripción es obligatoria."
            )
        if len(value) < 10:
            raise serializers.ValidationError(
                "La descripción debe tener al menos 10 caracteres."
            )
        if len(value) > 500:
            raise serializers.ValidationError(
                "La descripción no puede superar los 500 caracteres."
            )
        return value


class CompanyFileSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.CompanyFile
        fields = '__all__'
        extra_kwargs = {
            'created_by_user_id': {'required': True},
        }


class CompanyBasicSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = models.Company
        fields = ['id', 'name', 'description', 'image_url', 'nequi_number']

    def get_image_url(self, obj: models.Company):
        request = self.context.get('request')
        host = request.build_absolute_uri('/') if request else None

        from core import constants
        image = models.CompanyFile.objects.filter(
            company=obj,
            type__code=constants.PROFILE_IMAGE
        ).first()

        if image and image.file:
            url = image.file.url
            if host:
                host = host.rstrip('/')
                return f'{host}{url}'
            return url
        return None
