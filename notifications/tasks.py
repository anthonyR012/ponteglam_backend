import logging
import http.client
from datetime import timedelta

import requests
from celery import shared_task
from django.utils import timezone
from firebase_admin import messaging, exceptions as firebase_exceptions
from fcm_django.models import FCMDevice

from notifications import models as notification_models
from notifications.models import DeviceToken
from companies.models import Company
from services.models import Appointment, AppointmentService, TraceabilityAppointment
from users.models import User

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_fcm_notification_batch_task(self, tokens, title, body, data=None):
    """
    Tarea robusta para enviar notificaciones push en lote (multicast).
    Maneja reintentos para errores de red y marca tokens inválidos.
    """
    if not tokens:
        return "No tokens provided"

    # Asegurar que data sea serializable por FCM (solo strings)
    fcm_data = {str(k): str(v) for k, v in data.items()} if data else None

    multicast_message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data=fcm_data,
        android=messaging.AndroidConfig(
            priority='high',
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound='default', badge=1),
            ),
        ),
    )

    try:
        response = messaging.send_each_for_multicast(multicast_message)
    except (http.client.RemoteDisconnected,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout) as e:
        logger.warning(f"Falla de red enviando FCM (reintentando): {str(e)}")
        raise self.retry(exc=e)
    except firebase_exceptions.FirebaseError as e:
        # Reintentar solo si es un error transitorio de Firebase
        retry_codes = ['unavailable', 'internal', 'unknown']
        if any(code in str(e).lower() for code in retry_codes):
            logger.warning(f"Error transitorio de Firebase (reintentando): {str(e)}")
            raise self.retry(exc=e)

        logger.error(f"Error crítico de Firebase: {str(e)}")
        return f"Critical error: {str(e)}"
    except Exception as e:
        logger.error(f"Error inesperado en send_fcm_notification_batch_task: {str(e)}")
        return f"Unexpected error: {str(e)}"

    # Procesar resultados individuales
    success_count = response.success_count
    failure_count = response.failure_count
    invalid_tokens = []

    for idx, resp in enumerate(response.responses):
        token = tokens[idx]
        if resp.success:
            logger.info(f"FCM Éxito: Token {token[:10]}... [ID: {resp.message_id}]")
        else:
            error = resp.exception
            err_code = getattr(error, 'code', 'Unknown')
            err_msg = str(error)
            logger.error(f"FCM Fallo: Token {token[:10]}... [Error: {err_code}] - {err_msg}")

            # Identificar tokens que deben ser desactivados (NotRegistered, etc.)
            if isinstance(error, (messaging.UnregisteredError,
                                  messaging.SenderIdMismatchError)):
                invalid_tokens.append(token)
            elif "invalid-registration" in str(err_code).lower():
                invalid_tokens.append(token)

    if invalid_tokens:
        # Marcamos dispositivos como inactivos en la base de datos
        deactivated_count = FCMDevice.objects.filter(
            registration_id__in=invalid_tokens
        ).update(active=False)
        logger.info(f"Se desactivaron {deactivated_count} tokens FCM inválidos")

    return {
        'success_count': success_count,
        'failure_count': failure_count,
        'deactivated_tokens': len(invalid_tokens)
    }


def _send_push_to_user(user_id: int, title: str, body: str, data: dict = None):
    """Envía push notification FCM a todos los dispositivos activos de un usuario."""
    tokens = list(
        FCMDevice.objects.filter(user_id=user_id, active=True)
        .values_list('registration_id', flat=True)
    )
    if not tokens:
        return

    # Delegamos el envío a la tarea robusta asíncrona
    send_fcm_notification_batch_task.delay(tokens, title, body, data)


def _already_notified(user_id: int, appointment_id: int, title: str) -> bool:
    return notification_models.UserNotification.objects.filter(
        user_id=user_id,
        notification__title=title,
        notification__data__appointment_id=str(appointment_id),
    ).exists()


