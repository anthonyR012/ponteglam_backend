# Python Standard Library
import os
import requests
import time
from datetime import datetime

# Third-party Libraries
from django.contrib.auth import authenticate
from django.core.files.base import ContentFile
from django.utils import timezone
from fcm_django.models import FCMDevice
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

# Local Modules
from notifications.models import DeviceToken
from core.models import Type
from core.permissions import not_found_response
from core.throttles import LoginRateThrottle
from users import models
from users import tasks
from users.api import serializers


class CustomAuthToken(ObtainAuthToken):
    serializer_class = serializers.BaseUserSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request: Request, *args, **kwargs):
        data = request.data
        username = data.get('username')
        password = data.get('password')

        user = authenticate(
            request=request, username=username, password=password)
        if not user:
            return Response(
                {'error': 'Credenciales inválidas'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not models.UserTermsAndConditions.objects.has_accepted(user):
            return Response(
                {'error': 'Debe aceptar los términos y condiciones para ingresar al aplicativo'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.serializer_class(
            user, data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        token, created = Token.objects.get_or_create(user=user)

        serialized_data = serializer.data
        serialized_data['token'] = token.key

        return Response(
            {
                'success': 'Login exitoso',
                'user': serialized_data,
            },
            status=status.HTTP_200_OK
        )


class RegistrationOauthAPI(viewsets.ViewSet):
    serializer_class = serializers.RegisterOauthUserSerializer
    permission_classes = [AllowAny]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        access_token_google = data.get('access_google_token')
        email = data.get('email')
        url_picture = data.get('picture')
        accepted_terms = data.get('accepted_terms', False)

        google_token_valid = self.validate_google_token(
            access_token_google, email
        )
        if not google_token_valid:
            return Response(
                {'error': 'Invalid Google Token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = models.User.objects.filter(email=email).first()
        if user:
            return self.handle_existing_user(user, accepted_terms)

        data['picture'] = self.get_google_picture(url_picture)

        return self.handle_new_user(data)

    def validate_google_token(self, access_token, email):
        token_validation = requests.get(
            f'https://oauth2.googleapis.com/'
            f'tokeninfo?access_token={access_token}'
        )

        if token_validation.status_code == status.HTTP_200_OK:
            user_info = token_validation.json()
            if user_info.get('email') == email:
                return True

        return False

    def get_google_picture(self, url_picture):
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                response = requests.get(url_picture, stream=True)
                response.raise_for_status()

                filename = os.path.basename(url_picture)
                if '.' not in filename:
                    filename += '.jpg'
                picture = ContentFile(response.content, name=filename)
                return picture

            except requests.exceptions.RequestException:
                if attempt == max_attempts - 1:
                    return None

                time.sleep(1)

    def handle_existing_user(self, user: models.User, accepted_terms: bool):
        if accepted_terms:
            tc_serializer = serializers.CreateUserTermsAndConditionsSerializer(
                data={'user': user.pk, 'accepted': True}
            )
            tc_serializer.is_valid(raise_exception=True)
            tc_serializer.save()
        elif not models.UserTermsAndConditions.objects.has_accepted(user):
            return Response(
                {'error': 'Debe aceptar los términos y condiciones para ingresar al aplicativo'},
                status=status.HTTP_403_FORBIDDEN
            )

        token, created = Token.objects.get_or_create(user=user)

        serializer_data = self.serializer_class(
            user, context={'request': self.request}
        ).data
        serializer_data['token'] = token.key

        return Response(
            {
                'success': 'Usuario registrado exitosamente',
                'user': serializer_data
            },
            status=status.HTTP_200_OK
        )

    def handle_new_user(self, data):
        serializer = self.serializer_class(
            data=data, context={'request': self.request}
        )
        serializer.is_valid(raise_exception=True)

        user: models.User = serializer.save()
        user.email_verified = True
        try:
            user.login = Type.objects.get_type('by_gmail', 'login_of')
        except Type.DoesNotExist:
            pass
        user.save()

        token, created = Token.objects.get_or_create(user=user)

        # TODO: Add FCM registration
        try:
            # https://fcm-django.readthedocs.io/en/latest/
            registration_id = data.get('registration_id')
            device_id = data.get('device_id')
            type_device = data.get('type_device')  # 'android', 'web' or 'ios'

            FCMDevice.objects.create(
                registration_id=registration_id,
                device_id=device_id,
                type=type_device,
                user=user
            )

        except Exception as e:
            print(e)

        serializer_data = serializer.data
        serializer_data['token'] = token.key

        return Response(
            {
                'success': 'Usuario registrado exitosamente',
                'user': serializer_data
            },
            status=status.HTTP_201_CREATED
        )


class RegistrationAlternateAPI(viewsets.ViewSet):
    serializer_class = serializers.RegisterUserSerializer
    permission_classes = [AllowAny]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        email = data.get('email')
        picture = data.get('picture')

        if not picture or picture == '':
            data['picture'] = None

        user = models.User.objects.filter(email=email).first()
        if user:
            return Response(
                {'error': 'Ya existe un usuario con el correo ingresado'},
                status=status.HTTP_409_CONFLICT
            )

        serializer = self.serializer_class(
            data=data, context={'request': self.request}
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        try:
            user.login = Type.objects.get_type('by_credentials', 'login_of')
            user.save()
        except Type.DoesNotExist:
            pass
        token, created = Token.objects.get_or_create(user=user)

        # TODO: Add FCM registration
        try:
            # https://fcm-django.readthedocs.io/en/latest/
            registration_id = data.get('registration_id')
            device_id = data.get('device_id')
            type_device = data.get('type_device')  # 'android', 'web' or 'ios'

            FCMDevice.objects.create(
                registration_id=registration_id,
                device_id=device_id,
                type=type_device,
                user=user
            )

        except Exception as e:
            print(e)

        verification_code, _ = models.UserVerificationCode.objects.get_or_create(
            user=user,
            created_by_user_id=user.pk
        )
        verification_code.generate_code_and_set_valid_until()

        serializer_data = serializer.data
        serializer_data['token'] = token.key

        tasks.verification_email_user.delay(user.pk)

        return Response(
            {
                'success': 'Usuario registrado exitosamente, '
                           'se ha enviado un correo de verificación',
                'user': serializer_data,
            },
            status=status.HTTP_201_CREATED
        )


class BaseVerifyEmail(viewsets.ViewSet):

    def handle_verification_code(self, user, code):
        if not user:
            return Response(
                {'error': 'No existe un usuario con el correo ingresado'},
                status=status.HTTP_409_CONFLICT
            )

        verification_code = models.UserVerificationCode.objects.filter(
            user=user, code=code
        ).first()

        if not verification_code:
            return Response(
                {'error': 'Código inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if verification_code.valid_until < timezone.now():
            return Response(
                {'error': 'Código expirado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.email_verified = True
        user.save()

        return user


class VerifyEmail(BaseVerifyEmail):
    serializer_class = serializers.BaseUserSerializer
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        code = data.get('code')
        user = request.user

        result = self.handle_verification_code(user, code)
        if isinstance(result, Response):
            return result

        token, created = Token.objects.get_or_create(user=user)

        serializer = self.serializer_class(user, context={'request': request})
        serialized_data = serializer.data
        serialized_data['token'] = token.key

        return Response(
            {
                'success':  'Correo verificado exitosamente',
                'user': serialized_data
            },
            status=status.HTTP_200_OK
        )


class ForwardVerificationEmail(viewsets.ViewSet):
    serializer_class = serializers.BaseUserSerializer
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        user = request.user

        verification_code, _ = models.UserVerificationCode.objects.get_or_create(
            user=user,
            created_by_user_id=user.pk
        )
        verification_code.generate_code_and_set_valid_until()

        token, created = Token.objects.get_or_create(user=user)

        serializer = self.serializer_class(user, context={'request': request})
        serializer_data = serializer.data
        serializer_data['token'] = token.key

        tasks.verification_email_user.delay(user.pk)

        return Response(
            {
                'success': 'Se ha enviado un correo de verificación.',
                'user': serializer_data,
            },
            status=status.HTTP_201_CREATED
        )


class RequestRecoverUser(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        email = data.get('email')

        user = models.User.objects.filter(email=email).first()
        if not user:
            return Response(
                {'error': 'No existe un usuario con el correo ingresado'},
                status=status.HTTP_409_CONFLICT
            )

        verification_code, _ = models.UserVerificationCode.objects.get_or_create(
            user=user,
            created_by_user_id=user.pk
        )
        verification_code.generate_code_and_set_valid_until()

        tasks.verification_email_recover_user.delay(user.pk)

        return Response(
            {
                'success': 'Se ha enviado un codigo de recuperación al '
                           'correo ingresado'
            },
            status=status.HTTP_200_OK
        )


class VerifyEmailRecoverUser(BaseVerifyEmail):
    serializer_class = serializers.BaseUserSerializer
    permission_classes = [AllowAny]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        code = data.get('code')
        email = data.get('email')

        user = models.User.objects.filter(email=email).first()

        result = self.handle_verification_code(user, code)
        if isinstance(result, Response):
            return result

        token, created = Token.objects.get_or_create(user=user)

        serializer = self.serializer_class(user, context={'request': request})
        serialized_data = serializer.data
        serialized_data['token'] = token.key

        return Response(
            {
                'success':  'Correo verificado exitosamente',
                'user': serialized_data
            },
            status=status.HTTP_200_OK
        )


class UpdatePassword(viewsets.ViewSet):
    serializer_class = serializers.UpdatePasswordSerializer
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        
        serializer = self.serializer_class(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {'success': 'Contraseña actualizada exitosamente'},
            status=status.HTTP_200_OK
        )

class RequestCreatePassword(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        user = request.user
        
        if not user.uuid_google:
            return Response(
                {'error': 'Este endpoint es solo para usuarios registrados con OAuth.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        verification_code, _ = models.UserVerificationCode.objects.get_or_create(
            user=user,
            created_by_user_id=user.pk
        )
        verification_code.generate_code_and_set_valid_until()

        tasks.verification_email_user.delay(user.pk)

        return Response(
            {
                'success': 'Se ha enviado un código de verificación a su correo.'
            },
            status=status.HTTP_200_OK
        )

class ConfirmCreatePassword(BaseVerifyEmail):
    authentication_classes = [TokenAuthentication]
    
    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        code = data.get('code')
        new_password = data.get('new_password')
        user = request.user

        if not new_password:
            return Response(
                {'error': 'new_password es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.uuid_google:
            return Response(
                {'error': 'Este endpoint es solo para usuarios registrados con OAuth.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = self.handle_verification_code(user, code)
        if isinstance(result, Response):
            return result

        # Validate complexity
        try:
            serializers.validate_password_complexity(new_password)
        except serializers.ValidationError as e:
            return Response(
                {'error': e.detail[0]},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Setting the password
        user.set_password(new_password)
        user.save()

        return Response(
            {
                'success': 'Contraseña creada exitosamente',
            },
            status=status.HTTP_200_OK
        )


class UpdateUserInfo(viewsets.ViewSet):
    serializer_class = serializers.UpdateUserInfoSerializer
    authentication_classes = [TokenAuthentication]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user

        serializer = self.serializer_class(user, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                'success': 'Información actualizada exitosamente',
                'user': serializer.data
            },
            status=status.HTTP_200_OK
        )


class CreateUserAddress(viewsets.ViewSet):
    serializer_class = serializers.CreateUserAddressSerializer
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        user = request.user
        data['user'] = user.pk
        data['created_by_user_id'] = user.pk

        existing = models.UserAddress.objects.filter(user=user)

        user_address = existing.filter(address=data['address']).first()

        if not user_address and existing.count() >= 3:
            return Response(
                {'error': 'Maximum of 3 addresses allowed per user.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.serializer_class(instance=user_address, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                'success': 'Dirección registrada exitosamente',
                'address': serializer.data
            },
            status=status.HTTP_201_CREATED
        )


class UpdateUserAddress(viewsets.ViewSet):
    serializer_class = serializers.UpdateUserAddressSerializer
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        user_address_id = data.get('user_address_id')

        if not user_address_id:
            return Response(
                {'error': 'user_address_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_address = models.UserAddress.objects.filter(
            id=user_address_id, user=request.user
        ).first()

        if not user_address:
            return not_found_response(
                'Dirección no encontrada o no tienes permiso para editarla.'
            )

        serializer = self.serializer_class(instance=user_address, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                'success': 'Dirección actualizada exitosamente',
                'address': serializer.data
            },
            status=status.HTTP_200_OK
        )


class ListUserAddresses(viewsets.ViewSet):
    serializer_class = serializers.ListUserAddressSerializer
    authentication_classes = [TokenAuthentication]

    def list(self, request: Request, *args, **kwargs):
        user = request.user
        addresses = models.UserAddress.objects.filter(user=user)

        serializer = self.serializer_class(addresses, many=True)

        return Response(
            {'success': serializer.data},
            status=status.HTTP_200_OK
        )


class DeleteUserAddress(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def destroy(self, request: Request, pk=None, *args, **kwargs):
        address = models.UserAddress.objects.filter(
            pk=pk, user=request.user
        ).first()

        if not address:
            return Response(
                {'error': 'Address not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        address.delete()
        return Response(
            {'success': 'Address deleted successfully.'},
            status=status.HTTP_200_OK,
        )


class MeView(viewsets.ViewSet):
    """Retorna el perfil completo del usuario autenticado."""

    serializer_class = serializers.MeSerializer
    authentication_classes = [TokenAuthentication]

    def list(self, request: Request, *args, **kwargs):
        serializer = self.serializer_class(
            request.user, context={'request': request}
        )
        return Response(
            {'success': serializer.data},
            status=status.HTTP_200_OK
        )


class UserTermsAndConditionsView(viewsets.ViewSet):
    """CRUD de aceptación de términos y condiciones por usuario."""

    authentication_classes = [TokenAuthentication]

    def list(self, request: Request, *args, **kwargs):
        records = models.UserTermsAndConditions.objects.accepted_users()
        serializer = serializers.UserTermsAndConditionsSerializer(records, many=True)
        return Response(
            {'success': serializer.data},
            status=status.HTTP_200_OK
        )

    def create(self, request: Request, *args, **kwargs):
        serializer = serializers.CreateUserTermsAndConditionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()

        result = serializers.UserTermsAndConditionsSerializer(record)
        return Response(
            {
                'success': 'Términos y condiciones registrados exitosamente',
                'terms': result.data
            },
            status=status.HTTP_200_OK
        )

    def destroy(self, request: Request, pk=None, *args, **kwargs):
        record = models.UserTermsAndConditions.objects.filter(
            user=request.user
        ).first()
        if not record:
            return not_found_response(
                'No se encontró registro de T&C para tu cuenta.'
            )

        record.delete()
        return Response(
            {'success': 'Registro de términos y condiciones eliminado exitosamente'},
            status=status.HTTP_200_OK
        )


class LogoutUser(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request: Request, *args, **kwargs):
        DeviceToken.objects.filter(user=request.user).delete()
        Token.objects.filter(user=request.user).delete()
        return Response(
            {'success': 'Logout exitoso'},
            status=status.HTTP_200_OK,
        )
