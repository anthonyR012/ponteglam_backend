import logging
from celery import shared_task
from django.utils import timezone
from services.models import Service, ServiceDeletionAudit

logger = logging.getLogger(__name__)


@shared_task
def permanently_delete_service_task(service_id):
    """
    Permanently deletes a service and updates its deletion audit log.
    """
    logger.info("Starting permanent deletion for Service ID: %s", service_id)
    try:
        # Use all_objects manager to access soft-deleted service
        service = Service.all_objects.filter(id=service_id).first()
        if service:
            service_name = service.name
            service.delete()
            logger.info("Successfully permanently deleted Service: %s (ID: %s)", service_name, service_id)
        else:
            logger.warning("Service with ID: %s not found or already permanently deleted.", service_id)

        # Update the deletion audit log
        audit = ServiceDeletionAudit.objects.filter(service_id=service_id, is_permanently_deleted=False).first()
        if audit:
            audit.is_permanently_deleted = True
            audit.purged_at = timezone.now()
            audit.save()
            logger.info("Updated ServiceDeletionAudit for Service ID: %s", service_id)
    except Exception as e:
        logger.error("Error permanently deleting Service ID %s: %s", service_id, str(e))


@shared_task
def cleanup_expired_services_task():
    """
    Fallback task to permanently delete all services whose scheduled deletion date has passed.
    """
    now = timezone.now()
    logger.info("Running fallback cleanup for expired services at %s", now)
    expired_audits = ServiceDeletionAudit.objects.filter(
        scheduled_deletion_date__lte=now,
        is_permanently_deleted=False
    )

    count = 0
    for audit in expired_audits:
        try:
            service = Service.all_objects.filter(id=audit.service_id).first()
            if service:
                service.delete()
                logger.info("Fallback: permanently deleted Service ID %s", audit.service_id)
            audit.is_permanently_deleted = True
            audit.purged_at = now
            audit.save()
            count += 1
        except Exception as e:
            logger.error("Fallback: error deleting Service ID %s: %s", audit.service_id, str(e))

    return f"Cleaned up {count} expired services"