def _create_in_app_notification(
    title: str, body: str, user_id: int, go_to: str = None,
    created_by_user_id: int = None, company_id: int = None, data: dict = None,
):
    """
    Crea una Notification y la asigna al usuario.
    recipient_type se infiere: RECIPIENT_SUPPLIER si hay company_id, RECIPIENT_USER si no.
    """
    if not User.objects.filter(pk=user_id).exists():
        logger.warning(f"_create_in_app_notification: user_id={user_id} no existe, omitiendo.")
        return

    recipient_type = (
        notification_models.UserNotification.RECIPIENT_SUPPLIER
        if company_id
        else notification_models.UserNotification.RECIPIENT_USER
    )
    
    notification = notification_models.Notification.objects.create(
        title=title,
        body=body,
        go_to=go_to,
        data=data,
        created_by_user_id=created_by_user_id or user_id,
    )
    notification_models.UserNotification.objects.create(
        notification=notification,
        user_id=user_id,
        created_by_user_id=created_by_user_id or user_id,
        company_id=company_id,
        recipient_type=recipient_type,
    )


@shared_task
def send_multicast_notification(data: dict):
    title = data.get('title')
    message = data.get('message')

    # Solo considerar tokens activos
    tokens = list(FCMDevice.objects.filter(active=True).values_list('registration_id', flat=True))

    if not tokens:
        return "No active tokens found"

    # Usar la tarea robusta para el envío
    send_fcm_notification_batch_task.delay(tokens, title, message)

    return f"Multicast triggered for {len(tokens)} tokens"


@shared_task
def send_app_notification(data: dict):
    title = data.get('title')
    message = data.get('message')
    user_target = data.get('user_target')
    created_by_user_id = data.get('created_by_user_id')

    notification, _ = notification_models.Notification.objects.get_or_create(
        title=title,
        body=message,
        created_by_user_id=created_by_user_id,
    )

    notification_models.UserNotification.objects.get_or_create(
        notification=notification,
        user_id=user_target,
        created_by_user_id=created_by_user_id,
    )

    return f"Notification sent to user {user_target}"


@shared_task
def create_campaign_app_notification(data: dict):
    title = data.get('title')
    message = data.get('message')
    company_id = data.get('company_id')
    created_by_user_id = data.get('created_by_user_id')
    go_to = data.get('go_to')

    notification, _ = notification_models.Notification.objects.get_or_create(
        title=title,
        body=message,
        go_to=go_to,
        created_by_user_id=created_by_user_id,
    )

    company = Company.objects.get(id=company_id)
    users = company.get_users_liked()

    for user in users:
        notification_models.UserNotification.objects.get_or_create(
            notification=notification,
            user_id=user,
            created_by_user_id=created_by_user_id,
        )

    return f"Notification created to users {users}"


@shared_task
def clean_stale_tokens():
    cutoff = timezone.now() - timedelta(days=60)
    deleted_count, _ = DeviceToken.objects.filter(
        updated_at__lt=cutoff
    ).delete()
    logger.info(
        'clean_stale_tokens: deleted %d stale DeviceToken records',
        deleted_count,
    )
    return deleted_count


@shared_task
def mark_notifications_as_read(notifications_ids: list):
    notification_models.UserNotification.objects.filter(id__in=notifications_ids).exclude(
        is_read=True
    ).update(is_read=True, read_at=timezone.now())

    return f"UserNotifications marked as read with ids: {notifications_ids}"


@shared_task
def push_booking_notification_to_supplier(
    appointment_id: int, supplier_user_id: int, service_name: str
):
    """
    Solo envía FCM push al proveedor al crear una reserva.
    El registro en DB se crea síncronamente en la vista.
    """
    title = "Nueva reserva recibida 📅"
    body = f"Tienes una nueva reserva para **{service_name}**. Revisa tu agenda."
    payload = {
        'action': 'supplier_appointments',
        'appointment_id': str(appointment_id),
    }

    _send_push_to_user(user_id=supplier_user_id, title=title, body=body, data=payload)
    return f"Push sent to supplier {supplier_user_id} for appointment {appointment_id}"


