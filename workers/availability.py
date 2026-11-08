"""Cálculo de horarios disponibles de los trabajadores para reservar o reagendar."""
from datetime import datetime, time, timedelta

from django.utils import timezone

from core import models as core_models
from headquarters.models import HeadquarterWorker, HeadquaterWeekDayTimeConfiguration
from services.models import Appointment, AppointmentService
from workers.models import WorkerAvailability, WorkerBlock

SLOT_STEP = timedelta(minutes=30)
DEFAULT_DURATION = timedelta(minutes=30)
DEFAULT_SCHEDULE = [(time(8, 0), time(17, 0))]
WEEKDAY_CODES = {
    0: 'lunes', 1: 'martes', 2: 'miercoles', 3: 'jueves',
    4: 'viernes', 5: 'sabado', 6: 'domingo',
}
BLOCKING_STATUSES = [
    Appointment.STATUS_PENDING,
    Appointment.STATUS_ACTIVE,
    Appointment.STATUS_COMPLETED,
]


def get_service_duration(service) -> timedelta:
    """Duración configurada del servicio; 30 minutos si no tiene una válida."""
    time_conf = service.time_configuration_service.select_related(
        'time_configuration'
    ).first()
    if not time_conf or not time_conf.time_configuration:
        return DEFAULT_DURATION

    tc = time_conf.time_configuration
    total = timedelta(
        hours=getattr(tc, 'hours', 0) or 0,
        minutes=getattr(tc, 'minutes', 0) or 0,
    )
    return total if total.total_seconds() > 0 else DEFAULT_DURATION


def get_appointment_duration(appointment, appointment_service) -> timedelta:
    """Duración real de una cita: servicio más los adicionales reservados."""
    addons_minutes = sum(
        appointment.appointment_addons.values_list('duration_at_booking', flat=True)
    )
    return get_service_duration(appointment_service.service) + timedelta(
        minutes=addons_minutes
    )


def _headquarter_schedules(headquarter_id, weekday: int) -> list:
    configs = HeadquaterWeekDayTimeConfiguration.objects.filter(
        headquarter_id=headquarter_id,
        week_day_time_configuration__week_day__code=WEEKDAY_CODES[weekday],
    ).values_list('week_day_time_configuration_id', flat=True)

    return list(
        core_models.HourWeekDayTimeConfiguration.objects.filter(
            week_day_time_configuration_id__in=list(configs)
        ).values_list('start_time', 'end_time')
    )


def _worker_schedules(worker, weekday: int, headquarter_id, cache: dict) -> list:
    """Horario del trabajador; si no tiene propio, el de su sede; si no, 8am–5pm."""
    key = (worker.id, weekday)
    if key in cache:
        return cache[key]

    schedules = list(
        WorkerAvailability.objects.filter(
            worker=worker, weekday=weekday
        ).values_list('start_time', 'end_time')
    )

    if not schedules:
        target_hq_id = headquarter_id
        if not target_hq_id:
            hq_worker = HeadquarterWorker.objects.filter(worker=worker).first()
            target_hq_id = hq_worker.headquarter_id if hq_worker else None
        if target_hq_id:
            schedules = _headquarter_schedules(target_hq_id, weekday)

    cache[key] = schedules or DEFAULT_SCHEDULE
    return cache[key]


def _overlaps(start, end, ranges) -> bool:
    return any(start < r_end and end > r_start for r_start, r_end in ranges)


def compute_available_slots(
    service,
    workers,
    start_date,
    days: int,
    duration: timedelta,
    headquarter_id=None,
    client=None,
    exclude_appointment_id=None,
    earliest_start=None,
) -> dict:
    """
    Slots libres agrupados por fecha local (YYYY-MM-DD).

    Un slot es libre si cabe en el horario del trabajador y no cruza sus citas
    (pendientes, activas o completadas), sus bloqueos manuales ni las citas
    pendientes/activas del cliente. `exclude_appointment_id` ignora una cita
    existente (la que se está reagendando).
    """
    workers = list(workers)
    end_date = start_date + timedelta(days=days)
    earliest_start = earliest_start or timezone.now()

    booked_qs = AppointmentService.objects.filter(
        worker__in=workers,
        start_time__date__gte=start_date,
        start_time__date__lt=end_date,
        appointment__status__in=BLOCKING_STATUSES,
    )
    blocks_qs = WorkerBlock.objects.filter(
        worker__in=workers,
        start_time__lt=timezone.make_aware(datetime.combine(end_date, time.max)),
        end_time__gt=timezone.make_aware(datetime.combine(start_date, time.min)),
    )
    client_qs = AppointmentService.objects.none()
    if client is not None and client.is_authenticated:
        client_qs = AppointmentService.objects.filter(
            appointment__user=client,
            start_time__date__gte=start_date,
            start_time__date__lt=end_date,
            appointment__status__in=[
                Appointment.STATUS_PENDING, Appointment.STATUS_ACTIVE
            ],
        )
    if exclude_appointment_id:
        booked_qs = booked_qs.exclude(appointment_id=exclude_appointment_id)
        client_qs = client_qs.exclude(appointment_id=exclude_appointment_id)

    worker_busy = {}
    for w_id, b_start, b_end in booked_qs.values_list('worker_id', 'start_time', 'end_time'):
        worker_busy.setdefault(w_id, []).append((b_start, b_end))
    for w_id, b_start, b_end in blocks_qs.values_list('worker_id', 'start_time', 'end_time'):
        worker_busy.setdefault(w_id, []).append((b_start, b_end))
    client_busy = list(client_qs.values_list('start_time', 'end_time'))

    schedules_cache = {}
    grouped = {}

    for offset in range(days):
        target_date = start_date + timedelta(days=offset)
        date_key = target_date.strftime('%Y-%m-%d')

        for worker in workers:
            busy = worker_busy.get(worker.id, [])
            schedules = _worker_schedules(
                worker, target_date.weekday(), headquarter_id, schedules_cache
            )

            for sched_start, sched_end in schedules:
                current = timezone.make_aware(datetime.combine(target_date, sched_start))
                schedule_end = timezone.make_aware(datetime.combine(target_date, sched_end))

                while current + duration <= schedule_end:
                    slot_end = current + duration
                    if (
                        current >= earliest_start
                        and not _overlaps(current, slot_end, busy)
                        and not _overlaps(current, slot_end, client_busy)
                    ):
                        grouped.setdefault(date_key, []).append({
                            'worker_id': worker.id,
                            'worker_name': str(worker),
                            'start_time': current,
                            'end_time': slot_end,
                            'only_home_service': service.only_home_service,
                            'home_service_price': service.home_service_price,
                        })
                    current += SLOT_STEP

    return grouped


def group_slots_response(grouped: dict) -> list:
    """Forma de respuesta del API: [{'date', 'slots'}] ordenada por fecha y hora."""
    return [
        {'date': date_key, 'slots': sorted(slots, key=lambda s: s['start_time'])}
        for date_key, slots in sorted(grouped.items())
    ]
