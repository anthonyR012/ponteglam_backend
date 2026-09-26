from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from core.models import MobileAppLog

@shared_task(name='core.tasks.cleanup_mobile_logs')
def cleanup_mobile_logs():
    """Elimina logs de la aplicación móvil con más de 30 días de antigüedad."""
    threshold_date = timezone.now() - timedelta(days=30)
    deleted_count, _ = MobileAppLog.objects.filter(created_at__lt=threshold_date).delete()
    return f"Se eliminaron {deleted_count} logs antiguos."