@shared_task
def push_appointment_confirmed_to_client(appointment_id: int, client_user_id: int):
    """
    Solo envía FCM push al cliente cuando su cita es confirmada.
    El registro en DB se crea síncronamente en la vista o auto-confirmación.
    """
    appointment = Appointment.objects.filter(id=appointment_id).first()
    service_name = "tu servicio"
    if appointment:
        first_service = appointment.appointment_service.first()
        if first_service:
            service_name = first_service.service.name

    title = "Reserva Confirmada ✅"
    body = f"Tu reserva para **{service_name}** ha sido confirmada. ¡Te esperamos!"
    payload = {
        'action': 'history',
        'appointment_id': str(appointment_id),
    }
    _send_push_to_user(user_id=client_user_id, title=title, body=body, data=payload)

    # Si la cita es pronto (menos de 35 min desde ahora), enviamos el recordatorio 1 min después de confirmar
    if appointment:
        first_service = appointment.appointment_service.first()
        if first_service and first_service.start_time:
            now = timezone.now()
            if first_service.start_time < now + timedelta(minutes=35) and first_service.start_time > now + timedelta(minutes=10):
                notify_client_reminder.apply_async(
                    kwargs={
                        'appointment_id': appointment.id,
                        'client_user_id': client_user_id,
                        'service_name': service_name,
                    },
                    eta=now + timedelta(minutes=1),
                )

    return f"Push sent to client {client_user_id} for appointment {appointment_id}"


@shared_task
def notify_client_reminder(appointment_id: int, client_user_id: int, service_name: str):
    """
    Programada con eta = start_time - 30 minutos.
    Recuerda al cliente que su cita está próxima.
    """
    # Verificar que la cita siga activa
    if not Appointment.objects.filter(id=appointment_id, status=Appointment.STATUS_ACTIVE).exists():
        return f"Appointment {appointment_id} is not ACTIVE, skipping reminder."

    app_service = AppointmentService.objects.filter(appointment_id=appointment_id).first()
    if not app_service:
        return f"No service found for appointment {appointment_id}"

    now = timezone.now()
    diff = app_service.start_time - now
    minutes = round(diff.total_seconds() / 60)

    title = "Tu cita está próxima ⏰"
    if minutes <= 0:
        body = f"Tu cita de **{service_name}** está comenzando ahora. ¡Prepárate!"
    else:
        body = f"En {minutes} minutos tienes tu cita de **{service_name}**. ¡Prepárate!"

    if _already_notified(client_user_id, appointment_id, title):
        return f"Client {client_user_id} already reminded for appointment {appointment_id}"

    _create_in_app_notification(
        title=title,
        body=body,
        user_id=client_user_id,
        go_to='history',
        created_by_user_id=client_user_id,
        data={'appointment_id': str(appointment_id)},
    )
    payload = {
        'action': 'history',
        'appointment_id': str(appointment_id),
    }
    _send_push_to_user(user_id=client_user_id, title=title, body=body, data=payload)
    return f"Client {client_user_id} reminded for appointment {appointment_id}"

@shared_task
def notify_supplier_reminder(
    appointment_id: int, supplier_user_id: int, service_name: str, minutes_before: int
):
    # Verificar que la cita siga activa
    if not Appointment.objects.filter(id=appointment_id, status=Appointment.STATUS_ACTIVE).exists():
        return f"Appointment {appointment_id} is not ACTIVE, skipping supplier reminder."

    # Obtener el ID de la empresa
    company_id = None
    app_service = AppointmentService.objects.filter(appointment_id=appointment_id).first()
    if app_service and app_service.worker:
        hq_worker = app_service.worker.headquarter_worker.first()
        if hq_worker and hq_worker.headquarter:
            company_id = hq_worker.headquarter.company_id

    payload = {
        'action': 'supplier_appointments',
        'appointment_id': str(appointment_id),
    }

    app_service = AppointmentService.objects.filter(appointment_id=appointment_id).first()
    if not app_service:
        return f"No service found for appointment {appointment_id}"

    now = timezone.now()
    diff = app_service.start_time - now
    minutes = round(diff.total_seconds() / 60)

    title = "Próximo servicio ⏰"
    if minutes <= 0:
        body = f"El servicio **{service_name}** está programado para comenzar ahora."
    else:
        body = f"En {minutes} minutos tienes el servicio **{service_name}** programado."

    if _already_notified(supplier_user_id, appointment_id, title):
        return f"Supplier {supplier_user_id} already reminded for appointment {appointment_id}"

    _create_in_app_notification(
        title=title,
        body=body,
        user_id=supplier_user_id,
        go_to='supplier_appointments',
        created_by_user_id=supplier_user_id,
        company_id=company_id,
        data=payload
    )
    _send_push_to_user(user_id=supplier_user_id, title=title, body=body, data=payload)
    return f"Supplier {supplier_user_id} reminded for appointment {appointment_id}"


