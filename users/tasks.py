# Third-party Libraries
from celery import shared_task

# Local Modules
from core import views


# Local Modules
@shared_task(bind=True)
def verification_email_user(self, user_id: int):
    try:

        subject = 'PonteGlam : Confirmación de correo'
        template_name = 'users/verification_email_user.html'
        views.send_email_user_verification_code(
            user_id=user_id, subject=subject, template_name=template_name
        )

    except Exception as e:
        return str(e)


@shared_task(bind=True)
def verification_email_recover_user(self, user_id: int):
    try:
        subject = 'PonteGlam : Código de recuperación de cuenta'
        template_name = 'users/verification_email_recover_user.html'
        views.send_email_user_verification_code(
            user_id=user_id, subject=subject, template_name=template_name
        )

    except Exception as e:
        return str(e)
