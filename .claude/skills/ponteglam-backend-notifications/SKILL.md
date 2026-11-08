---
name: ponteglam-backend-notifications
description: Sistema de notificaciones del backend PonteGlam — notificaciones in-app (Notification + UserNotification), push FCM con firebase_admin y fcm_django, destinatario usuario vs proveedor, payload action/appointment_id que el app usa para navegar, y registro de dispositivos. Úsala al notificar a un usuario, al agregar un tipo de notificación nueva o al depurar un push que no llega.
---

# Notificaciones (in-app + push)

## Modelo de datos (`notifications/models.py`)

- `Notification(title, body, go_to, data: JSON, image)` — el contenido.
- `UserNotification(notification, user, company, recipient_type, is_read, read_at)` — la entrega a un usuario.
  - `recipient_type`: `RECIPIENT_USER` ('user') o `RECIPIENT_SUPPLIER` ('supplier'). El app muestra
    bandejas separadas para cliente y proveedor; el manager `UserNotificationManager` filtra por ello.
- Dispositivos: `fcm_django.models.FCMDevice` (fuente real para push, campo `active`) y
  `notifications.DeviceToken` (legado, limpiado por `clean_stale_tokens`).
  El app registra su token en `notifications/api/register-device/` (POST registra, DELETE elimina).

## Las dos mitades de una notificación

| Mitad | Cómo | Cuándo |
|---|---|---|
| In-app (registro en BD) | `_create_in_app_notification(...)` | **Síncrono** si el usuario debe verla ya (ej. nueva reserva); dentro de la tarea si es programada |
| Push (FCM) | `_send_push_to_user(user_id, title, body, data)` → `send_fcm_notification_batch_task.delay(...)` | Siempre asíncrono |

```python
from notifications.tasks import _create_in_app_notification, _send_push_to_user

payload = {'action': 'history', 'appointment_id': str(appointment.id)}
_create_in_app_notification(
    title='Reserva Confirmada ✅',
    body=f'Tu reserva para **{service.name}** ha sido confirmada.',
    user_id=client_id,
    go_to='history',
    created_by_user_id=request.user.pk,
    data=payload,
)
_send_push_to_user(user_id=client_id, title=..., body=..., data=payload)
```

- `company_id` presente → `recipient_type = supplier`. Para notificar a un proveedor o trabajador,
  pasar el `company_id` de su sede; si no, la notificación cae en la bandeja de cliente.
- `data` de FCM debe ser `dict[str, str]`: la tarea convierte, pero pasar ids como `str(...)`.
- El texto usa `**negrita**`: el app lo renderiza. Mensajes en español, con emoji al inicio del título como el resto.

## Contrato de navegación con el app (`action` / `go_to`)

El app lee `data['go_to'] ?? data['action']` (`lib/core/navigation/notification_handler.dart`,
`lib/device/firebase/cloud_messaging.dart`, `local_notification_service.dart`):

| Valor | Destino en el app | Extra |
|---|---|---|
| `history`, `client_appointments`, `appointment_detail` | Historial / detalle de cita del cliente | `appointment_id`, opcional `prompt_rating: 'true'` abre la calificación |
| `supplier_appointments` | Agenda del proveedor | `appointment_id` |
| `confirm_cash` | **No está manejado en el app**: el push llega pero no navega. Si se usa, agregar el caso en el app | `appointment_id` |

Un `go_to` nuevo requiere cambiar el app en los tres archivos anteriores; un valor desconocido no navega (a propósito, para evitar crashes).

## Idempotencia

Antes de crear una notificación desde una tarea que puede repetirse:
`_already_notified(user_id, appointment_id, title)` (busca por título + `data.appointment_id`).
Si cambias el título de una notificación existente, esta deduplicación deja de reconocer las viejas.

## FCM: envío y errores (`send_fcm_notification_batch_task`)

- Multicast con prioridad alta en Android y sonido/badge en iOS.
- Reintenta (3 veces, 10 s) ante errores de red y errores transitorios de Firebase (`unavailable`, `internal`, `unknown`).
- Tokens `UnregisteredError` / `SenderIdMismatchError` / `invalid-registration` → `FCMDevice.active = False`.
- Credenciales: JSON de service account cargado en `settings.py` (archivo privado: **no leerlo sin permiso**).

## Depurar un push que no llega

1. ¿El usuario tiene `FCMDevice` activo? `FCMDevice.objects.filter(user_id=X, active=True)`.
2. ¿El worker está arriba y la tarea corrió? Revisar *Task results* (`success_count`, `failure_count`).
3. ¿Se creó la `UserNotification`? Si sí y no hubo push, el problema es FCM o el token.
4. Script manual de prueba: `antigravity/send_manual_notification.py`.
