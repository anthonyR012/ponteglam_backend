# Python Standard Library
import smtplib

# Third-party Libraries
from celery import shared_task

# Local Modules
from core import views


EMAIL_RETRY_OPTIONS = {
    'autoretry_for': (smtplib.SMTPException, OSError),
    'retry_backoff': 30,
    'max_retries': 3,
}


@shared_task(bind=True, **EMAIL_RETRY_OPTIONS)
def verification_email_user(self, user_id: int):
    subject = 'PonteGlam : Confirmación de correo'
    template_name = 'users/verification_email_user.html'
    return views.send_email_user_verification_code(
        user_id=user_id, subject=subject, template_name=template_name
    )


@shared_task(bind=True, **EMAIL_RETRY_OPTIONS)
def verification_email_recover_user(self, user_id: int):
    subject = 'PonteGlam : Código de recuperación de cuenta'
    template_name = 'users/verification_email_recover_user.html'
    return views.send_email_user_verification_code(
        user_id=user_id, subject=subject, template_name=template_name
    )
