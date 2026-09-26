from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from notifications.api import serializers
from notifications import tasks
from notifications import models
from core import utils
from fcm_django.models import FCMDevice


class ListUserNotifications(viewsets.ModelViewSet):
    serializer_class = serializers.UserNotificationSerializer
    authentication_classes = [TokenAuthentication]
    pagination_class = utils.CustomPagination
    queryset = models.UserNotification.objects.all()

    def list(self, request: Request, *args, **kwargs):
        company_id = request.query_params.get('company_id')

        if company_id:
            queryset = models.UserNotification.objects.for_supplier(
                request.user, company_id
            ).order_by('-id')
        else:
            queryset = models.UserNotification.objects.for_client(
                request.user
            ).order_by('-id')

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(
                page, many=True, context={'request': request}
            )
            # Solo marca como leídas las notificaciones de la página actual,
            # no todo el queryset.
            tasks.mark_notifications_as_read.delay([n.id for n in page])
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)


class SendPushNotificationsViewSet(viewsets.ViewSet):
    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        tasks.send_multicast_notification.delay(data)
        return Response({'success': 'Notificación enviada'}, status=status.HTTP_200_OK)


class SendAppNotificationsViewSet(viewsets.ViewSet):
    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        data['created_by_user_id'] = request.user.pk
        tasks.send_app_notification.delay(data)
        return Response({'success': 'Notificación enviada'}, status=status.HTTP_200_OK)


class CreateCampaignAppNotificationsViewSet(viewsets.ViewSet):
    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        data['created_by_user_id'] = request.user.pk
        tasks.create_campaign_app_notification.delay(data)
        return Response({'success': 'Campaña creada'}, status=status.HTTP_200_OK)


class UnreadNotificationsCountViewSet(viewsets.ViewSet):
    """Retorna el conteo de notificaciones no leídas del usuario."""

    authentication_classes = [TokenAuthentication]

    def list(self, request: Request, *args, **kwargs):
        company_id = request.query_params.get('company_id')

        if company_id:
            recipient_type = models.UserNotification.RECIPIENT_SUPPLIER
        else:
            recipient_type = models.UserNotification.RECIPIENT_USER

        count = models.UserNotification.objects.unread_count(
            user=request.user,
            recipient_type=recipient_type,
            company_id=company_id,
        )
        return Response({'count': count}, status=status.HTTP_200_OK)


class RegisterDeviceViewSet(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request: Request, *args, **kwargs):
        registration_id = request.data.get('registration_id')
        device_type = request.data.get('device_type', 'android')

        if not registration_id:
            return Response(
                {'error': 'registration_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if device_type not in ('android', 'ios', 'web'):
            return Response(
                {'error': 'device_type must be android, ios or web'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _, created = FCMDevice.objects.update_or_create(
            registration_id=registration_id,
            defaults={
                'user': request.user,
                'type': device_type,
                'active': True,
            },
        )

        return Response(
            {'success': 'Device registered'},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def destroy(self, request: Request, *args, **kwargs):
        registration_id = request.data.get('registration_id')

        if not registration_id:
            return Response(
                {'error': 'registration_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        FCMDevice.objects.filter(
            user=request.user,
            registration_id=registration_id,
        ).update(active=False)

        return Response(
            {'success': 'Device deregistered'},
            status=status.HTTP_200_OK,
        )


class RegisterFcmToken(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request: Request, *args, **kwargs):
        serializer = serializers.RegisterFcmTokenSerializer(
            data=request.data
        )
        if not serializer.is_valid():
            return Response(
                {'error': 'token is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_value = serializer.validated_data['token']
        user = request.user

        if models.DeviceToken.objects.filter(
            user=user, token=token_value
        ).exists():
            return Response(
                {'success': 'Token registered'},
                status=status.HTTP_200_OK,
            )

        existing = models.DeviceToken.objects.filter(
            token=token_value
        ).first()

        if existing:
            models.DeviceToken.objects.filter(user=user).delete()
            existing.user = user
            existing.save(update_fields=['user', 'updated_at'])
        else:
            models.DeviceToken.objects.filter(user=user).delete()
            models.DeviceToken.objects.create(
                user=user, token=token_value
            )

        return Response(
            {'success': 'Token registered'},
            status=status.HTTP_200_OK,
        )


class DeleteFcmToken(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def destroy(self, request: Request, *args, **kwargs):
        token_value = request.data.get('token')
        user = request.user

        if token_value:
            models.DeviceToken.objects.filter(
                user=user, token=token_value
            ).delete()
        else:
            models.DeviceToken.objects.filter(user=user).delete()

        return Response(
            {'success': 'Token removed'},
            status=status.HTTP_200_OK,
        )
