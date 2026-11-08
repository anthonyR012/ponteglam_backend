"""
File for the API views of the services application
"""

# Python Standard Library
from datetime import timedelta
import decimal

# Third-party Libraries
from django.core.cache import cache
from django.db.models import Q, Count, Sum
from rest_framework import status, viewsets
from rest_framework.authentication import (
    BasicAuthentication, TokenAuthentication
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings

# Local Modules
from django.db import transaction
from headquarters.api.serializers import HeadquarterWithServicesSerializer
from headquarters.models import Headquarter, HeadquarterService
from core import models as core_models
from core import utils
from services import models
from services.api import serializers
from services.tasks import permanently_delete_service_task
from notifications import tasks as notification_tasks
from transactions import models as transaction_models
from workers.models import Worker
from services.api.serializers import CreateServiceSerializer
from headquarters.models import HeadquarterWorker
from notifications.tasks import _create_in_app_notification
from core.permissions import get_owned_object, get_user_object, not_found_response


class CreateService(viewsets.ViewSet):

    serializer_class_service = CreateServiceSerializer
    serializer_class_file_service = serializers.ServiceFileSerializer
    status_class = status.HTTP_200_OK
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):

        data = request.data.copy()
        headquarter_id = data.get('headquarter_id')
        created_by_user_id = request.user.pk
        data['created_by_user_id'] = created_by_user_id

        # Set defaults
        if not data.get('confirmation_in'):
            data['confirmation_in'] = 10
        if not data.get('remember_in'):
            data['remember_in'] = 30
            
        if not data.get('state'):
            available_type = core_models.Type.objects.filter(
                code='available', category_type__code='status_service'
            ).first()
            if available_type:
                data['state'] = available_type.id

        # Limit to 5 services per Headquarter
        current_services_count = HeadquarterService.objects.filter(
            headquarter_id=headquarter_id
        ).count()
        if current_services_count >= 5:
            return Response(
                {'error': 'No puedes crear más de 5 servicios en esta sede.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        additional_service_image = data.getlist('service_image') if hasattr(data, 'getlist') else data.get('service_image', [])
        if len(additional_service_image) < 3:
            return Response(
                {'error': 'Debes enviar al menos 3 imágenes para el servicio.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        amenities = data.getlist('amenities') if hasattr(data, 'getlist') else data.get('amenities', [])
        if len(amenities) > 7:
            return Response(
                {'error': 'No puedes agregar más de 7 comodidades (amenities).'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = self.get_or_create_service(data)
        self.get_or_create_files(data)
        self.get_or_create_service_amenities(data, service)
        self.get_or_create_headquarter_service(service, headquarter_id, created_by_user_id)
        self.get_or_create_worker_service(service, headquarter_id, request.user)

        return Response(
            {
                'service_id': service.id
            },
            status=self.status_class
        )

    def get_or_create_service(self, data):
        service_name = data.get('name')
        created_by_user_id = data.get('created_by_user_id')

        service = models.Service.objects.filter(
            name=service_name, created_by_user_id=created_by_user_id
        ).first()

        if not service:
            serializer_service = self.serializer_class_service(data=data)
            serializer_service.is_valid(raise_exception=True)
            service = serializer_service.save()
            self.status_class = status.HTTP_201_CREATED

        data['service'] = service.id
        return service

    def get_or_create_files(self, data: Request):

        type_file_service_image = \
            core_models.Type.objects.get_type(
                code='service_image',
                category_type_code='type_file'
            )

        data_file_service = []

        service_id = data.get('service')
        additional_service_image = data.getlist('service_image') if hasattr(data, 'getlist') else data.get('service_image', [])
        created_by_user_id = data.get('created_by_user_id')

        for image in additional_service_image:

            data_file_service.append(
                {
                    'service': service_id,
                    'type': type_file_service_image.id,
                    'file': image,
                    'created_by_user_id': created_by_user_id
                }
            )

        if data_file_service:
            serializer_file_service = self.serializer_class_file_service(
                data=data_file_service, many=True
            )
            serializer_file_service.is_valid(raise_exception=True)
            serializer_file_service.save()

    def get_or_create_service_amenities(self, data, service):
        amenities = data.getlist('amenities') if hasattr(data, 'getlist') else data.get('amenities', [])
        created_by_user_id = data.get('created_by_user_id')

        for amenity_id in amenities:
            if not amenity_id:
                continue
            exists_amenity = models.ServiceAmenity.objects.filter(
                service=service, amenity_id=amenity_id
            ).exists()

            if not exists_amenity:
                models.ServiceAmenity.objects.create(
                    service=service,
                    amenity_id=amenity_id,
                    created_by_user_id=created_by_user_id
                )

    def get_or_create_headquarter_service(self, service, headquarter, created_by_user_id):

        HeadquarterService.objects.get_or_create(
            headquarter_id=headquarter, service=service,
            defaults={'created_by_user_id': created_by_user_id}
        )

    def get_or_create_worker_service(self, service, headquarter_id, user):

        worker, _ = Worker.objects.get_or_create(
            user=user,
            defaults={'created_by_user_id': user.id}
        )
        models.WorkerService.objects.get_or_create(
            worker=worker,
            service=service,
            defaults={'created_by_user_id': user.id}
        )
        HeadquarterWorker.objects.get_or_create(
            worker=worker,
            headquarter_id=headquarter_id,
            defaults={'created_by_user_id': user.id}
        )


class UpdateService(viewsets.ViewSet):

    serializer_class_service = CreateServiceSerializer
    authentication_classes = [TokenAuthentication]

    def update(self, request: Request, pk=None, *args, **kwargs):
        service = get_owned_object(models.Service, pk, request.user)
        if not service:
            return not_found_response(
                'Servicio no encontrado o no tienes permiso para editarlo.'
            )

        data = request.data.copy()

        # Check amenities limit
        amenities = data.getlist('amenities') if hasattr(data, 'getlist') else data.get('amenities', [])
        if len(amenities) > 7:
            return Response(
                {'error': 'No puedes agregar más de 7 comodidades (amenities).'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update Service instance
        serializer = self.serializer_class_service(service, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Update Images if provided
        additional_service_image = data.getlist('service_image') if hasattr(data, 'getlist') else data.get('service_image', [])

        if additional_service_image:
            if len(additional_service_image) < 3:
                return Response(
                    {'error': 'Debes enviar al menos 3 imágenes para el servicio.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Delete old images (related_name='service_file')
            service.service_file.all().delete()
            # Create new ones
            type_file_service_image = core_models.Type.objects.get_type(
                code='service_image',
                category_type_code='type_file'
            )
            data_file_service = []
            for image in additional_service_image:
                data_file_service.append({
                    'service': service.id,
                    'type': type_file_service_image.id,
                    'file': image,
                    'created_by_user_id': request.user.pk
                })

            serializer_file_service = serializers.ServiceFileSerializer(
                data=data_file_service, many=True
            )
            serializer_file_service.is_valid(raise_exception=True)
            serializer_file_service.save()

        # Update Amenities if provided
        amenities = data.getlist('amenities') if hasattr(data, 'getlist') else data.get('amenities', [])
        if amenities:
            # Refresh amenities
            models.ServiceAmenity.objects.filter(service=service).delete()
            for amenity_id in amenities:
                if not amenity_id:
                    continue
                models.ServiceAmenity.objects.create(
                    service=service,
                    amenity_id=amenity_id,
                    created_by_user_id=request.user.pk
                )

        return Response(
            {
                'message': 'Servicio actualizado correctamente',
                'service_id': service.id
            },
            status=status.HTTP_200_OK
        )


class ServiceDetailView(viewsets.ViewSet):
    """Retorna el detalle completo de un servicio por ID."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def retrieve(self, request: Request, pk=None, *args, **kwargs):
        try:
            service = models.Service.objects.get(pk=pk)
        except models.Service.DoesNotExist:
            return Response(
                {'error': 'Servicio no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = serializers.ServiceDetailSerializer(
            service, context={'request': request}
        )
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)


class DeleteService(viewsets.ViewSet):
    """Permite al proveedor eliminar su propio servicio con borrado diferido."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def destroy(self, request: Request, pk=None, *args, **kwargs):
        service = get_owned_object(models.Service, pk, request.user)
        if not service:
            return not_found_response(
                'Servicio no encontrado o no tienes permiso para eliminarlo.'
            )

        active_appointments = models.AppointmentService.objects.filter(
            service=service,
            appointment__status__in=[
                models.Appointment.STATUS_PENDING,
                models.Appointment.STATUS_ACTIVE,
            ]
        ).exists()

        if active_appointments:
            return Response(
                {'error': 'No puedes eliminar un servicio con citas pendientes o activas.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Soft-delete the service immediately from active listings
        service.is_deleted = True
        service.deleted_at = timezone.now()
        service.save()

        # Schedule the permanent deletion task for 5 days from now
        scheduled_date = timezone.now() + timedelta(days=5)
        models.ServiceDeletionAudit.objects.create(
            service_id=service.id,
            service_name=service.name,
            requested_by_user_id=request.user.id,
            requested_by_user_email=request.user.email,
            scheduled_deletion_date=scheduled_date
        )

        permanently_delete_service_task.apply_async(
            args=[service.id],
            eta=scheduled_date
        )

        return Response(
            {'success': 'El servicio ha sido programado para eliminación. Se borrará permanentemente en 5 días.'},
            status=status.HTTP_200_OK
        )


class ServiceStatsView(viewsets.ViewSet):
    """Retorna estadísticas de un servicio para el proveedor."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def retrieve(self, request: Request, pk=None, *args, **kwargs):
        service = get_owned_object(models.Service, pk, request.user)
        if not service:
            return not_found_response("Servicio no encontrado o no tienes permiso para verlo.")

        appointment_services = models.AppointmentService.objects.filter(
            service=service
        ).select_related('appointment')

        total = appointment_services.count()
        pending = appointment_services.filter(
            appointment__status=models.Appointment.STATUS_PENDING
        ).count()
        active = appointment_services.filter(
            appointment__status=models.Appointment.STATUS_ACTIVE
        ).count()
        completed = appointment_services.filter(
            appointment__status=models.Appointment.STATUS_COMPLETED
        ).count()
        cancelled = appointment_services.filter(
            appointment__status=models.Appointment.STATUS_CANCELLED
        ).count()

        total_revenue = models.Appointment.objects.filter(
            appointment_service__service=service,
            status=models.Appointment.STATUS_COMPLETED
        ).aggregate(total=Sum('price'))['total'] or 0

        hq_service = service.headquarter_service.first()
        rating = hq_service.rating if hq_service else 0
        rating_count = hq_service.rating_count if hq_service else 0

        return Response({
            'success': {
                'service_id': service.id,
                'service_name': service.name,
                'price': str(service.price),
                'rating': rating,
                'rating_count': rating_count,
                'appointments': {
                    'total': total,
                    'pending': pending,
                    'active': active,
                    'completed': completed,
                    'cancelled': cancelled,
                },
                'total_revenue': str(total_revenue),
            }
        }, status=status.HTTP_200_OK)


class CreateAppointment(viewsets.ViewSet):

    serializer_class = serializers.CreateAppointmentSerializer
    authentication_classes = [TokenAuthentication]

    @transaction.atomic
    def create(self, request: Request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        service_id = data.get('service_id')
        worker_id = data.get('worker_id')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        remember_in = data.get('remember_in')
        confirmation_in = data.get('confirmation_in')
        payment_method = data.get('payment_method', 'card')
        is_home_service = data.get('is_home_service', False)
        home_address_id = data.get('home_address_id')

        now = timezone.now()
        
        # Check for debt in wallet
        wallet, _ = transaction_models.Wallet.objects.get_or_create(
            user=request.user, 
            defaults={'created_by_user_id': request.user.id}
        )
        if wallet.balance < 0:
            formatted_debt = utils.format_currency(abs(wallet.balance))
            return Response(
                {
                    'detail': (
                        f'Tienes una deuda pendiente de {formatted_debt}. '
                        'Debes saldarla desde tu billetera antes de agendar nuevas citas.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if start_time <= now + timedelta(minutes=5):
            return Response(
                {'detail': 'La cita debe programarse con al menos 5 minutos de antelación.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        MAX_ACTIVE_APPOINTMENTS = 6
        active_count = models.Appointment.objects.filter(
            user=request.user,
            status__in=[
                models.Appointment.STATUS_PENDING,
                models.Appointment.STATUS_ACTIVE,
            ],
        ).count()
        if active_count >= MAX_ACTIVE_APPOINTMENTS:
            return Response(
                {
                    'detail': (
                        f'Has alcanzado el límite de'
                        f' {MAX_ACTIVE_APPOINTMENTS} citas activas.'
                        f' Completa o cancela alguna para'
                        f' poder agendar una nueva.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not confirmation_in:
            # Deadline para confirmar: 30 min desde ahora, o el inicio de la cita (lo que pase primero)
            confirmation_in = min(now + timedelta(minutes=30), start_time)
        if not remember_in:
            # Recordatorio: 30 min antes, o ahora mismo + 1 min si es muy pronto
            remember_in = max(now + timedelta(minutes=1), start_time - timedelta(minutes=30))

        service = models.Service.objects.filter(pk=service_id).first()
        if not service:
            return Response(
                {'detail': 'Service not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if is_home_service:
            from users.models import UserAddress
            home_address = UserAddress.objects.filter(
                id=home_address_id,
                user=request.user,
            ).first()
            if not home_address:
                return Response(
                    {'detail': 'Address not found or does not belong to user.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            home_address = None

        # Check for user overlap (don't allow two appointments at once for the same client)
        user_overlap = models.AppointmentService.objects.filter(
            appointment__user=request.user,
            start_time__lt=end_time,
            end_time__gt=start_time,
            appointment__status__in=[
                models.Appointment.STATUS_PENDING,
                models.Appointment.STATUS_ACTIVE
            ]
        ).exists()

        if user_overlap:
            return Response(
                {'detail': 'Ya tienes otra cita programada o en curso en este horario.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        final_price = service.price
        if (
            is_home_service
            and service.only_home_service
            and service.home_service_price
            and service.home_service_price > 0
        ):
            final_price = service.price + service.home_service_price

        addon_ids = data.get('addon_ids', [])
        valid_addons = []
        if addon_ids:
            from addons.models import ServiceAddonLink
            for addon_id in addon_ids:
                link = ServiceAddonLink.objects.filter(
                    addon_id=addon_id,
                    service_id=service_id,
                ).first()
                if not link:
                    continue
                valid_addons.append(link.addon)
                final_price += link.addon.price

        overlap = models.AppointmentService.objects.filter(
            worker_id=worker_id,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(
            appointment__status=models.Appointment.STATUS_CANCELLED
        ).exists()

        if overlap:
            return Response(
                {'detail': 'El trabajador no está disponible en ese horario.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        duplicate = models.AppointmentService.objects.filter(
            worker_id=worker_id,
            appointment__user=request.user,
            start_time=start_time,
        ).exclude(
            appointment__status=models.Appointment.STATUS_CANCELLED
        ).exists()

        if duplicate:
            return Response(
                {'detail': 'Ya tienes una reserva con este trabajador en ese horario.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        category, _ = core_models.Category.objects.get_or_create(
            code='status_appointment',
            defaults={
                'description': 'Categoría para los diferentes estados de las citas',
                'created_by_user_id': request.user.id
            }
        )

        pending_type, _ = core_models.Type.objects.get_or_create(
            code='pending_payment', category_type=category,
            defaults={
                'description': 'Pendiente de Pago',
                'created_by_user_id': request.user.id
            }
        )

        appointment = models.Appointment.objects.create(
            confirmation_in=confirmation_in,
            remember_in=remember_in,
            price=final_price,
            state=pending_type,
            status=models.Appointment.STATUS_PENDING,
            payment_method=payment_method,
            is_home_service=is_home_service,
            home_address=home_address,
            user=request.user,
            created_by_user_id=request.user.id
        )

        models.AppointmentService.objects.create(
            appointment=appointment,
            service_id=service_id,
            worker_id=worker_id,
            start_time=start_time,
            end_time=end_time,
            created_by_user_id=request.user.id
        )

        if valid_addons:
            from addons.models import AppointmentAddon
            for addon in valid_addons:
                AppointmentAddon.objects.create(
                    appointment=appointment,
                    addon=addon,
                    price_at_booking=addon.price,
                    duration_at_booking=addon.duration_minutes,
                    created_by_user_id=request.user.id,
                )

        try:
            _schedule_appointment_notifications(
                appointment=appointment,
                service=service,
                start_time=start_time,
                end_time=end_time,
                client_user_id=request.user.id,
            )
        except Exception as e:
            # Si Redis falla las tareas programadas fallan, pero el in-app ya fue guardado
            print(f"Error al programar notificaciones (Redis): {str(e)}")

        # Create Traceability entry
        models.TraceabilityAppointment.objects.create(
            appointment=appointment,
            previous_state=None,
            new_state=models.Appointment.STATUS_PENDING,
            change_reason='Cita creada',
            created_by_user_id=request.user.id
        )

        return Response(
            {
                'appointment_id': appointment.id,
                'detail': 'Cita creada exitosamente.'
            },
            status=status.HTTP_201_CREATED
        )


def _schedule_appointment_notifications(
    appointment, service, start_time, end_time, client_user_id
):
    """
    Notificaciones al crear una cita:
    - Inmediatas (in-app síncronas + push async): registro de nueva reserva al proveedor.
    - Programadas (Celery): recordatorios, auto-confirm en 5 min, auto-complete en end_time.
    """
    hq_service = service.headquarter_service.select_related(
        'headquarter__company'
    ).first()

    supplier_user_id = (
        hq_service.headquarter.company.created_by_user_id
        if hq_service else None
    )

    now = timezone.now()

    # 1. Notificación inmediata al proveedor — in-app síncrona (siempre se guarda en DB)
    if supplier_user_id:
        _create_in_app_notification(
            title="Nueva reserva recibida 📅",
            body=f"Tienes una nueva reserva para **{service.name}**. Revisa tu agenda.",
            user_id=supplier_user_id,
            go_to='supplier_appointments',
            created_by_user_id=client_user_id,
            company_id=hq_service.headquarter.company_id,
        )
        notification_tasks.push_booking_notification_to_supplier.delay(
            appointment_id=appointment.id,
            supplier_user_id=supplier_user_id,
            service_name=service.name,
        )

    # 2. Recordatorio al cliente
    # Solo programamos si falta más de 30 min. 
    # Si falta menos, el recordatorio será disparado por la tarea de confirmación.
    if start_time > now + timedelta(minutes=30):
        client_eta = start_time - timedelta(minutes=30)
        notification_tasks.notify_client_reminder.apply_async(
            kwargs={
                'appointment_id': appointment.id,
                'client_user_id': client_user_id,
                'service_name': service.name,
            },
            eta=client_eta,
        )

    # 3. Recordatorio al proveedor
    # Solo programamos si falta más del tiempo definido en remember_in.
    if supplier_user_id and service.remember_in:
        supplier_eta = start_time - timedelta(minutes=service.remember_in)
        if start_time > now + timedelta(minutes=service.remember_in):
            notification_tasks.notify_supplier_reminder.apply_async(
                kwargs={
                    'appointment_id': appointment.id,
                    'supplier_user_id': supplier_user_id,
                    'service_name': service.name,
                    'minutes_before': service.remember_in,
                },
                eta=supplier_eta,
            )

    # 4. Auto-confirmar si el proveedor no responde en 5 minutos
    # Pero si la cita empieza en menos de 5 min, confirmamos justo antes de empezar
    auto_confirm_eta = now + timedelta(minutes=5)
    if auto_confirm_eta > start_time:
        auto_confirm_eta = start_time - timedelta(seconds=10)

    if auto_confirm_eta > now:
        notification_tasks.auto_confirm_appointment.apply_async(
            kwargs={'appointment_id': appointment.id},
            eta=auto_confirm_eta,
        )

    # 5. Auto-completar la cita al llegar end_time
    if end_time > now:
        notification_tasks.auto_complete_appointment.apply_async(
            kwargs={'appointment_id': appointment.id},
            eta=end_time,
        )


class ConfirmCashAppointment(viewsets.ViewSet):
    """Permite al trabajador confirmar el pago en efectivo de una cita pendiente."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def partial_update(self, request: Request, pk=None, *args, **kwargs):
        worker = Worker.objects.filter(user=request.user).first()
        if not worker:
            return Response(
                {'error': 'No tienes un perfil de trabajador.'},
                status=status.HTTP_403_FORBIDDEN
            )

        appointment_service = models.AppointmentService.objects.filter(
            appointment_id=pk, worker=worker
        ).first()

        if not appointment_service:
            return Response(
                {'error': 'No eres el trabajador asignado a esta cita.'},
                status=status.HTTP_403_FORBIDDEN
            )

        appointment = appointment_service.appointment

        if appointment.payment_method != models.Appointment.PAYMENT_CASH:
            return Response(
                {'error': 'Esta cita no es de pago en efectivo.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if appointment.status != models.Appointment.STATUS_PENDING:
            return Response(
                {'error': 'Solo se pueden confirmar citas en estado pendiente.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        category, _ = core_models.Category.objects.get_or_create(
            code='status_appointment',
            defaults={
                'description': 'Categoría para los diferentes estados de las citas',
                'created_by_user_id': request.user.id
            }
        )
        active_type, _ = core_models.Type.objects.get_or_create(
            code='active', category_type=category,
            defaults={
                'description': 'Activa',
                'created_by_user_id': request.user.id
            }
        )

        previous_status = appointment.status
        appointment.status = models.Appointment.STATUS_ACTIVE
        appointment.state = active_type
        appointment.save()

        # Create Traceability entry
        models.TraceabilityAppointment.objects.create(
            appointment=appointment,
            previous_state=previous_status,
            new_state=models.Appointment.STATUS_ACTIVE,
            change_reason='Pago en efectivo confirmado por el proveedor',
            created_by_user_id=request.user.id
        )

        if appointment.user_id:
            first_service = appointment.appointment_service.first()
            service_name = first_service.service.name if first_service else "tu servicio"
            
            _create_in_app_notification(
                title="Reserva Confirmada ✅",
                body=f"El proveedor confirmó tu reserva para **{service_name}**. ¡Te esperamos!",
                user_id=appointment.user_id,
                go_to='history',
                created_by_user_id=request.user.id,
            )
            notification_tasks.push_appointment_confirmed_to_client.delay(
                appointment_id=appointment.id,
                client_user_id=appointment.user_id,
            )

        serializer = serializers.AppointmentDetailSerializer(
            appointment, context={'request': request}
        )
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)


class ListServices(viewsets.ModelViewSet):
    serializer_class = HeadquarterWithServicesSerializer
    authentication_classes = [TokenAuthentication]
    pagination_class = utils.CustomPagination
    queryset = Headquarter.objects.all().select_related('company')

    def list(self, request: Request, *args, **kwargs):
        query_page = request.query_params.get('page', 1)
        category = request.query_params.get('category')
        search = request.query_params.get('search')
        rating = request.query_params.get('rating')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        mine = request.query_params.get('mine')
        only_home_service = request.query_params.get('only_home_service')
        available_for = request.query_params.get('available_for')
        lat = request.query_params.get('latitude')
        lng = request.query_params.get('longitude')

        queryset = self.get_queryset()

        if mine == 'true':
            queryset = queryset.filter(
                created_by_user_id=request.user.pk,
                company__state__code='available'
            )
        else:
            queryset = queryset.filter(
                company__state__code='available',
                state__code='available',
                headquarter_service__service__state__code='available'
            ).distinct()

        queries = Q()
        additional_filters = {}

        if category:
            queries = queries & Q(
                headquarter_service__service__service_category=category
            )

        if search:
            queries = queries & Q(
                Q(name__icontains=search) |
                Q(headquarter_service__service__name__icontains=search) |
                Q(headquarter_service__service__description__icontains=search)
            )
            additional_filters['name__icontains'] = search
            additional_filters['description__icontains'] = search

        if rating:
            queries = queries & Q(
                headquarter_service__headquarter__rating__gte=rating
            )

        if only_home_service == 'true':
            queries = queries & Q(
                headquarter_service__service__only_home_service=True
            )
            additional_filters['only_home_service'] = True

        if available_for:
            day_ids = available_for.split(',')
            queries = queries & Q(
                headquater_week_day_time_configuration__week_day_time_configuration__week_day_id__in=day_ids
            )

        if min_price and max_price:
            additional_filters['price__range'] = (min_price, max_price)

        if queries:
            queryset = queryset.filter(queries).distinct()

        # Sort by proximity if coordinates are provided
        if lat and lng:
            try:
                user_point = (float(lat), float(lng))
                # Sort the queryset manually after fetch or using annotation if possible.
                # For simplicity and given the pagination, we'll sort the list of objects.
                # Note: This might affect large dataset pagination performance.
                # In a real production app with many HQs, we'd use PostGIS/GeoDjango.
                
                hqs_list = list(queryset)
                for hq in hqs_list:
                    hq.distance = utils.calculate_km_between_two_points(
                        user_point, (float(hq.latitude), float(hq.longitude))
                    )
                hqs_list.sort(key=lambda x: x.distance)
                
                # Re-create queryset from sorted list for pagination
                # This is a workaround since standard queryset doesn't support distance sorting without PostGIS
                queryset = hqs_list
            except (ValueError, TypeError):
                pass

        page = self.paginate_queryset(queryset)

        if page is not None:
            cache_key = (
                f'services_list_page_{query_page}_user_{request.user.pk}_'
                f'mine_{mine}_home_{only_home_service}_avail_{available_for}_'
                f'lat_{lat}_lng_{lng}_category_{category}_search_{search}_'
                f'rating_{rating}_min_{min_price}_max_{max_price}'
            )
            cached_data = cache.get(cache_key)

            if cached_data is not None:
                return self.get_paginated_response(cached_data)

            serializer = self.get_serializer(
                page, many=True, context={
                    'request': request,
                    'additional_filters': additional_filters}
            )
            cache.set(cache_key, serializer.data, timeout=50)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(
            queryset, many=True,
            context={
                'request': request,
                'category': category
            }
        )
        return Response(
            {
                'success': serializer.data
            },
            status=status.HTTP_200_OK
        )


class ListCategoriesServices(viewsets.ModelViewSet):
    serializer_class = serializers.ServiceCategorySerializer
    authentication_classes = [BasicAuthentication]
    permission_classes = [AllowAny]

    def list(self, request: Request, *args, **kwargs):
        if request.query_params.get('include_empty') == 'true':
            categories = models.ServiceCategory.objects.all()
        else:
            categories = models.ServiceCategory.objects.with_available_services()
        serializer = self.serializer_class(
            categories, many=True, context={'request': request}
        )
        data = serializer.data
        return Response(
            {
                'success': data
            },
            status=status.HTTP_200_OK
        )


class SupplierServiceAppointmentsViewSet(viewsets.ViewSet):
    """Lista las citas agrupadas por pasadas y próximas para un servicio dado, enfocado en el Proveedor."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request: Request, *args, **kwargs):
        service_id = request.query_params.get('service_id')
        if not service_id:
            return Response(
                {'error': 'service_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = get_owned_object(models.Service, service_id, request.user)
        if not service:
            return not_found_response(
                'Servicio no encontrado o no tienes permiso para ver sus citas.'
            )

        appointment_status_filter = request.query_params.get('status', 'upcoming')

        status_map = {
            'upcoming': [
                models.Appointment.STATUS_PENDING,
                models.Appointment.STATUS_ACTIVE,
            ],
            'past': [
                models.Appointment.STATUS_COMPLETED,
                models.Appointment.STATUS_CANCELLED,
            ],
        }

        statuses = status_map.get(appointment_status_filter, status_map['upcoming'])

        appointments = models.Appointment.objects.filter(
            appointment_service__service_id=service_id,
            status__in=statuses
        ).prefetch_related('appointment_service', 'traceability').order_by('-confirmation_in').distinct()

        serializer = serializers.AppointmentListSerializer(
            appointments, many=True, context={'request': request}
        )
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)


class ListAppointments(viewsets.ViewSet):
    """Lista las citas del usuario autenticado filtradas por estado."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request: Request, *args, **kwargs):
        appointment_status = (
            request.query_params.get('filter')
            or request.query_params.get('status')
            or 'active'
        )

        status_map = {
            'upcoming': [
                models.Appointment.STATUS_PENDING,
                models.Appointment.STATUS_ACTIVE,
            ],
            'completed': [models.Appointment.STATUS_COMPLETED],
            'cancelled': [models.Appointment.STATUS_CANCELLED],
            'active': [models.Appointment.STATUS_ACTIVE],
            'pending': [models.Appointment.STATUS_PENDING],
        }

        statuses = status_map.get(appointment_status, [models.Appointment.STATUS_ACTIVE])

        appointments = models.Appointment.objects.filter(
            user=request.user,
            status__in=statuses
        ).prefetch_related('appointment_service', 'traceability').order_by('-confirmation_in')

        serializer = serializers.AppointmentListSerializer(
            appointments, many=True, context={'request': request}
        )
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)


class AppointmentDetail(viewsets.ViewSet):
    """Retorna el detalle completo de una cita del usuario."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def retrieve(self, request: Request, pk=None, *args, **kwargs):
        appointment = get_user_object(models.Appointment, pk, request.user)
        if not appointment:
            return not_found_response('Cita no encontrada.')

        serializer = serializers.AppointmentDetailSerializer(
            appointment, context={'request': request}
        )
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)


class CancelAppointment(viewsets.ViewSet):
    """Cancela una cita del usuario autenticado."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def partial_update(self, request: Request, pk=None, *args, **kwargs):
        appointment = get_user_object(models.Appointment, pk, request.user)
        if not appointment:
            return not_found_response('Cita no encontrada.')

        if appointment.status not in [
            models.Appointment.STATUS_PENDING,
            models.Appointment.STATUS_ACTIVE
        ]:
            return Response(
                {'error': 'Solo puedes cancelar citas pendientes o activas.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')
        previous_status = appointment.status
        appointment.status = models.Appointment.STATUS_CANCELLED
        appointment.cancellation_reason = reason

        # Calculate cancellation fee based on requirements doc
        app_service = appointment.appointment_service.first()
        if app_service:
            # If the appointment was still PENDING, no fee is charged (as per user request)
            if previous_status == models.Appointment.STATUS_PENDING:
                fee_info = {
                    'penalty_pct': 0.0,
                    'fee_amount': 0.0,
                    'platform_commission': 0.0,
                    'refund_to_party': float(appointment.price),
                    'fee_level': 'low'
                }
            else:
                fee_info = utils.calculate_cancellation_fee(
                    appointment_start=app_service.start_time,
                    service_total=appointment.price
                )

            # 1. Store fee info in appointment
            appointment.cancellation_fee = fee_info['fee_amount']
            appointment.cancellation_fee_level = fee_info['fee_level']
            
            # 2. Create Fee record (Finance model)
            transaction_models.Fee.objects.create(
                appointment=appointment,
                penalty_pct=fee_info['penalty_pct'],
                fee_amount=fee_info['fee_amount'],
                platform_commission=fee_info['platform_commission'],
                refund_to_party=fee_info['refund_to_party'],
                fee_level=fee_info['fee_level'],
                created_by_user_id=request.user.id
            )

            # 3. Create Transaction record of type devolution (if applies for card)
            if (
                fee_info['refund_to_party'] > 0
                and appointment.payment_method == models.Appointment.PAYMENT_CARD
            ):
                transaction_models.Transaction.objects.create(
                    appointment=appointment,
                    type=transaction_models.Transaction.TYPE_DEVOLUTION,
                    amount=fee_info['refund_to_party'],
                    status='pending',
                    created_by_user_id=request.user.id
                )

            # 4. Handle Wallet movements (Debt/Credit) for Cash or Platform Balance
            if fee_info['fee_amount'] > 0:
                # User (Client) records a debt if it was cash
                if appointment.payment_method == models.Appointment.PAYMENT_CASH:
                    user_wallet = getattr(request.user, 'wallet', None)
                    if user_wallet:
                        prev_b = user_wallet.balance
                        user_wallet.balance -= decimal.Decimal(fee_info['fee_amount'])
                        user_wallet.save()
                        
                        transaction_models.WalletTransaction.objects.create(
                            wallet=user_wallet,
                            appointment=appointment,
                            type=transaction_models.WalletTransaction.TYPE_DEBT,
                            amount=fee_info['fee_amount'],
                            previous_balance=prev_b,
                            new_balance=user_wallet.balance,
                            description=f"Multa por cancelación tardía (Efectivo) - Cita #{appointment.id}",
                            created_by_user_id=request.user.id
                        )

                # Provider (Worker) records a credit for the penalty minus commission
                if app_service.worker and app_service.worker.user:
                    worker_user = app_service.worker.user
                    worker_wallet, _ = transaction_models.Wallet.objects.get_or_create(
                        user=worker_user, defaults={'created_by_user_id': 1}
                    )
                    prev_bw = worker_wallet.balance
                    # Net amount for worker = Penalty - Platform Commission
                    net_for_worker = decimal.Decimal(fee_info['fee_amount']) - decimal.Decimal(fee_info['platform_commission'])
                    
                    if net_for_worker > 0:
                        worker_wallet.balance += net_for_worker
                        worker_wallet.save()
                        
                        transaction_models.WalletTransaction.objects.create(
                            wallet=worker_wallet,
                            appointment=appointment,
                            type=transaction_models.WalletTransaction.TYPE_DEPOSIT,
                            amount=net_for_worker,
                            previous_balance=prev_bw,
                            new_balance=worker_wallet.balance,
                            description=f"Compensación por cancelación tardía de cliente - Cita #{appointment.id}",
                            created_by_user_id=request.user.id
                        )

        if appointment.payment_method == models.Appointment.PAYMENT_CARD:
            appointment.refund_pending = True

        appointment.save()

        # 5. Create Traceability entry
        models.TraceabilityAppointment.objects.create(
            appointment=appointment,
            previous_state=previous_status,
            new_state=models.Appointment.STATUS_CANCELLED,
            change_reason=reason,
            created_by_user_id=request.user.id
        )

        # Notify the other party
        notification_tasks.notify_appointment_cancelled.delay(
            appointment_id=appointment.id,
            cancelled_by_user_id=request.user.id
        )

        serializer = serializers.AppointmentDetailSerializer(
            appointment, context={'request': request}
        )
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)


class RescheduleAppointment(viewsets.ViewSet):
    """Reprograma la fecha y hora de una cita existente."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def partial_update(self, request: Request, pk=None, *args, **kwargs):
        appointment = get_user_object(models.Appointment, pk, request.user)
        if not appointment:
            return not_found_response('Cita no encontrada.')

        if appointment.status not in [
            models.Appointment.STATUS_PENDING,
            models.Appointment.STATUS_ACTIVE
        ]:
            return Response(
                {'error': 'Solo puedes reprogramar citas pendientes o activas.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = serializers.RescheduleAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_start = data['new_start_time']
        new_end = data['new_end_time']
        worker_id = data.get('worker_id')

        appointment_service = appointment.appointment_service.first()
        if not appointment_service:
            return Response(
                {'error': 'No se encontró el servicio de la cita.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Enforce Max 1 reschedule
        if appointment.reschedule_count >= 1:
            return Response(
                {'error': 'Ya has agotado el límite de 1 reprogramación para esta cita.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Enforce 10-hour notice
        if appointment_service.start_time < timezone.now() + timedelta(hours=10):
            return Response(
                {'error': 'No puedes reprogramar faltando menos de 10 horas para la cita.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        target_worker_id = worker_id or appointment_service.worker_id

        overlap = models.AppointmentService.objects.filter(
            worker_id=target_worker_id,
            start_time__lt=new_end,
            end_time__gt=new_start
        ).exclude(appointment=appointment).exists()

        if overlap:
            return Response(
                {'error': 'El trabajador no está disponible en ese horario.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment_service.start_time = new_start
        appointment_service.end_time = new_end
        if worker_id:
            appointment_service.worker_id = worker_id
        appointment_service.save()

        appointment.confirmation_in = new_start
        appointment.remember_in = new_start - timedelta(minutes=30)
        appointment.reschedule_count += 1
        appointment.save()

        # Friendly date formatting
        local_time = utils.get_local_time(new_start, settings.TIME_ZONE)
        months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", 
                  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        month_name = months[local_time.month - 1]
        time_str = local_time.strftime('%I:%M %p').lower()
        friendly_date = f"{local_time.day} de {month_name} a las {time_str}"

        # Create Traceability entry
        models.TraceabilityAppointment.objects.create(
            appointment=appointment,
            previous_state=appointment.status,
            new_state=appointment.status,
            change_reason=f'Reprogramada para el {friendly_date}',
            created_by_user_id=request.user.id
        )

        # Notify the other party
        notification_tasks.notify_appointment_rescheduled.delay(
            appointment_id=appointment.id,
            rescheduled_by_user_id=request.user.id
        )

        detail_serializer = serializers.AppointmentDetailSerializer(
            appointment, context={'request': request}
        )
        return Response({'success': detail_serializer.data}, status=status.HTTP_200_OK)


class UpdateAppointmentStatus(viewsets.ViewSet):
    """Permite al worker asignado actualizar el estado de la cita."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    ALLOWED_TRANSITIONS = {
        models.Appointment.STATUS_ACTIVE: [models.Appointment.STATUS_COMPLETED],
        models.Appointment.STATUS_PENDING: [models.Appointment.STATUS_ACTIVE],
    }

    def partial_update(self, request: Request, pk=None, *args, **kwargs):
        new_status = request.data.get('status')

        valid_statuses = [
            models.Appointment.STATUS_ACTIVE,
            models.Appointment.STATUS_COMPLETED,
        ]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Estado inválido. Valores permitidos: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        worker = Worker.objects.filter(user=request.user).first()
        if not worker:
            return Response(
                {'error': 'No tienes un perfil de trabajador.'},
                status=status.HTTP_403_FORBIDDEN
            )

        appointment_service = models.AppointmentService.objects.filter(
            appointment_id=pk, worker=worker
        ).first()

        if not appointment_service:
            return Response(
                {'error': 'No eres el trabajador asignado a esta cita.'},
                status=status.HTTP_403_FORBIDDEN
            )

        appointment = appointment_service.appointment
        allowed_next = self.ALLOWED_TRANSITIONS.get(appointment.status, [])
        if new_status not in allowed_next:
            return Response(
                {'error': f'No puedes cambiar de "{appointment.status}" a "{new_status}".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        previous_status = appointment.status
        appointment.status = new_status
        appointment.save()

        # Create Traceability entry
        models.TraceabilityAppointment.objects.create(
            appointment=appointment,
            previous_state=previous_status,
            new_state=new_status,
            change_reason=f'Estado actualizado por el proveedor',
            created_by_user_id=request.user.id
        )

        serializer = serializers.AppointmentDetailSerializer(
            appointment, context={'request': request}
        )
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)


class NearbyServices(viewsets.ViewSet):
    """Lista sedes con servicios cercanos a una ubicación geográfica."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request: Request, *args, **kwargs):
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        radius_km = float(request.query_params.get('radius_km', 10))
        category_id = request.query_params.get('category_id')

        if not latitude or not longitude:
            return Response(
                {'error': 'latitude y longitude son requeridos.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lat = float(latitude)
            lng = float(longitude)
        except ValueError:
            return Response(
                {'error': 'latitude y longitude deben ser números.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_point = (lat, lng)
        headquarters = Headquarter.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related('company').prefetch_related('headquarter_service')

        if category_id:
            headquarters = headquarters.filter(
                headquarter_service__service__service_category_id=category_id
            ).distinct()

        nearby = []
        for hq in headquarters:
            try:
                hq_point = (float(hq.latitude), float(hq.longitude))
                distance = utils.calculate_km_between_two_points(user_point, hq_point)
                if distance <= radius_km:
                    nearby.append((hq, distance))
            except (ValueError, TypeError):
                continue

        nearby.sort(key=lambda x: x[1])

        results = []
        for hq, distance in nearby:
            hq_data = HeadquarterWithServicesSerializer(
                hq, context={'request': request}
            ).data
            hq_data['distance_km'] = distance
            results.append(hq_data)

        return Response({'success': results}, status=status.HTTP_200_OK)
