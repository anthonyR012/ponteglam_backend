from django.db import models
from django.utils import timezone

from core.models import MixinAudit


class Notification(MixinAudit):
    title = models.CharField(max_length=255)
    body = models.TextField()
    go_to = models.CharField(max_length=255, null=True, blank=True)
    data = models.JSONField(null=True, blank=True)
    image = models.ImageField(
        upload_to='notification_images/', null=True, blank=True)


class UserNotificationManager(models.Manager):
    def for_client(self, user):
        return self.filter(user=user, recipient_type=UserNotification.RECIPIENT_USER)

    def for_supplier(self, user, company_id):
        return self.filter(
            user=user,
            recipient_type=UserNotification.RECIPIENT_SUPPLIER,
            company_id=company_id,
        )

    def unread_count(self, user, recipient_type, company_id=None):
        qs = self.filter(user=user, is_read=False, recipient_type=recipient_type)
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs.count()


class UserNotification(MixinAudit):
    RECIPIENT_USER = 'user'
    RECIPIENT_SUPPLIER = 'supplier'
    RECIPIENT_CHOICES = [
        (RECIPIENT_USER, 'Usuario'),
        (RECIPIENT_SUPPLIER, 'Proveedor'),
    ]

    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='company_notifications',
    )
    recipient_type = models.CharField(
        max_length=10,
        choices=RECIPIENT_CHOICES,
        default=RECIPIENT_USER,
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    objects = UserNotificationManager()

    def __str__(self):
        return f'Notification: {str(self.notification)} - {str(self.user)}'

    def mark_as_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save()


class UserSubscription(models.Model):
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name="user_subscription")
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name="company_subscription")
    subscribed_at = models.DateTimeField(auto_now_add=True)


class DeviceToken(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='device_tokens',
    )
    token = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'token')

    def __str__(self):
        return f'{self.user_id} — {self.token[:20]}'
