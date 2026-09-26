import logging
from celery import shared_task
from django.utils import timezone
from companies.models import Company, CompanyDeletionAudit

logger = logging.getLogger(__name__)


@shared_task
def permanently_delete_company_task(company_id):
    """
    Permanently deletes a company and updates its deletion audit log.
    """
    logger.info("Starting permanent deletion for Company ID: %s", company_id)
    try:
        # Use all_objects manager to access soft-deleted company
        company = Company.all_objects.filter(id=company_id).first()
        if company:
            company_name = company.name
            company.delete()
            logger.info("Successfully permanently deleted Company: %s (ID: %s)", company_name, company_id)
        else:
            logger.warning("Company with ID: %s not found or already permanently deleted.", company_id)

        # Update the deletion audit log
        audit = CompanyDeletionAudit.objects.filter(company_id=company_id, is_permanently_deleted=False).first()
        if audit:
            audit.is_permanently_deleted = True
            audit.purged_at = timezone.now()
            audit.save()
            logger.info("Updated CompanyDeletionAudit for Company ID: %s", company_id)
    except Exception as e:
        logger.error("Error permanently deleting Company ID %s: %s", company_id, str(e))


@shared_task
def cleanup_expired_companies_task():
    """
    Fallback task to permanently delete all companies whose scheduled deletion date has passed.
    """
    now = timezone.now()
    logger.info("Running fallback cleanup for expired companies at %s", now)
    expired_audits = CompanyDeletionAudit.objects.filter(
        scheduled_deletion_date__lte=now,
        is_permanently_deleted=False
    )

    count = 0
    for audit in expired_audits:
        try:
            company = Company.all_objects.filter(id=audit.company_id).first()
            if company:
                company.delete()
                logger.info("Fallback: permanently deleted Company ID %s", audit.company_id)
            audit.is_permanently_deleted = True
            audit.purged_at = now
            audit.save()
            count += 1
        except Exception as e:
            logger.error("Fallback: error deleting Company ID %s: %s", audit.company_id, str(e))

    return f"Cleaned up {count} expired companies"
