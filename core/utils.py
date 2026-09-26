# Python Standard Library
import datetime
import zoneinfo

# Third-party Libraries
from django.conf import settings
from django.utils import timezone
from haversine import haversine
from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    page_size = 15


def calculate_km_between_two_points(initial_point: tuple, target_point: tuple):
    """
    Calculate the distance in kilometers between two geographical points.

    Parameters:
    initial_point (tuple): A tuple representing the initial
                           point with (latitude, longitude).
    target_point (tuple): A tuple representing the target
                          point with (latitude, longitude).

    Returns:
    float: The distance between the initial and target points
           in kilometers, rounded to 1 decimal place.
    """

    return round(haversine(initial_point, target_point), 1)


def parse_aware_datetime(value: str) -> datetime.datetime:
    """
    Parse an ISO 8601 string and return a UTC-aware datetime.

    Raises ValueError if the string does not include a timezone offset,
    e.g. '2026-04-14T15:00:00-05:00' is valid but '2026-04-14T15:00:00' is not.
    """
    dt = datetime.datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError(
            "DateTime must include timezone offset. "
            "Example: 2026-04-14T15:00:00-05:00"
        )
    return dt.astimezone(datetime.timezone.utc)


def get_local_time(dt: datetime.datetime, tz_name: str) -> datetime.datetime:
    """Convert a UTC-aware datetime to the given IANA timezone."""
    tz = zoneinfo.ZoneInfo(tz_name)
    return dt.astimezone(tz)


def now_in_tz(tz_name: str) -> datetime.datetime:
    """Return the current time converted to the given IANA timezone."""
    return get_local_time(timezone.now(), tz_name)


def format_currency(amount) -> str:
    """Format an amount as Colombian Pesos."""
    return f"${int(amount):,}".replace(",", ".")


def calculate_cancellation_fee(
    appointment_start: datetime.datetime,
    service_total: float,
) -> dict:
    """
    Return fee info based on dynamic rules in the database.
    Checks if cancellation fees are globally enabled.
    """
    from services.models import CancellationRule
    from core.models import Type

    # 1. Check Global Configuration
    # We use Type model with code 'enable_cancellation_fees' in category 'global_config'
    # The 'description' field stores "true" or "false"
    config = Type.objects.filter(
        code='enable_cancellation_fees',
        category_type__code='global_config'
    ).first()

    is_enabled = config and config.description.lower() == 'true'

    if not is_enabled:
        return {
            "penalty_pct": 0.0,
            "fee_amount": 0.0,
            "platform_commission": 0.0,
            "refund_to_party": float(service_total),
            "fee_level": "none",
        }

    PONTEGLAM_COMMISSION = 0.05  # 5% of the fee
    now = timezone.now()
    hours_remaining = (
        appointment_start - now
    ).total_seconds() / 3600

    # Get the rule that matches the highest min_hours <= current hours_remaining
    rule = CancellationRule.objects.filter(
        is_active=True,
        min_hours__lte=hours_remaining
    ).order_by('-min_hours').first()

    # Default if no rules are found (very unlikely)
    if not rule:
        penalty_pct = 0.80
        fee_level = "high"
    else:
        penalty_pct = rule.penalty_pct
        fee_level = rule.fee_level

    fee_amount = float(service_total) * penalty_pct
    commission = fee_amount * PONTEGLAM_COMMISSION
    refund = float(service_total) - fee_amount

    return {
        "penalty_pct": penalty_pct,
        "fee_amount": fee_amount,
        "platform_commission": commission,
        "refund_to_party": refund,
        "fee_level": fee_level,
    }
