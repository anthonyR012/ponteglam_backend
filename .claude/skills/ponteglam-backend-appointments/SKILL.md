---
name: ponteglam-backend-appointments
description: Dominio central de PonteGlam — reservas/citas (Appointment, AppointmentService), su ciclo de estados pending→active→completed/cancelled, trazabilidad, reglas de agendamiento, cancelación con multa y billetera, reprogramación, efectivo, trabajadores y visibilidad de servicios/sedes/empresas. Úsala antes de tocar cualquier lógica de citas, disponibilidad, listados de servicios, cancelaciones, pagos o billetera.
---

# Citas y reglas de negocio

## Jerarquía de oferta

`Company` (dueño = `created_by_user_id`, el proveedor) → `Headquarter` (sede) →
`HeadquarterService` (servicio ofrecido en la sede) → `Service` → `WorkerService` (qué trabajador lo presta).

**Visible para clientes** = servicio `state__code='available'` y no borrado, en sede `available` no
borrada, de empresa `available` no borrada. `ListServices` y
`ServiceCategoryManager.with_available_services()` aplican estas mismas condiciones; cualquier
listado nuevo para clientes debe respetarlas.

## Modelo de cita

- `Appointment`: `status` (CharField, **fuente de verdad**), `payment_method` (`card`/`cash`),
  `price`, `user` (cliente), `reschedule_count`, `cancellation_fee`, `cancellation_fee_level`,
  `refund_pending`, `is_home_service` + `home_address`, `confirmation_in`, `remember_in`.
  El FK `state` (a `core.Type`) es legado: se llena al crear, pero no se usa para decidir nada.
- `AppointmentService`: `service`, `worker`, `start_time`, `end_time` (UTC). Hoy una cita tiene un solo servicio; el código usa `.first()`.
- `AppointmentAddon` (app `addons`): guarda `price_at_booking` y `duration_at_booking`.
- `TraceabilityAppointment`: **cada cambio de estado crea una fila** (`previous_state`, `new_state`, `change_reason`, `metadata`). El app la muestra como línea de tiempo.

## Ciclo de estados

```
            crear cita                  proveedor confirma / auto_confirm (+5 min)
 (nada) ──────────────▶ pending ────────────────────────────────────────▶ active
                          │                                                 │
                          │ cancelar                     auto_complete (end_time) / worker
                          ▼                                                 ▼
                      cancelled ◀──────────── cancelar ─────────────── completed
```

Constantes: `Appointment.STATUS_PENDING | STATUS_ACTIVE | STATUS_CANCELLED | STATUS_COMPLETED`.
Usar siempre las constantes, nunca strings sueltos.

## Reglas al crear (`CreateAppointment`)

1. Billetera con saldo negativo → 400 con `detail` (debe pagar la deuda primero).
2. `start_time` al menos 5 min en el futuro.
3. Máximo 6 citas `pending`+`active` por cliente.
4. Sin duplicado: mismo cliente + trabajador + `start_time`, **excluyendo canceladas**.
5. Crear `Appointment` (status `pending`) + `AppointmentService` + addons + traza "Cita creada".
6. `_schedule_appointment_notifications(...)`: notificación in-app síncrona al proveedor + push, y tareas programadas (recordatorios, auto-confirmación, auto-completado). Ver skill `ponteglam-backend-celery`.

## Cancelación (`CancelAppointment`)

- Cita aún `pending` → **sin multa**.
- Cita `active` → `core.utils.calculate_cancellation_fee(start_time, price)`:
  - Si `global_config.enable_cancellation_fees` ≠ "true" → sin multa.
  - Si no, regla `CancellationRule` activa con mayor `min_hours` ≤ horas restantes; comisión de plataforma 5 % sobre la multa.
- Siempre se registra un `transactions.Fee` con el cálculo.
- Pago con tarjeta y reembolso > 0 → `Transaction` tipo devolución `pending` y `refund_pending = True`.
- Multa > 0:
  - Pago en efectivo → se descuenta de la `Wallet` del cliente (puede quedar negativa = deuda) con `WalletTransaction.TYPE_DEBT`.
  - El trabajador recibe `multa − comisión` como `TYPE_DEPOSIT`.
- Traza de cancelación y `notify_appointment_cancelled.delay(...)` a la contraparte.

## Reprogramación (`RescheduleAppointment`)

- Solo **una** vez por cita (`reschedule_count >= 1` → rechazo).
- Incrementa `reschedule_count`, crea traza y notifica con `notify_appointment_rescheduled`.

## Otras transiciones

- `UpdateAppointmentStatus`: solo el **worker asignado** puede cambiar el estado, con valores validados.
- `ConfirmCashAppointment`: el trabajador confirma que recibió el efectivo.
- `auto_complete_appointment`: además de completar, pide calificación al cliente
  (`prompt_rating`), pide confirmar efectivo si `payment_method == cash` y elimina el
  `WorkerService` marcado `is_pending_removal` cuando era su última cita.

## Billetera (`transactions`)

- Cada `User` tiene una `Wallet` creada por señal `post_save` (`transactions/signals.py`).
- Todo movimiento crea un `WalletTransaction` con `previous_balance` y `new_balance`; nunca
  modificar `balance` sin registrar el movimiento.
- Endpoint: `transactions/api/wallet/`.

## Reglas al modificar esta lógica

- Toda transición de estado: filtrar por el estado de origen, cambiar `status`, crear
  `TraceabilityAppointment`, notificar a la contraparte.
- Operaciones que tocan cita + billetera: envolver en `transaction.atomic()`.
- Comparaciones de "hoy", "faltan X horas", etc.: en UTC con `timezone.now()`; si la regla es
  por día local, convertir ambos lados con `core.utils.get_local_time(..., settings.TIME_ZONE)`.
- Las tareas ya programadas no se revocan: si agregas un estado nuevo, revisa que las tareas de
  `notifications/tasks.py` lo ignoren o lo manejen.
- Al borrar un servicio, una sede o un trabajador, comprobar primero que no haya citas `pending` o `active`.
