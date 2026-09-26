import logging
from celery import shared_task
from django.utils import timezone
from headquarters.models import Headquarter, HeadquarterDeletionAudit

logger = logging.getLogger(__name__)


@shared_task
def permanently_delete_headquarter_task(headquarter_id):
    """
    Permanently deletes a headquarter and updates its deletion audit log.
    """
    logger.info("Starting permanent deletion for Headquarter ID: %s", headquarter_id)
    try:
        # Use all_objects manager to access soft-deleted headquarter
        headquarter = Headquarter.all_objects.filter(id=headquarter_id).first()
        if headquarter:
            hq_name = headquarter.name
            headquarter.delete()
            logger.info("Successfully permanently deleted Headquarter: %s (ID: %s)", hq_name, headquarter_id)
        else:
            logger.warning("Headquarter with ID: %s not found or already permanently deleted.", headquarter_id)

        # Update the deletion audit log
        audit = HeadquarterDeletionAudit.objects.filter(headquarter_id=headquarter_id, is_permanently_deleted=False).first()
        if audit:
            audit.is_permanently_deleted = True
            audit.purged_at = timezone.now()
            audit.save()
            logger.info("Updated HeadquarterDeletionAudit for Headquarter ID: %s", headquarter_id)
    except Exception as e:
        logger.error("Error permanently deleting Headquarter ID %s: %s", headquarter_id, str(e))


@shared_task
def cleanup_expired_headquarters_task():
    """
    Fallback task to permanently delete all headquarters whose scheduled deletion date has passed.
    """
    now = timezone.now()
    logger.info("Running fallback cleanup for expired headquarters at %s", now)
    expired_audits = HeadquarterDeletionAudit.objects.filter(
        scheduled_deletion_date__lte=now,
        is_permanently_deleted=False
    )

    count = 0
    for audit in expired_audits:
        try:
            headquarter = Headquarter.all_objects.filter(id=audit.headquarter_id).first()
            if headquarter:
                headquarter.delete()
                logger.info("Fallback: permanently deleted Headquarter ID %s", audit.headquarter_id)
            audit.is_permanently_deleted = True
            audit.purged_at = now
            audit.save()
            count += 1
        except Exception as e:
            logger.error("Fallback: error deleting Headquarter ID %s: %s", audit.headquarter_id, str(e))

    return f"Cleaned up {count} expired headquarters"
