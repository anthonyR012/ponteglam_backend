"""
File for the API views of the ratings application
"""
import logging

from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.request import Request
from rest_framework.response import Response

from headquarters import models as hq_models
from ratings import models
from ratings.api import serializers

logger = logging.getLogger(__name__)


class CreateHeadquarterServiceRating(viewsets.ViewSet):
    """Crea una calificación para un servicio de una sede."""

    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        serializer = serializers.CreateHeadquarterServiceRatingSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        hq_service = hq_models.HeadquarterService.objects.filter(
            service_id=data['service_id']
        ).first()
        if not hq_service:
            return Response(
                {'error': 'Servicio de sede no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        from datetime import timedelta
        from django.utils import timezone

        one_year_ago = timezone.now() - timedelta(days=365)
        from services.models import AppointmentService, Appointment
        has_taken_recently = AppointmentService.objects.filter(
            service_id=data['service_id'],
            appointment__user=request.user,
            appointment__status=Appointment.STATUS_COMPLETED,
            end_time__gte=one_year_ago
        ).exists()

        if not has_taken_recently:
            return Response(
                {
                    'error': 'Debes tomar el servicio recientemente (hace menos de un año) para poder calificarlo o editar tu calificación.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        rating_obj = models.HeadquarterServiceRating.objects.filter(
            headquarter_service=hq_service,
            user=request.user
        ).first()

        if rating_obj:
            rating_obj.rating = data['rating']
            rating_obj.comment = data.get('comment', rating_obj.comment)
            rating_obj.save()
            rating = rating_obj
        else:
            rating = models.HeadquarterServiceRating.objects.create(
                headquarter_service=hq_service,
                user=request.user,
                rating=data['rating'],
                comment=data.get('comment', ''),
                created_by_user_id=request.user.pk
            )

        total = models.HeadquarterServiceRating.objects.filter(
            headquarter_service=hq_service
        )
        count = total.count()
        avg = sum(r.rating for r in total) / count if count > 0 else 0
        hq_service.rating = round(avg, 2)
        hq_service.rating_count = count
        hq_service.save()

        response_serializer = serializers.HeadquarterServiceRatingSerializer(
            rating, context={'request': request}
        )
        return Response(
            {'success': response_serializer.data},
            status=status.HTTP_201_CREATED
        )


class ListHeadquarterServiceRatings(viewsets.ViewSet):
    """Lista las calificaciones de un servicio específico de una sede."""

    authentication_classes = [TokenAuthentication]

    def list(self, request: Request, *args, **kwargs):
        service_id = request.query_params.get('service_id')
        if not service_id:
            return Response(
                {'error': 'service_id es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ratings = models.HeadquarterServiceRating.objects.filter(
            headquarter_service__service_id=service_id
        ).select_related('user').order_by('-created_at')

        serializer = serializers.HeadquarterServiceRatingSerializer(
            ratings, many=True, context={'request': request}
        )
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)


class CreateHeadquarterRating(viewsets.ViewSet):
    """Crea una calificación para una sede."""

    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        serializer = serializers.CreateHeadquarterRatingSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        headquarter = hq_models.Headquarter.objects.filter(
            pk=data['headquarter_id']
        ).first()
        if not headquarter:
            return Response(
                {'error': 'Sede no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )

        from services.models import Appointment
        appointment = Appointment.objects.filter(
            pk=data['appointment_id'],
            user=request.user,
            status=Appointment.STATUS_COMPLETED
        ).first()

        if not appointment:
            return Response(
                {'error': 'Solo puedes calificar sedes de citas completadas.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        already_rated = models.HeadquarterRating.objects.filter(
            headquarter=headquarter,
            user=request.user
        ).exists()

        if already_rated:
            return Response(
                {'error': 'Ya calificaste esta sede.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rating = models.HeadquarterRating.objects.create(
            headquarter=headquarter,
            user=request.user,
            rating=data['rating'],
            created_by_user_id=request.user.pk
        )

        all_ratings = models.HeadquarterRating.objects.filter(
            headquarter=headquarter
        )
        count = all_ratings.count()
        avg = sum(r.rating for r in all_ratings) / count if count > 0 else 0
        headquarter.rating = round(avg, 2)
        headquarter.rating_count = count
        headquarter.save()

        return Response(
            {
                'success': {
                    'id': rating.id,
                    'headquarter_id': headquarter.id,
                    'rating': rating.rating,
                    'new_avg': headquarter.rating,
                    'total_ratings': count,
                }
            },
            status=status.HTTP_201_CREATED
        )


class ListHeadquarterRatings(viewsets.ViewSet):
    """Lista las calificaciones de una sede."""

    authentication_classes = [TokenAuthentication]

    def list(self, request: Request, *args, **kwargs):
        headquarter_id = request.query_params.get('headquarter_id')
        if not headquarter_id:
            return Response(
                {'error': 'headquarter_id es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ratings = models.HeadquarterRating.objects.filter(
            headquarter_id=headquarter_id
        ).select_related('user').order_by('-created_at')

        data = [
            {
                'id': r.id,
                'user_id': r.user_id,
                'user_name': r.user.full_name or r.user.username if r.user else None,
                'rating': r.rating,
                'created_at': r.created_at,
            }
            for r in ratings
        ]

        return Response({'success': data}, status=status.HTTP_200_OK)


class ReplyHeadquarterServiceRating(viewsets.ViewSet):
    """Permite a un proveedor responder a la calificación de un usuario."""

    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        rating_id = request.data.get('rating_id')
        if not rating_id:
            return Response(
                {'error': 'rating_id es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = serializers.ReplyHeadquarterServiceRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reply_text = serializer.validated_data['reply']

        rating = models.HeadquarterServiceRating.objects.filter(pk=rating_id).first()
        if not rating:
            return Response(
                {'error': 'Calificación no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if rating.supplier_reply:
            return Response(
                {'error': 'Ya has respondido a esta calificación.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar que el usuario sea el dueño de la sede
        hq_id = rating.headquarter_service.headquarter_id
        from core.permissions import verify_headquarter_ownership
        if not verify_headquarter_ownership(hq_id, request.user):
            return Response(
                {'error': 'No tienes permisos para responder en nombre de esta sede.'},
                status=status.HTTP_403_FORBIDDEN
            )

        from django.utils import timezone
        rating.supplier_reply = reply_text
        rating.replied_at = timezone.now()
        rating.save()

        response_serializer = serializers.HeadquarterServiceRatingSerializer(
            rating, context={'request': request}
        )
        return Response({'success': response_serializer.data}, status=status.HTTP_200_OK)
