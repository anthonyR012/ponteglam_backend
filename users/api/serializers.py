# Python Standard Library
import re

# Third-party Libraries
from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

# Local Modules
from users import models


def validate_password_complexity(value):
    if len(value) < 8 or len(value) > 15:
        raise serializers.ValidationError(
            "La contraseña debe tener entre 8 y 15 caracteres."
        )
    if not re.search(r'[A-Z]', value):
        raise serializers.ValidationError(
            "La contraseña debe tener al menos una letra mayúscula."
        )
    if not re.search(r'[a-z]', value):
        raise serializers.ValidationError(
            "La contraseña debe tener al menos una letra minúscula."
        )
    if not re.search(r'\d', value):
        raise serializers.ValidationError(
            "La contraseña debe tener al menos un número."
        )

    try:
        django_validate_password(value)
    except DjangoValidationError as e:
        raise serializers.ValidationError(list(e.messages))

    return value


class BaseUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.User
        fields = '__all__'
        read_only_fields = [
            'pk', 'first_name', 'last_name', 'email', 'is_superuser',
            'is_active', 'is_staff', 'date_joined'
        ]
        extra_kwargs = {
            'username': {'required': False},
            'picture': {'required': False},
            'password': {'write_only': True},
        }

    date_of_birth = serializers.DateField(
        format="%d/%m/%Y", input_formats=["%d/%m/%Y", "iso-8601"],
        required=False, allow_null=True
    )
    has_password = serializers.SerializerMethodField()
    login_code = serializers.SerializerMethodField()
    has_accepted_terms = serializers.SerializerMethodField()

    def get_has_password(self, obj):
        return obj.has_usable_password()

    def get_has_accepted_terms(self, obj):
        try:
            return obj.terms_and_conditions.accepted
        except models.UserTermsAndConditions.DoesNotExist:
            return False

    def get_login_code(self, obj):
        if obj.login:
            return obj.login.code
        return None


class PublicUserSerializer(serializers.ModelSerializer):
    """
    Serializer de solo lectura para exponer perfiles de usuario
    sin comprometer información personal sensible (PII).
    """
    class Meta:
        model = models.User
        fields = ['pk', 'full_name', 'picture', 'gender']
        read_only_fields = fields


class RegisterUserSerializer(BaseUserSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=models.User.objects.all()
            )
        ]
    )
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password_complexity]
    )
    accepted_terms = serializers.BooleanField(write_only=True)

    def validate_accepted_terms(self, value):
        if not value:
            raise serializers.ValidationError(
                'Debe aceptar los términos y condiciones para registrarse.'
            )
        return value

    def create(self, validated_data):
        validated_data.pop('accepted_terms')

        user = models.User.objects.create(
            username=validated_data.get('email'),
            email=validated_data.get('email'),
            full_name=validated_data.get('full_name'),
            phone=validated_data.get('phone'),
            picture=validated_data.get('picture'),
            uuid_google=validated_data.get('uuid_google')
        )

        user.set_password(validated_data['password'])
        user.save()

        models.UserTermsAndConditions.objects.create(
            user=user,
            accepted=True,
            accepted_at=timezone.now()
        )

        return user


class RegisterOauthUserSerializer(RegisterUserSerializer):
    """
    Serializer para el registro por OAuth (Google/Firebase).
    Permite passwords de cualquier longitud (UIDs) y maneja la
    creación de usuarios sin requerir contraseña manual.
    """
    password = serializers.CharField(
        write_only=True, required=False, allow_null=True
    )

    def create(self, validated_data):
        # Si no viene password (UID), generamos uno aleatorio
        if not validated_data.get('password'):
            from django.utils.crypto import get_random_string
            validated_data['password'] = get_random_string(32)
        return super().create(validated_data)