@shared_task
def auto_confirm_appointment(appointment_id: int):
    """
    Si la cita sigue en pending después de 5 min, pasa automáticamente a STATUS_ACTIVE.
    """
    appointment = Appointment.objects.filter(
        id=appointment_id, status=Appointment.STATUS_PENDING
    ).first()

    if not appointment:
        return f"Appointment {appointment_id} already confirmed or cancelled."

    previous_status = appointment.status
    appointment.status = Appointment.STATUS_ACTIVE
    appointment.save()

    # Create Traceability entry (System action)
    TraceabilityAppointment.objects.create(
        appointment=appointment,
        previous_state=previous_status,
        new_state=Appointment.STATUS_ACTIVE,
        change_reason='Reserva confirmada automáticamente por el sistema',
        created_by_user_id=1
    )

    if appointment.user_id:
        first_service = appointment.appointment_service.first()
        service_name = first_service.service.name if first_service else "tu servicio"

        title = "Reserva Confirmada ✅"
        body = f"Tu reserva para **{service_name}** ha sido confirmada automáticamente."
        payload = {
            'action': 'history',
            'appointment_id': str(appointment_id),
        }
        _create_in_app_notification(
            title=title,
            body=body,
            user_id=appointment.user_id,
            go_to='history',
            created_by_user_id=appointment.user_id,
            data=payload
        )
        _send_push_to_user(user_id=appointment.user_id, title=title, body=body, data=payload)

        # Si la cita es pronto, disparamos el recordatorio 1 min después de confirmar
        if first_service and first_service.start_time:
            now = timezone.now()
            if first_service.start_time < now + timedelta(minutes=35) and first_service.start_time > now + timedelta(minutes=10):
                notify_client_reminder.apply_async(
                    kwargs={
                        'appointment_id': appointment.id,
                        'client_user_id': appointment.user_id,
                        'service_name': service_name,
                    },
                    eta=now + timedelta(minutes=1),
                )

    return f"Appointment {appointment_id} auto-confirmed after 5 min."


@shared_task
def auto_complete_appointment(appointment_id: int):
    """
    Programada con eta = end_time de la cita.
    Marca la cita como completada y notifica al cliente para calificar.
    Si el pago fue en efectivo, notifica al proveedor para confirmar el pago.
    """
    appointment = Appointment.objects.filter(
        id=appointment_id, status=Appointment.STATUS_ACTIVE
    ).first()

    if not appointment:
        return f"Appointment {appointment_id} is not active, skipping auto-complete."

    previous_status = appointment.status
    appointment.status = Appointment.STATUS_COMPLETED
    appointment.save()

    # Create Traceability entry (System action)
    TraceabilityAppointment.objects.create(
        appointment=appointment,
        previous_state=previous_status,
        new_state=Appointment.STATUS_COMPLETED,
        change_reason='Completada automáticamente por el sistema',
        created_by_user_id=1  # ID representativo para el sistema o el admin inicial
    )

    if appointment.user_id:
        first_service = appointment.appointment_service.first()
        service_name = first_service.service.name if first_service else "tu servicio"
        
        title = "¿Cómo estuvo tu servicio? ⭐"
        body = f"Tu cita para {service_name} ha finalizado. ¡Déjanos tu calificación!"
        
        if not _already_notified(appointment.user_id, appointment_id, title):
            payload = {
                'action': 'history',
                'appointment_id': str(appointment_id),
                'prompt_rating': 'true',
            }
            _create_in_app_notification(
                title=title,
                body=body,
                user_id=appointment.user_id,
                go_to='history',
                created_by_user_id=appointment.user_id,
                data=payload
            )
            _send_push_to_user(user_id=appointment.user_id, title=title, body=body, data=payload)

    # 2. Notificación de pago en efectivo
    if appointment.payment_method == Appointment.PAYMENT_CASH:
        app_service_cash = AppointmentService.objects.filter(
            appointment_id=appointment_id
        ).select_related('worker__user').first()

        if app_service_cash and app_service_cash.worker and app_service_cash.worker.user_id:
            worker_user_id = app_service_cash.worker.user_id
            title = "Confirma el pago en efectivo 💵"
            body = "El servicio ha finalizado. Confirma que recibiste el pago del cliente."
            payload = {
                'action': 'confirm_cash',
                'appointment_id': str(appointment_id),
            }
            # Obtener company_id para el trabajador
            company_id = None
            hq_worker = app_service_cash.worker.headquarter_worker.first()
            if hq_worker and hq_worker.headquarter:
                company_id = hq_worker.headquarter.company_id

            if not _already_notified(worker_user_id, appointment_id, title):
                _create_in_app_notification(
                    title=title,
                    body=body,
                    user_id=worker_user_id,
                    go_to='supplier_appointments',
                    created_by_user_id=worker_user_id,
                    company_id=company_id,
                    data=payload
                )
                _send_push_to_user(user_id=worker_user_id, title=title, body=body, data=payload)

    # 3. Lógica de desvinculación diferida (Delayed Unlink)
    app_service = AppointmentService.objects.filter(
        appointment_id=appointment_id
    ).first()

    if app_service and app_service.worker_id:
        from services.models import WorkerService
        ws_link = WorkerService.objects.filter(
            worker_id=app_service.worker_id,
            service_id=app_service.service_id,
            is_pending_removal=True
        ).first()

        if ws_link:
            # Verificar si quedan más citas activas o pendientes para este mismo binomio
            has_more = AppointmentService.objects.filter(
                worker_id=app_service.worker_id,
                service_id=app_service.service_id,
                appointment__status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_ACTIVE]
            ).exclude(appointment_id=appointment_id).exists()

            if not has_more:
                ws_link.delete()
                logger.info(f"WorkerService vinculado al trabajador {app_service.worker_id} eliminado automáticamente tras su última cita.")

    return f"Appointment {appointment_id} auto-completed."


