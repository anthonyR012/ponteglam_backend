# Third-party Libraries
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from django.conf import settings

# Local Modules
from core.utils import get_local_time
from workers import models
from workers.availability import (
    compute_available_slots, get_service_duration, group_slots_response
)
from workers.api import serializers
from core.permissions import (
    verify_headquarter_ownership, ownership_denied_response, not_found_response
)
from headquarters.models import (
    Headquarter, HeadquarterWorker
)
from users.models import User
from services.models import WorkerService, AppointmentService, Service
from notifications.tasks import _create_in_app_notification


class CreateWorker(viewsets.ModelViewSet):
    serializer_class = serializers.WorkerSerializer
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        data['created_by_user_id'] = request.user.pk

        worker = models.Worker.objects.filter(
            user_id=data['user']
        ).first()

        serializer = self.serializer_class(instance=worker, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        head_quarter_id = data.get('head_quarter')
        if head_quarter_id:
            worker_hq, _ = HeadquarterWorker.objects.get_or_create(
                worker=serializer.instance,
                headquarter_id=head_quarter_id,
                defaults={
                    'created_by_user_id': request.user.pk
                }
            )
            worker_hq.save()

        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED
        )


class ListWorkers(viewsets.ModelViewSet):

    queryset = models.Worker.objects.all().order_by('-created_at')
    serializer_class = serializers.WorkerFlatSerializer
    authentication_classes = [TokenAuthentication]

    def list(self, request: Request, *args, **kwargs):
        head_quarter_id = request.GET.get('head_quarter_id')
        service_id = request.GET.get('service_id')

        queryset = self.filter_queryset(self.get_queryset())

        if head_quarter_id:
            queryset = queryset.filter(
                headquarter_worker__headquarter_id=head_quarter_id
            )

        if service_id:
            queryset = queryset.filter(
                worker_service__service_id=service_id,
                worker_service__is_pending_removal=False
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                'success': serializer.data
            }
        )