class UpdateUserInfoSerializer(serializers.ModelSerializer):
    date_of_birth = serializers.DateField(
        format="%d/%m/%Y", input_formats=["%d/%m/%Y", "iso-8601"],
        required=False, allow_null=True
    )

    has_accepted_terms = serializers.SerializerMethodField()

    def get_has_accepted_terms(self, obj):
        try:
            return obj.terms_and_conditions.accepted
        except models.UserTermsAndConditions.DoesNotExist:
            return False

    class Meta:
        model = models.User
        fields = (
            'pk', 'email', 'full_name', 'phone', 'address', 'gender',
            'city', 'date_of_birth', 'picture', 'has_accepted_terms'
        )

        read_only_fields = ['pk', 'email']
        extra_kwargs = {
            'full_name': {
                'required': True,
                'min_length': 3,
                'max_length': 50,
                'error_messages': {
                    'required': 'El nombre es obligatorio.',
                    'min_length': 'El nombre debe tener al menos 3 caracteres.',
                    'max_length': 'El nombre no puede exceder los 50 caracteres.'
                }
            },
            'phone': {
                'required': False,
                'min_length': 7,
                'max_length': 15,
                'allow_blank': True,
                'error_messages': {
                    'min_length': 'El teléfono debe tener al menos 7 números.',
                    'max_length': 'El teléfono no puede exceder los 15 números.'
                }
            },
            'address': {'required': False},
            'gender': {'required': False},
            'city': {'required': False},
            'picture': {'required': False},
        }

    def validate_phone(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError("El teléfono debe contener solo números.")
        return value

class UpdatePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True, write_only=True, validators=[validate_password_complexity]
    )

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual es incorrecta.")
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

def _validate_latitude(value):
    try:
        lat = float(value)
    except (ValueError, TypeError):
        raise serializers.ValidationError(
            'latitude must be a valid decimal number.'
        )
    if not -90 <= lat <= 90:
        raise serializers.ValidationError(
            'latitude must be between -90 and 90.'
        )
    return value


def _validate_longitude(value):
    try:
        lng = float(value)
    except (ValueError, TypeError):
        raise serializers.ValidationError(
            'longitude must be a valid decimal number.'
        )
    if not -180 <= lng <= 180:
        raise serializers.ValidationError(
            'longitude must be between -180 and 180.'
        )
    return value


class CreateUserAddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.UserAddress
        fields = (
            'pk', 'user', 'address', 'latitude', 'longitude',
            'created_by_user_id',
        )
        read_only_fields = ['pk']
        extra_kwargs = {
            'address': {'required': True},
            'latitude': {'required': True},
            'longitude': {'required': True},
        }

    def validate_latitude(self, value):
        return _validate_latitude(value)

    def validate_longitude(self, value):
        return _validate_longitude(value)


class UpdateUserAddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.UserAddress
        fields = ('pk', 'address', 'latitude', 'longitude')
        read_only_fields = ['pk']
        extra_kwargs = {
            'address': {'required': False},
            'latitude': {'required': False},
            'longitude': {'required': False},
        }

    def validate_latitude(self, value):
        return _validate_latitude(value)

    def validate_longitude(self, value):
        return _validate_longitude(value)


class ListUserAddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.UserAddress
        fields = ('pk', 'address', 'latitude', 'longitude')
        read_only_fields = ['pk', 'address', 'latitude', 'longitude']


class UserTermsAndConditionsSerializer(serializers.ModelSerializer):

    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = models.UserTermsAndConditions
        fields = ('pk', 'user', 'username', 'email', 'accepted', 'accepted_at')
        read_only_fields = ('pk', 'username', 'email', 'accepted_at')


class CreateUserTermsAndConditionsSerializer(serializers.ModelSerializer):

    user = serializers.PrimaryKeyRelatedField(queryset=models.User.objects.all())

    class Meta:
        model = models.UserTermsAndConditions
        fields = ('user', 'accepted')
        validators = []

    def create(self, validated_data):
        user = validated_data['user']
        accepted = validated_data['accepted']

        record, _ = models.UserTermsAndConditions.objects.get_or_create(user=user)
        record.accepted = accepted
        record.accepted_at = timezone.now() if accepted else None
        record.save()

        return record


class MeSerializer(serializers.ModelSerializer):
    """Serializer para el perfil completo del usuario autenticado."""

    addresses = ListUserAddressSerializer(source='user_address', many=True, read_only=True)
    picture_url = serializers.SerializerMethodField()

    class Meta:
        model = models.User
        fields = (
            'pk', 'email', 'full_name', 'phone', 'date_of_birth',
            'email_verified', 'gender', 'city', 'picture_url', 'addresses',
            'uuid_google'
        )
        read_only_fields = fields

    def get_picture_url(self, obj):
        request = self.context.get('request')
        if obj.picture:
            url = obj.picture.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None
