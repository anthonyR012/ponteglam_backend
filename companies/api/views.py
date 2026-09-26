"""
File for the API views of the companies application
"""
import logging
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from companies import models
from companies.api import serializers
from companies.tasks import permanently_delete_company_task
from core import models as core_models
from core import utils as core_utils
from core.permissions import get_owned_object, not_found_response
from users import models as users_models
from users import tasks as users_tasks
from rest_framework.decorators import action

logger = logging.getLogger(__name__)


class CreateCompany(viewsets.ViewSet):

    serializer_class_company = serializers.CompanySerializer
    serializer_class_company_file = serializers.CompanyFileSerializer
    status_class = status.HTTP_200_OK
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):

        data = request.data.copy()

        if 'profile_image' not in data and 'profile_image' in request.FILES:
            data['profile_image'] = request.FILES['profile_image']
        if 'cover_image' not in data and 'cover_image' in request.FILES:
            data['cover_image'] = request.FILES['cover_image']

        if not data.get('profile_image'):
            return Response(
                {"error": "La imagen de perfil es obligatoria."},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_by_user_id = request.user.pk
        data['created_by_user_id'] = created_by_user_id

        existing = models.Company.objects.filter(
            created_by_user_id=request.user.pk
        ).first()
        if existing:
            creating_state = core_models.Type.objects.filter(
                code='creating',
                category_type__code='status_company'
            ).first()
            if not creating_state or existing.state_id != creating_state.id:
                return Response(
                    {'error': (
                        'Ya tienes una empresa registrada. '
                        'Solo puedes tener una empresa.'
                    )},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer_company = self.get_or_create_company(data)
        data['company_id'] = serializer_company.data['id']
        self.get_or_create_files(data)

        return Response(
            serializer_company.data,
            status=self.status_class
        )

    def get_or_create_company(self, data):

        company_name = data.get('name')
        created_by_user_id = data.get('created_by_user_id')

        creating_state = core_models.Type.objects.filter(
            code='creating',
            category_type__code='status_company'
        ).first()

        company = None
        if creating_state:
            company = models.Company.objects.filter(
                created_by_user_id=created_by_user_id,
                state_id=creating_state.id
            ).first()

        if not company:
            company = models.Company.objects.filter(
                name=company_name, created_by_user_id=created_by_user_id
            ).first()

        if company:
            serializer_company = self.serializer_class_company(
                instance=company, data=data, partial=True
            )
            serializer_company.is_valid(raise_exception=True)
            company = serializer_company.save()
            self.status_class = status.HTTP_200_OK
        else:
            if 'type' not in data:
                try:
                    type_obj = core_models.Type.objects.get_type(
                        code='independent',
                        category_type_code='type_company'
                    )
                    data['type'] = type_obj.id
                except core_models.Type.DoesNotExist:
                    pass

            if 'state' not in data:
                if creating_state:
                    data['state'] = creating_state.id
                else:
                    try:
                        state_obj = core_models.Type.objects.get_type(
                            code='creating',
                            category_type_code='status_company'
                        )
                        data['state'] = state_obj.id
                    except core_models.Type.DoesNotExist:
                        pass

            serializer_company = self.serializer_class_company(data=data)
            try:
                serializer_company.is_valid(raise_exception=True)
            except ValidationError as e:
                self._handle_validation_error(e)
            company = serializer_company.save()
            self.status_class = status.HTTP_201_CREATED

        return serializer_company

    def get_or_create_files(self, data):
        try:
            type_file_profile_image = core_models.Type.objects.get_type(
                code='profile_image',
                category_type_code='type_file'
            )

            type_file_cover_image = core_models.Type.objects.get_type(
                code='cover_image',
                category_type_code='type_file'
            )
        except core_models.Type.DoesNotExist:

            raise ValidationError(
                {"detail": "Falta configuración para crear compañias"}
            )

        data_company_file = []

        company_id = data.get('company_id')
        profile_image = data.get('profile_image')
        cover_image = data.get('cover_image')
        created_by_user_id = data.get('created_by_user_id')

        exists_profile_image = models.CompanyFile.objects.filter(
            company_id=company_id, type_id=type_file_profile_image.id
        ).exists()

        exists_cover_image = models.CompanyFile.objects.filter(
            company_id=company_id, type_id=type_file_cover_image.id
        ).exists()

        if profile_image and not exists_profile_image:
            data_company_file.append(
                {
                    'company': company_id,
                    'type': type_file_profile_image.id,
                    'file': profile_image,
                    'created_by_user_id': created_by_user_id
                }
            )
        if cover_image and not exists_cover_image:
            data_company_file.append(
                {
                    'company': company_id,
                    'type': type_file_cover_image.id,
                    'file': cover_image,
                    'created_by_user_id': created_by_user_id
                }
            )

        if data_company_file:
            serializer_company_file = self.serializer_class_company_file(
                data=data_company_file, many=True
            )
            serializer_company_file.is_valid(raise_exception=True)
            serializer_company_file.save()

    def _handle_validation_error(self, e: ValidationError):
        """Helper to return user-friendly messages for common validation errors."""
        details = e.detail
        if isinstance(details, dict):
            if 'company' in details:
                msg = details['company'][0]
                if 'does not exist' in msg or 'Invalid pk' in msg:
                    raise ValidationError(
                        {"detail": "La empresa no existe o ha sido eliminada. Por favor, recarga los datos."}
                    )
            if 'type' in details or 'state' in details:
                raise ValidationError(
                    {"detail": "El tipo o estado configurado no existe. Por favor, sincroniza los datos."}
                )
            if 'geo_reference_city' in details:
                raise ValidationError(
                    {"detail": "La ciudad seleccionada no es válida o ha sido reiniciada. Por favor, selecciona la ciudad nuevamente."}
                )
        raise e


class ListCompanies(viewsets.ModelViewSet):

    serializer_class = serializers.CompanySerializer
    authentication_classes = [TokenAuthentication]
    pagination_class = core_utils.CustomPagination
    queryset = models.Company.objects.all()

    def list(self, request: Request, *args, **kwargs):

        query_page = request.query_params.get('page')
        mine = request.query_params.get('mine')
        queryset = self.filter_queryset(self.get_queryset())

        if mine == 'true':
            queryset = queryset.filter(created_by_user_id=request.user.pk)

        page = self.paginate_queryset(queryset)

        if page is not None:
            cache_key = f'companies_list_page_{query_page}_mine_{mine}'
            cache_data = cache.get(cache_key)

            if cache_data is not None:
                return self.get_paginated_response(cache_data)

            serializer = self.get_serializer(page, many=True)
            cache.set(cache_key, serializer.data, timeout=50)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        return Response(
            {
                'success': data
            },
            status=status.HTTP_200_OK
        )


class UpdateCompany(viewsets.ViewSet):

    authentication_classes = [TokenAuthentication]

    def partial_update(self, request: Request, pk=None, *args, **kwargs):
        company = get_owned_object(models.Company, pk, request.user)
        if not company:
            return not_found_response(
                'Empresa no encontrada o no tienes permiso para editarla.'
            )

        data = request.data.copy()
        data['created_by_user_id'] = request.user.pk

        serializer = serializers.CompanySerializer(
            company, data=data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if 'profile_image' in request.FILES:
            try:
                type_profile = core_models.Type.objects.get_type(
                    code='profile_image',
                    category_type_code='type_file'
                )
                models.CompanyFile.objects.filter(
                    company=company, type=type_profile
                ).delete()
                file_serializer = serializers.CompanyFileSerializer(
                    data={
                        'company': company.pk,
                        'type': type_profile.id,
                        'file': request.FILES['profile_image'],
                        'created_by_user_id': request.user.pk,
                    }
                )
                file_serializer.is_valid(raise_exception=True)
                file_serializer.save()
            except core_models.Type.DoesNotExist:
                logger.warning(
                    "Type 'profile_image' not found for company %s", pk
                )

        return Response(
            {'success': serializer.data},
            status=status.HTTP_200_OK
        )


class DeleteCompany(viewsets.ViewSet):
    """Vista para gestionar la solicitud de eliminación diferida de una empresa."""

    authentication_classes = [TokenAuthentication]

    def destroy(self, request: Request, pk=None, *args, **kwargs):
        company = get_owned_object(models.Company, pk, request.user)
        if not company:
            return not_found_response(
                'Empresa no encontrada o no tienes permiso para eliminarla.'
            )

        # Soft-delete the company immediately from active listings
        company.is_deleted = True
        company.deleted_at = timezone.now()
        company.save()

        # Schedule the permanent deletion task for 5 days from now
        scheduled_date = timezone.now() + timedelta(days=5)
        models.CompanyDeletionAudit.objects.create(
            company_id=company.id,
            company_name=company.name,
            requested_by_user_id=request.user.id,
            requested_by_user_email=request.user.email,
            scheduled_deletion_date=scheduled_date
        )

        permanently_delete_company_task.apply_async(
            args=[company.id],
            eta=scheduled_date
        )

        return Response(
            {'success': 'La empresa ha sido programada para eliminación. Se borrará permanentemente junto con todas sus sedes y servicios asociados en 5 días.'},
            status=status.HTTP_200_OK
        )


class CompanyNequiViewSet(viewsets.ViewSet):
    """ViewSet para gestionar el registro y actualización del número de Nequi de una empresa."""

    authentication_classes = [TokenAuthentication]

    @action(detail=True, methods=['post'], url_path='request-nequi-update')
    def request_nequi_update(self, request: Request, pk=None):
        """Genera y envía un código de verificación por correo para autorizar el cambio de Nequi."""
        company = get_owned_object(models.Company, pk, request.user)
        if not company:
            return not_found_response(
                'Empresa no encontrada o no tienes permiso para editarla.'
            )

        verification_code, _ = users_models.UserVerificationCode.objects.get_or_create(
            user=request.user,
            created_by_user_id=request.user.pk
        )
        verification_code.generate_code_and_set_valid_until()

        users_tasks.verification_email_user.delay(request.user.pk)

        return Response(
            {"success": "Verification code sent successfully to your registered email."},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'], url_path='update-nequi')
    def update_nequi(self, request: Request, pk=None):
        """Valida el código de verificación OTP y actualiza el número de Nequi."""
        company = get_owned_object(models.Company, pk, request.user)
        if not company:
            return not_found_response(
                'Empresa no encontrada o no tienes permiso para editarla.'
            )

        nequi_number = request.data.get('nequi_number')
        verification_code_str = request.data.get('verification_code')

        if not nequi_number:
            return Response(
                {"error": "Nequi number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not verification_code_str:
            return Response(
                {"error": "Verification code is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        verification_code = users_models.UserVerificationCode.objects.filter(
            user=request.user, code=verification_code_str
        ).first()

        if not verification_code:
            return Response(
                {"error": "Invalid verification code."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if verification_code.valid_until < timezone.now():
            return Response(
                {"error": "Verification code has expired."},
                status=status.HTTP_400_BAD_REQUEST
            )

        company.nequi_number = nequi_number
        company.save()

        verification_code.delete()

        serializer = serializers.CompanySerializer(company, context={'request': request})
        return Response(
            {"success": serializer.data},
            status=status.HTTP_200_OK
        )