class ListAvailableSlots(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]

    def list(self, request, *args, **kwargs):
        service_id = request.GET.get('service_id')
        date_str = request.GET.get('date')
        worker_id = request.GET.get('worker_id')
        head_quarter_id = request.GET.get('head_quarter_id')

        try:
            days = int(request.GET.get('days', 15))
        except ValueError:
            days = 15

        if days > 30:
            days = 30

        if not service_id:
            return Response(
                {'error': 'service_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if date_str:
            try:
                start_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            start_date = timezone.localdate()

        try:
            service = Service.objects.get(pk=service_id)
        except Service.DoesNotExist:
            return Response(
                {'error': 'Service not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        worker_qs = WorkerService.objects.filter(
            service=service,
            is_pending_removal=False
        ).select_related('worker')
        if worker_id:
            worker_qs = worker_qs.filter(worker_id=worker_id)

        grouped = compute_available_slots(
            service=service,
            workers=[ws.worker for ws in worker_qs],
            start_date=start_date,
            days=days,
            duration=get_service_duration(service),
            headquarter_id=head_quarter_id,
            client=request.user,
        )

        serializer = serializers.AvailableDateWithSlotsSerializer(
            group_slots_response(grouped), many=True
        )
        return Response(
            {'success': serializer.data}, status=status.HTTP_200_OK
        )


class WorkerAvailabilityView(viewsets.ViewSet):
    """Configura y consulta la disponibilidad semanal de un trabajador."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request: Request, *args, **kwargs):
        """GET: Retorna la disponibilidad del trabajador autenticado."""
        worker = models.Worker.objects.filter(user=request.user).first()
        if not worker:
            return Response(
                {'error': 'No tienes un perfil de trabajador.'},
                status=status.HTTP_404_NOT_FOUND
            )

        availabilities = models.WorkerAvailability.objects.filter(worker=worker)
        serializer = serializers.WorkerAvailabilitySerializer(availabilities, many=True)
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)

    def create(self, request: Request, *args, **kwargs):
        """
        POST: Configura la disponibilidad semanal del trabajador.
        Reemplaza toda la disponibilidad existente.

        Body: lista de objetos con weekday (0-6), start_time y end_time.
        Ejemplo:
        [
            {"weekday": 0, "start_time": "08:00", "end_time": "17:00"},
            {"weekday": 1, "start_time": "09:00", "end_time": "18:00"}
        ]
        """
        worker = models.Worker.objects.filter(user=request.user).first()
        if not worker:
            return Response(
                {'error': 'No tienes un perfil de trabajador.'},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data
        if not isinstance(data, list):
            return Response(
                {'error': 'Se espera una lista de disponibilidades.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = serializers.WorkerAvailabilitySerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        # Reemplazar disponibilidad existente
        models.WorkerAvailability.objects.filter(worker=worker).delete()

        availabilities = [
            models.WorkerAvailability(
                worker=worker,
                weekday=item['weekday'],
                start_time=item['start_time'],
                end_time=item['end_time'],
            )
            for item in serializer.validated_data
        ]
        models.WorkerAvailability.objects.bulk_create(availabilities)

        result = models.WorkerAvailability.objects.filter(worker=worker)
        return Response(
            {'success': serializers.WorkerAvailabilitySerializer(result, many=True).data},
            status=status.HTTP_201_CREATED
        )


class ScheduledAppointmentsViewSet(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]

    def list(self, request, *args, **kwargs):
        fecha_inicio_str = request.GET.get('fecha_inicio')
        fecha_fin_str = request.GET.get('fecha_fin')

        now = timezone.now()

        if not fecha_inicio_str and not fecha_fin_str:
            fecha_inicio = now
            fecha_fin = now + timedelta(days=5)
        else:
            if fecha_inicio_str:
                try:
                    fecha_inicio = self.parse_datetime_param(fecha_inicio_str)
                except ValueError:
                    return Response(
                        {'error': 'Formato inválido para fecha_inicio. Use YYYY-MM-DD o YYYY-MM-DD HH:MM:SS'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                fecha_inicio = now

            if fecha_fin_str:
                try:
                    fecha_fin = self.parse_datetime_param(fecha_fin_str, end_of_day=True)
                except ValueError:
                    return Response(
                        {'error': 'Formato inválido para fecha_fin. Use YYYY-MM-DD o YYYY-MM-DD HH:MM:SS'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                fecha_fin = fecha_inicio + timedelta(days=5)

        if fecha_inicio > fecha_fin:
            return Response(
                {'error': 'fecha_inicio no puede ser mayor que fecha_fin'},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointments = AppointmentService.objects.filter(
            start_time__gte=fecha_inicio,
            start_time__lte=fecha_fin
        ).select_related(
            'appointment',
            'service',
            'worker',
            'worker__user',
            'appointment__state',
        ).order_by('start_time')

        serializer = serializers.ScheduledAppointmentSerializer(appointments, many=True)

        return Response({
            'success': True,
            'filters': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'total': appointments.count()
            },
            'data': serializer.data
        })


class StaffManagementViewSet(viewsets.ViewSet):
    """
    Módulo administrativo para gestión de staff de la sede.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='list-staff/(?P<headquarter_id>[0-9]+)')
    def list_staff(self, request, headquarter_id=None):
        """Lista los trabajadores vinculados a una sede específica."""
        if not verify_headquarter_ownership(headquarter_id, request.user):
            return ownership_denied_response(
                'No tienes permiso para ver el staff de esta sede.'
            )

        workers_ids = HeadquarterWorker.objects.filter(
            headquarter_id=headquarter_id
        ).values_list('worker_id', flat=True)

        workers = models.Worker.objects.filter(id__in=workers_ids).select_related('user')
        serializer = serializers.StaffMemberSerializer(workers, many=True, context={'request': request})
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='onboard')
    def onboard(self, request):
        """Invita a un usuario o crea un trabajador anónimo."""
        serializer = serializers.OnboardWorkerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        headquarter_id = data['headquarter_id']
        is_anonymous = data['is_anonymous']

        if not verify_headquarter_ownership(headquarter_id, request.user):
            return ownership_denied_response(
                'No tienes permiso para gestionar staff en esta sede.'
            )
        
        if is_anonymous:
            # Crear trabajador anónimo
            worker = models.Worker.objects.create(
                name=data['name'],
                created_by_user_id=request.user.id
            )
            HeadquarterWorker.objects.create(
                worker=worker,
                headquarter_id=headquarter_id,
                created_by_user_id=request.user.id
            )
            return Response({'message': 'Trabajador anónimo creado.', 'worker_id': worker.id}, status=status.HTTP_201_CREATED)
        else:
            # Flujo de invitación
            email = data.get('email')
            phone = data.get('phone')
            
            # Buscar si el usuario ya existe
            invited_user = User.objects.filter(Q(email=email) | Q(phone_number=phone)).first()
            
            invitation = models.WorkerInvitation.objects.create(
                email=email,
                phone=phone,
                headquarter_id=headquarter_id,
                invited_user=invited_user,
                created_by_user_id=request.user.id
            )
            
            if invited_user:
                # Notificación in-app al usuario
                _create_in_app_notification(
                    title="Invitación a unirte a un equipo 🤝",
                    body=f"Has sido invitado a trabajar en la sede {invitation.headquarter.name}.",
                    user_id=invited_user.id,
                    go_to='worker_invitations',
                    created_by_user_id=request.user.id
                )
            
            return Response({'message': 'Invitación enviada.', 'invitation_id': invitation.id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='link-service')
    def link_service(self, request, pk=None):
        """Vincula un trabajador a un servicio."""
        worker = models.Worker.objects.filter(pk=pk).first()
        if not worker:
            return not_found_response('Trabajador no encontrado.')

        hq_link = HeadquarterWorker.objects.filter(worker=worker).first()
        if not hq_link or not verify_headquarter_ownership(hq_link.headquarter_id, request.user):
            return ownership_denied_response(
                'No tienes permiso para gestionar este trabajador.'
            )

        service_id = request.data.get('service_id')
        if not service_id:
            return Response({'error': 'service_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
            
        link, created = WorkerService.objects.get_or_create(
            worker=worker,
            service_id=service_id,
            defaults={'created_by_user_id': request.user.id}
        )
        if not created:
            link.is_pending_removal = False
            link.removal_date = None
            link.save()
        return Response({'message': 'Servicio vinculado correctamente.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='unlink-service')
    def unlink_service(self, request, pk=None):
        """Desvincula un trabajador de un servicio validando citas pendientes."""
        worker = models.Worker.objects.filter(pk=pk).first()
        if not worker:
            return not_found_response('Trabajador no encontrado.')

        hq_link = HeadquarterWorker.objects.filter(worker=worker).first()
        if not hq_link or not verify_headquarter_ownership(hq_link.headquarter_id, request.user):
            return ownership_denied_response(
                'No tienes permiso para gestionar este trabajador.'
            )

        service_id = request.data.get('service_id')
        if not service_id:
            return Response({'error': 'service_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validar que al menos quede otro trabajador vinculado al servicio
        other_workers_count = WorkerService.objects.filter(
            service_id=service_id,
            is_pending_removal=False
        ).exclude(worker=worker).count()

        if other_workers_count == 0:
            return Response(
                {'error': 'No puedes desvincular al único trabajador asociado a este servicio. Añade otro trabajador primero.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar citas pendientes
        pending_appointments = AppointmentService.objects.filter(
            worker=worker,
            service_id=service_id,
            appointment__status__in=['pending', 'active']
        ).order_by('-end_time')
        if pending_appointments.exists():
            last_appt = pending_appointments.first()
            
            # Marcar para desvinculación diferida
            ws_link = WorkerService.objects.filter(worker=worker, service_id=service_id).first()
            if ws_link:
                ws_link.is_pending_removal = True
                ws_link.removal_date = last_appt.end_time
                ws_link.save()
            
            # Formatear la fecha/hora local para el mensaje
            local_time = get_local_time(last_appt.end_time, settings.TIME_ZONE)
            date_str = local_time.strftime('%Y-%m-%d %H:%M')

            return Response({
                'message': 'El trabajador ha sido marcado para desvinculación diferida.',
                'status': 'pending_removal',
                'effective_date': last_appt.end_time,
                'detail': f"No se aceptarán más citas nuevas. La vinculación se eliminará automáticamente tras su última cita el {date_str}."
            }, status=status.HTTP_202_ACCEPTED)
            
        WorkerService.objects.filter(worker=worker, service_id=service_id).delete()
        return Response({'message': 'Servicio desvinculado exitosamente.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='remove-from-hq')
    def remove_from_hq(self, request, pk=None):
        """Desvincula a un trabajador de la sede por completo."""
        worker = models.Worker.objects.filter(pk=pk).first()
        if not worker:
            return not_found_response('Trabajador no encontrado.')

        headquarter_id = request.data.get('headquarter_id')
        if not headquarter_id:
            return Response({'error': 'headquarter_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        if not verify_headquarter_ownership(headquarter_id, request.user):
            return ownership_denied_response(
                'No tienes permiso para gestionar staff en esta sede.'
            )
            
        # Validar citas pendientes en cualquier servicio de esta sede
        pending = AppointmentService.objects.filter(
            worker=worker,
            service__headquarter_service__headquarter_id=headquarter_id,
            appointment__status__in=['pending', 'active']
        ).exists()
        
        if pending:
            return Response({'error': 'El trabajador tiene citas pendientes en esta sede y no puede ser retirado aún.'}, status=status.HTTP_400_BAD_REQUEST)
            
        HeadquarterWorker.objects.filter(worker=worker, headquarter_id=headquarter_id).delete()
        # Limpiar también vínculos a servicios de esta sede
        WorkerService.objects.filter(worker=worker, service__headquarter_service__headquarter_id=headquarter_id).delete()
        
        return Response({'message': 'Trabajador retirado de la sede exitosamente.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='add-block')
    def add_block(self, request, pk=None):
        """Bloquea un rango de tiempo para el trabajador si no hay citas."""
        worker = models.Worker.objects.filter(pk=pk).first()
        if not worker:
            return not_found_response('Trabajador no encontrado.')

        hq_link = HeadquarterWorker.objects.filter(worker=worker).first()
        if not hq_link or not verify_headquarter_ownership(hq_link.headquarter_id, request.user):
            return ownership_denied_response(
                'No tienes permiso para gestionar este trabajador.'
            )

        data = request.data.copy()
        data['created_by_user_id'] = request.user.id
        data['worker'] = worker.id

        serializer = serializers.WorkerBlockSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        start = serializer.validated_data['start_time']
        end = serializer.validated_data['end_time']
        
        # Validar solapamiento con citas
        overlap_appt = AppointmentService.objects.filter(
            worker=worker,
            start_time__lt=end,
            end_time__gt=start,
            appointment__status__in=['pending', 'active']
        ).first()
        
        if overlap_appt:
            # Formatear la fecha/hora para informar al proveedor
            local_time = get_local_time(overlap_appt.start_time, settings.TIME_ZONE)
            date_str = local_time.strftime('%d/%m/%Y')
            time_str = local_time.strftime('%I:%M %p')
            
            return Response({'error': f'El usuario tiene una reserva pendiente para el {date_str} a las {time_str}, verifique otras opciones.'}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer.save()
        return Response({'success': serializer.data}, status=status.HTTP_201_CREATED)


class UserInvitationViewSet(viewsets.ViewSet):
    """Permite al usuario aceptar o rechazar invitaciones de trabajo."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        invitations = models.WorkerInvitation.objects.filter(invited_user=request.user, status='pending')
        serializer = serializers.WorkerInvitationSerializer(invitations, many=True)
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        invitation = models.WorkerInvitation.objects.get(pk=pk, invited_user=request.user)
        response = request.data.get('response') # 'accept' or 'reject'
        
        if response == 'accept':
            invitation.status = 'accepted'
            invitation.save()
            
            # Crear Worker y HeadquarterWorker
            worker, _ = models.Worker.objects.get_or_create(
                user=request.user,
                defaults={'created_by_user_id': request.user.id}
            )
            HeadquarterWorker.objects.get_or_create(
                worker=worker,
                headquarter=invitation.headquarter,
                defaults={'created_by_user_id': request.user.id}
            )
            return Response({'message': 'Invitación aceptada. Ahora eres parte del equipo.'}, status=status.HTTP_200_OK)
        else:
            invitation.status = 'rejected'
            invitation.save()
            return Response({'message': 'Invitación rechazada.'}, status=status.HTTP_200_OK)