@shared_task
def notify_appointment_cancelled(appointment_id: int, cancelled_by_user_id: int):
    """
    Notifica a la contraparte que la cita ha sido cancelada.
    """
    appointment = Appointment.objects.filter(id=appointment_id).first()
    if not appointment:
        return f"Appointment {appointment_id} not found."

    app_service = appointment.appointment_service.first()
    if not app_service:
        return f"No service found for appointment {appointment_id}"

    service_name = app_service.service.name
    
    # Determinar destinatario (si el cliente cancela, notifica al worker y viceversa)
    is_client = (cancelled_by_user_id == appointment.user_id)
    recipient_user_id = app_service.worker.user_id if is_client else appointment.user_id
    
    if not recipient_user_id:
        return "No recipient found."

    title = "Cita Cancelada ❌"
    body = (
        f"La cita para **{service_name}** ha sido cancelada."
    )
    
    payload = {
        'action': 'history',
        'appointment_id': str(appointment_id),
    }

    _create_in_app_notification(
        title=title,
        body=body,
        user_id=recipient_user_id,
        go_to='history',
        created_by_user_id=cancelled_by_user_id,
        data=payload
    )
    _send_push_to_user(user_id=recipient_user_id, title=title, body=body, data=payload)
    
    return f"Cancellation notification sent to user {recipient_user_id}"


@shared_task
def notify_appointment_rescheduled(appointment_id: int, rescheduled_by_user_id: int):
    """
    Notifica a la contraparte que la cita ha sido reprogramada.
    """
    appointment = Appointment.objects.filter(id=appointment_id).first()
    if not appointment:
        return f"Appointment {appointment_id} not found."

    app_service = appointment.appointment_service.first()
    if not app_service:
        return f"No service found for appointment {appointment_id}"

    service_name = app_service.service.name
    
    # Determinar destinatario
    is_client = (rescheduled_by_user_id == appointment.user_id)
    recipient_user_id = app_service.worker.user_id if is_client else appointment.user_id
    
    if not recipient_user_id:
        return "No recipient found."

    title = "Cita Reprogramada 🕒"
    body = (
        f"Tu cita para **{service_name}** ha sido reprogramada por la otra parte. "
        "Revisa los nuevos detalles en tu historial."
    )
    
    payload = {
        'action': 'history',
        'appointment_id': str(appointment_id),
    }

    _create_in_app_notification(
        title=title,
        body=body,
        user_id=recipient_user_id,
        go_to='history',
        created_by_user_id=rescheduled_by_user_id,
        data=payload
    )
    _send_push_to_user(user_id=recipient_user_id, title=title, body=body, data=payload)
    
    return f"Reschedule notification sent to user {recipient_user_id}"
