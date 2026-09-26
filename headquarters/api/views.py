"""
File for the API views of the headquarters application
"""
import logging
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from headquarters import models
from headquarters.api import serializers
from headquarters.tasks import permanently_delete_headquarter_task
from core import models as core_models
from core.permissions import (
    get_owned_object, verify_headquarter_ownership,
    ownership_denied_response, not_found_response
)


logger = logging.getLogger(__name__)


class CreateHeadquarter(viewsets.ViewSet):

    serializer_class_headquarter = \
        serializers.HeadquarterSerializer
    serializer_class_headquarter_file = \
        serializers.HeadquarterFileSerializer
    status_class = status.HTTP_200_OK
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        created_by_user_id = request.user.pk
        data['created_by_user_id'] = created_by_user_id

        if not data.get('city_id'):
            return Response(
                {"error": "La ciudad es obligatoria."},
                status=status.HTTP_400_BAD_REQUEST
            )

        data['geo_reference_city'] = data.get('city_id')

        company_id = data.get('company_id') or data.get('company')
        hq_count = models.Headquarter.objects.filter(
            company_id=company_id
        ).count()
        if hq_count >= 1:
            return Response(
                {'error': (
                    'Una empresa puede tener máximo '
                    '1 sedes registradas.'
                )},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer_headquarter = \
            self.get_or_create_headquarter(data=data)
        data['headquarter_id'] = \
            serializer_headquarter.data['id']
        self.get_or_create_files(data=data)

        return Response(
            data=serializer_headquarter.data,
            status=self.status_class
        )

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

    def get_or_create_headquarter(self, data):
        name_headquarter = data.get('name')
        company_id = data.get('company_id')
        created_by_user_id = data.get('created_by_user_id')

        headquarter = models.Headquarter.objects.filter(
            name=name_headquarter,
            company_id=company_id,
            created_by_user_id=created_by_user_id
        ).first()

        serializer_headquarter = \
            self.serializer_class_headquarter(
                instance=headquarter
            )

        if not headquarter:
            if 'type' not in data:
                try:
                    type_obj = core_models.Type.objects.get_type(
                        code='main',
                        category_type_code='type_headquarter'
                    )
                    data['type'] = type_obj.id
                except core_models.Type.DoesNotExist:
                    pass

            if 'state' not in data:
                try:
                    state_obj = core_models.Type.objects.get_type(
                        code='available',
                        category_type_code='status_headquarter'
                    )
                    data['state'] = state_obj.id
                except core_models.Type.DoesNotExist:
                    pass

            serializer_headquarter = \
                self.serializer_class_headquarter(data=data)
            try:
                serializer_headquarter.is_valid(raise_exception=True)
            except ValidationError as e:
                self._handle_validation_error(e)
            headquarter = serializer_headquarter.save()
            self.status_class = status.HTTP_201_CREATED

        return serializer_headquarter

    def get_or_create_files(self, data):

        type_file_additional_image = core_models.Type.objects.get_type(
            code='additional_image',
            category_type_code='type_file'
        )

        data_headquarter_file = []

        headquarter_id = data.get('headquarter_id')
        additional_image = self.request.FILES.getlist('additional_image')
        created_by_user_id = data.get('created_by_user_id')

        exists_additional_image = models.HeadquarterFile.objects.filter(
            headquarter_id=headquarter_id,
            type_id=type_file_additional_image.id
        ).exists()

        if additional_image and not exists_additional_image:
            for file in additional_image:
                data_headquarter_file.append(
                    {
                        'headquarter': headquarter_id,
                        'type': type_file_additional_image.id,
                        'file': file,
                        'created_by_user_id': created_by_user_id
                    }
                )

        if data_headquarter_file:
            serializer_headquarter_file =\
                self.serializer_class_headquarter_file(
                    data=data_headquarter_file, many=True
                )

            serializer_headquarter_file.is_valid(raise_exception=True)
            serializer_headquarter_file.save()


class CreateWeekDayTimeConfiguration(viewsets.ViewSet):
    """ViewSet to create a new week day time configuration."""
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        usuario = request.user
        hq_id_val = data.pop('headquarter_id', None)
        if isinstance(hq_id_val, list):
            headquarter_id = hq_id_val[0]
        else:
            headquarter_id = hq_id_val

        if not verify_headquarter_ownership(headquarter_id, usuario):
            return ownership_denied_response(
                'No tienes permiso para configurar esta sede.'
            )

        if not any(v for v in data.values() if v):
            return Response(
                {"error": "Debes configurar al menos un día de trabajo."},
                status=status.HTTP_400_BAD_REQUEST
            )

        models.HeadquaterWeekDayTimeConfiguration.objects.filter(
            headquarter_id=headquarter_id
        ).delete()

        week = data.items()

        for day, hours in week:
            if hours:
                self.create_headquartertimeconfiguration(
                    day, hours, headquarter_id, usuario)

        # Update Company and Headquarter state to available
        try:
            headquarter = models.Headquarter.objects.get(id=headquarter_id)
            
            # Update Headquarter state to available
            hq_available_type = core_models.Type.objects.filter(
                code='available',
                category_type__code='status_headquarter'
            ).first()
            if hq_available_type:
                headquarter.state = hq_available_type
                headquarter.save()

            # Update Company state to available
            company = headquarter.company
            if company:
                company_available_type = core_models.Type.objects.filter(
                    code='available',
                    category_type__code='status_company'
                ).first()
                if company_available_type:
                    company.state = company_available_type
                    company.save()
        except Exception as e:
            logger.error(f"Error updating company/headquarter status to available: {e}")

        return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)

    def create_headquartertimeconfiguration(
            self, day, hours, headquarter_id, usuario):

        DAY_MAPPING = {
            'monday': 'lunes',
            'tuesday': 'martes',
            'wednesday': 'miercoles',
            'thursday': 'jueves',
            'friday': 'viernes',
            'saturday': 'sabado',
            'sunday': 'domingo',
        }

        weekday = DAY_MAPPING.get(day.lower(), day.lower())
        times = hours.split(';')

        if len(times) > 2:
            raise ValidationError(
                {"error": (
                    f"El día {day} no puede tener "
                    "más de 2 franjas horarias."
                )}
            )

        def _parse(time_str):
            for fmt in ("%H:%M", "%H:%M:%S"):
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
            raise ValueError(
                f"Time format for '{time_str}' not recognized"
            )

        _parsed = []
        for _range in times:
            _s, _e = _range.split('-')
            _t1, _t2 = _parse(_s), _parse(_e)
            if _t1 >= _t2:
                raise ValidationError(
                    {"error": (
                        "La hora de inicio debe ser "
                        f"anterior al cierre en {day}."
                    )}
                )
            if (_t2 - _t1).seconds < 1800:
                raise ValidationError(
                    {"error": (
                        "Cada franja debe durar al menos "
                        f"30 minutos en {day}."
                    )}
                )
            _parsed.append((_t1, _t2))

        if len(_parsed) == 2 and _parsed[0][1] > _parsed[1][0]:
            raise ValidationError(
                {"error": f"Las franjas de {day} se solapan entre sí."}
            )

        for time in times:
            start_time_str, end_time_str = time.split('-')

            def parse_time(time_str):
                for fmt in ("%H:%M", "%H:%M:%S"):
                    try:
                        return datetime.strptime(time_str, fmt)
                    except ValueError:
                        continue
                raise ValueError(f"Time format for '{time_str}' not recognized")

            t1 = parse_time(start_time_str)
            t2 = parse_time(end_time_str)
            delta = t2 - t1
            duration_hours = delta.seconds // 3600
            duration_minutes = (delta.seconds // 60) % 60

            weekday_obj = core_models.WeekDay.objects.filter(
                code=weekday
            ).first()

            if not weekday_obj:
                logger.warning(
                    "WeekDay with code '%s' not found. Skipping...", weekday
                )
                continue

            time_config, _ = \
                core_models.TimeConfiguration.objects.get_or_create(
                    hours=duration_hours,
                    minutes=duration_minutes,
                    defaults={
                        'created_by_user_id': usuario.pk
                    }
                )

            w_d_t_config, _ = \
                core_models.WeekDayTimeConfiguration.objects.get_or_create(
                    week_day=weekday_obj,
                    time_configuration=time_config,
                    defaults={
                        'created_by_user_id': usuario.pk
                    }
                )

            core_models.HourWeekDayTimeConfiguration.objects.get_or_create(
                week_day_time_configuration=w_d_t_config,
                start_time=start_time_str,
                end_time=end_time_str,
                defaults={
                    'created_by_user_id': usuario.pk
                }
            )

            models.HeadquaterWeekDayTimeConfiguration.objects.get_or_create(
                headquarter_id=headquarter_id,
                week_day_time_configuration=w_d_t_config,
                defaults={
                    'created_by_user_id': usuario.pk
                }
            )


class HeadquarterLikeView(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        headquarter_id = request.data.get('headquarter_id')
        headquarter = models.Headquarter.objects.filter(
            id=headquarter_id
        ).first()

        if not headquarter:
            return Response(
                {'error': 'Headquarter  not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        models.HeadquarterLike.objects.get_or_create(
            headquarter=headquarter,
            user=request.user,
            created_by_user_id=request.user.pk
        )

        return Response({'success': '¡Liked!'}, status=status.HTTP_201_CREATED)


class HeadquarterDislikeView(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        headquarter_id = request.data.get('headquarter_id')
        headquarter = models.Headquarter.objects.filter(
            id=headquarter_id
        ).first()

        if not headquarter:
            return Response(
                {'error': 'Headquarter  not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        models.HeadquarterLike.objects.filter(
            headquarter=headquarter,
            user=request.user
        ).delete()

        return Response({'success': 'Dislike'},
                        status=status.HTTP_202_ACCEPTED
                        )


class UpdateHeadquarter(viewsets.ViewSet):
    """Permite al proveedor actualizar los datos de su sede."""

    authentication_classes = [TokenAuthentication]

    def partial_update(self, request: Request, pk=None, *args, **kwargs):
        headquarter = get_owned_object(models.Headquarter, pk, request.user)
        if not headquarter:
            return not_found_response(
                'Sede no encontrada o no tienes permiso para editarla.'
            )

        data = request.data.copy()
        data['created_by_user_id'] = request.user.pk

        if 'city_id' in data:
            data['geo_reference_city'] = data.get('city_id')

        if 'additional_image' in request.FILES:
            additional_images = request.FILES.getlist('additional_image')
            if additional_images:
                type_file_additional_image = core_models.Type.objects.get_type(
                    code='additional_image',
                    category_type_code='type_file'
                )
                models.HeadquarterFile.objects.filter(
                    headquarter=headquarter,
                    type=type_file_additional_image
                ).delete()
                hq_files = []
                for img in additional_images:
                    hq_files.append({
                        'headquarter': headquarter.id,
                        'type': type_file_additional_image.id,
                        'file': img,
                        'created_by_user_id': request.user.pk
                    })
                file_serializer = serializers.HeadquarterFileSerializer(
                    data=hq_files, many=True
                )
                file_serializer.is_valid(raise_exception=True)
                file_serializer.save()

        serializer = serializers.HeadquarterSerializer(
            headquarter, data=data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {'success': serializer.data},
            status=status.HTTP_200_OK
        )


class DeleteHeadquarter(viewsets.ViewSet):
    """Vista para gestionar la solicitud de eliminación diferida de una sede."""

    authentication_classes = [TokenAuthentication]

    def destroy(self, request: Request, pk=None, *args, **kwargs):
        headquarter = get_owned_object(models.Headquarter, pk, request.user)
        if not headquarter:
            return not_found_response(
                'Sede no encontrada o no tienes permiso para eliminarla.'
            )

        if headquarter.company_id:
            active_hqs_count = models.Headquarter.objects.filter(
                company_id=headquarter.company_id
            ).count()
            if active_hqs_count <= 1:
                return Response(
                    {'error': 'No puedes eliminar esta sede porque es la única que tiene tu empresa.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Soft-delete the headquarter immediately from active listings
        headquarter.is_deleted = True
        headquarter.deleted_at = timezone.now()
        headquarter.save()

        # Schedule the permanent deletion task for 5 days from now
        scheduled_date = timezone.now() + timedelta(days=5)
        models.HeadquarterDeletionAudit.objects.create(
            headquarter_id=headquarter.id,
            headquarter_name=headquarter.name,
            company_id=headquarter.company_id or 0,
            requested_by_user_id=request.user.id,
            requested_by_user_email=request.user.email,
            scheduled_deletion_date=scheduled_date
        )

        permanently_delete_headquarter_task.apply_async(
            args=[headquarter.id],
            eta=scheduled_date
        )

        return Response(
            {'success': 'La sede ha sido programada para eliminación. Se borrará permanentemente junto con todos sus servicios y dependencias asociadas en 5 días.'},
            status=status.HTTP_200_OK
        )


class GetHeadquarterWeekConfiguration(viewsets.ViewSet):
    """Returns the current weekly time configuration of a headquarter."""

    authentication_classes = [TokenAuthentication]

    DAY_MAPPING_REVERSE = {
        'lunes': 'monday',
        'martes': 'tuesday',
        'miercoles': 'wednesday',
        'jueves': 'thursday',
        'viernes': 'friday',
        'sabado': 'saturday',
        'domingo': 'sunday',
    }

    def retrieve(self, request: Request, pk=None, *args, **kwargs):
        headquarter = get_owned_object(models.Headquarter, pk, request.user)
        if not headquarter:
            return not_found_response(
                'Sede no encontrada o no tienes permiso para verla.'
            )

        hq_configs = models.HeadquaterWeekDayTimeConfiguration.objects.filter(
            headquarter=headquarter
        ).select_related(
            'week_day_time_configuration__week_day',
        ).prefetch_related(
            'week_day_time_configuration__hour_week_day_time_configuration'
        )

        day_ranges: dict[str, list[str]] = {}
        for hq_config in hq_configs:
            wdtc = hq_config.week_day_time_configuration
            day_code = wdtc.week_day.code
            english_day = self.DAY_MAPPING_REVERSE.get(day_code, day_code)

            for hour_config in wdtc.hour_week_day_time_configuration.all():
                start = str(hour_config.start_time)[:5]
                end = str(hour_config.end_time)[:5]
                time_range = f"{start}-{end}"

                if english_day not in day_ranges:
                    day_ranges[english_day] = []
                if time_range not in day_ranges[english_day]:
                    day_ranges[english_day].append(time_range)

        schedule = {
            day: ';'.join(ranges)
            for day, ranges in day_ranges.items()
            if ranges
        }

        return Response({'success': schedule}, status=status.HTTP_200_OK)


class HeadquarterDetailView(viewsets.ViewSet):
    """Retorna el detalle completo de una sede."""

    authentication_classes = [TokenAuthentication]

    def retrieve(self, request: Request, pk=None, *args, **kwargs):
        headquarter = models.Headquarter.objects.filter(pk=pk).select_related(
            'company'
        ).first()

        if not headquarter:
            return Response(
                {'error': 'Sede no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = serializers.HeadquarterDetailSerializer(
            headquarter, context={'request': request}
        )
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)
