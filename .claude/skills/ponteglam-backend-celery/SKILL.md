---
name: ponteglam-backend-celery
description: Procesos en cola del backend PonteGlam con Celery + Redis — configuración, cómo escribir y despachar tareas (.delay, apply_async con eta), tareas periódicas con beat, reintentos, idempotencia, borrado diferido, correo y notificaciones programadas, y cómo depurarlas. Úsala al crear o modificar cualquier tasks.py, al programar algo a futuro, al enviar correos o push, o cuando una tarea "no se ejecuta".
---

# Procesos en cola (Celery)

## Configuración (`ponteglam/celery.py`, `settings.py`)

- Broker: Redis db 0 (`REDIS_URL`). Resultados: BD (`django-db`), visibles en admin → *Task results*.
- `app.autodiscover_tasks()` carga `<app>/tasks.py` de todas las apps instaladas.
- `CELERY_TASK_ACKS_LATE = True` + `PREFETCH_MULTIPLIER = 1`: las tareas con ETA no se pierden si el worker reinicia.
- Serialización **solo JSON**: los argumentos deben ser tipos simples (int, str, dict, list). Pasar **ids**, nunca instancias de modelo.
- `CELERY_TIMEZONE = 'America/Bogota'`, `ENABLE_UTC = True`: los `eta` deben ser datetimes **aware** (`timezone.now() + timedelta(...)`).

## Inventario de tareas

| Tarea | Disparo | Qué hace |
|---|---|---|
| `users.tasks.verification_email_user` | `.delay(user_id)` al registrarse / reenviar | Correo con código de verificación (reintenta 3 veces ante errores SMTP) |
| `users.tasks.verification_email_recover_user` | `.delay(user_id)` | Correo de recuperación |
| `notifications.tasks.send_fcm_notification_batch_task` | interno | Envío multicast FCM con reintentos y desactivación de tokens inválidos |
| `notifications.tasks.push_booking_notification_to_supplier` | al crear cita | Push al proveedor |
| `notifications.tasks.push_appointment_confirmed_to_client` | al confirmar | Push al cliente |
| `notifications.tasks.notify_client_reminder` | `eta = inicio − 30 min` | Recordatorio al cliente |
| `notifications.tasks.notify_supplier_reminder` | `eta = inicio − service.remember_in` | Recordatorio al proveedor |
| `notifications.tasks.auto_confirm_appointment` | `eta = ahora + 5 min` | pending → active si nadie respondió |
| `notifications.tasks.auto_complete_appointment` | `eta = end_time` | active → completed, pedir calificación, pedir confirmar efectivo, desvincular trabajador pendiente |
| `notifications.tasks.notify_appointment_cancelled` / `_rescheduled` | `.delay` | Avisa a la contraparte |
| `notifications.tasks.send_multicast_notification`, `send_app_notification`, `create_campaign_app_notification`, `mark_notifications_as_read` | `.delay` desde vistas | Campañas y lectura |
| `services/companies/headquarters.tasks.permanently_delete_<x>_task` | `eta = +5 días` | Purga definitiva tras borrado lógico |
| `cleanup_expired_<x>_task` | respaldo | Purga lo vencido si se perdió el ETA |
| `notifications.tasks.clean_stale_tokens` | beat, semanal | Borra `DeviceToken` sin uso en 60 días |
| `core.tasks.cleanup_mobile_logs` | beat, mensual | Borra `MobileAppLog` de más de 30 días |

Beat está en `settings.CELERY_BEAT_SCHEDULE` (no hay PeriodicTask en BD). Las `cleanup_expired_*`
**no** están en el schedule: si se necesitan periódicas, agregarlas ahí.

## Cómo escribir una tarea

```python
import logging
import smtplib

from celery import shared_task

from services.models import Appointment

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(smtplib.SMTPException, OSError),
    retry_backoff=30,
    max_retries=3,
)
def mi_tarea(self, appointment_id: int):
    """Propósito de la tarea en una línea."""
    appointment = Appointment.objects.filter(
        id=appointment_id, status=Appointment.STATUS_ACTIVE
    ).first()
    if not appointment:
        return f'Appointment {appointment_id} ya no está activa, se omite.'
    ...
    return 'resultado legible'
```

Reglas:
1. **Revalidar el estado al ejecutar.** Entre que se programa y se ejecuta, la cita pudo cancelarse o cambiar. Todas las tareas de citas hacen `filter(..., status=...)` primero.
2. **Idempotencia.** Una tarea puede correr dos veces (acks_late, reintentos). Antes de notificar, `_already_notified(user_id, appointment_id, title)`; antes de cambiar estado, filtrar por el estado de origen.
3. **No tragarse errores.** `except Exception: return str(e)` marca la tarea como SUCCESS y esconde el fallo (pasó con el correo de verificación). Dejar que la excepción suba o usar `autoretry_for` / `self.retry(exc=e)` para errores transitorios. Loguear con `logger`, no `print`.
4. **Retornar un string o dict corto**: queda en *Task results* y sirve para depurar.
5. Registrar trazabilidad cuando una tarea cambia el estado de una cita (`TraceabilityAppointment`, `created_by_user_id=1` = sistema).

## Cómo despachar

```python
mi_tarea.delay(appointment.id)                                   # ya
mi_tarea.apply_async(kwargs={'appointment_id': a.id}, eta=start_time - timedelta(minutes=30))
```

- Despachar **después** de que los datos existan en BD. Si la vista usa `transaction.atomic`,
  usar `transaction.on_commit(lambda: mi_tarea.delay(obj.id))` para que el worker no lea antes del commit.
- Si el ETA ya pasó, decidir explícitamente: omitir o ejecutar ya (ver `_schedule_appointment_notifications`).
- Envolver el despacho en `try/except` solo si la vista debe responder aunque Redis falle, y loguear el error.
- Las tareas programadas **no se cancelan** al cancelar o reprogramar una cita: por eso cada tarea revalida el estado. Mantener ese patrón en lugar de depender de `revoke`.

## Depuración

```bash
pgrep -fl "celery -A ponteglam"                       # ¿worker y beat corriendo?
tail -f /private/tmp/celery_worker.log                # log local del worker
env/bin/python manage.py shell -c "
from django_celery_results.models import TaskResult
for t in TaskResult.objects.order_by('-date_created')[:10]:
    print(t.date_created, t.task_name, t.status, (t.result or '')[:200])"
```

- Cambié `tasks.py` o settings → **reiniciar el worker** (`kill -TERM <pid>` y relanzar
  `env/bin/celery -A ponteglam worker --loglevel=info`). Si no, sigue corriendo código viejo.
- Probar una tarea síncronamente: `mi_tarea.apply(args=[id]).get()` en el shell, o `.delay(...).get(timeout=60)` con el worker arriba.
- Correo: probar el login SMTP con `django.core.mail.get_connection().open()` antes de culpar a la tarea.
