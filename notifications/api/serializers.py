from rest_framework import serializers

from notifications import models

_DT_FORMAT = '%Y-%m-%dT%H:%M:%S%z'


class RegisterFcmTokenSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate_token(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('token is required')
        return value


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Notification
        fields = ['id', 'title', 'body', 'image', 'created_at']


class UserNotificationSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='notification.title')
    go_to = serializers.CharField(source='notification.go_to')
    data = serializers.JSONField(source='notification.data')
    body = serializers.CharField(source='notification.body')
    image = serializers.CharField(source='notification.image')
    created_at = serializers.DateTimeField(
        source='notification.created_at', format=_DT_FORMAT
    )

    class Meta:
        model = models.UserNotification
        fields = [
            'id', 'title', 'body', 'image', 'go_to', 'data',
            'created_at', 'is_read', 'read_at', 'recipient_type',
        ]
