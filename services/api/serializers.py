# Python Standard Library
import datetime

# Third-party Libraries
from rest_framework import serializers

# Local Modules
from services import models
from users.api.serializers import ListUserAddressSerializer
from addons.api.serializers import AppointmentAddonSerializer

_DT_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
_TZ_ERROR = (
    'DateTime must include timezone offset. '
    'Example: 2026-04-14T15:00:00-05:00'
)


def _validate_aware(value: datetime.datetime) -> datetime.datetime:
    """Reject naive datetimes and convert to UTC."""
    if value.tzinfo is None:
        raise serializers.ValidationError(_TZ_ERROR)
    return value.astimezone(datetime.timezone.utc)


class CreateServiceSerializer(serializers.ModelSerializer):

    only_home_service = serializers.BooleanField(
        required=False,
        default=False,
    )
    home_service_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        default=None,
    )

    class Meta:
        model = models.Service
        fields = (
            'id', 'name', 'description', 'confirmation_in', 'remember_in',
            'only_home_service', 'price', 'home_service_price',
            'state', 'gender', 'service_category',
            'created_by_user_id',
        )
        extra_kwargs = {
            'created_by_user_id': {'required': True},
        }

    def validate_name(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("El nombre debe tener al menos 10 caracteres.")
        import re
        if not re.search(r'[a-zA-Z]', value):
            raise serializers.ValidationError("El nombre debe contener letras, no solo números o símbolos.")
        return value

    def validate_description(self, value):
        if len(value) < 30:
            raise serializers.ValidationError("La descripción debe tener al menos 30 caracteres.")
        return value

    def validate(self, data):
        if (
            data.get('only_home_service')
            and data.get('home_service_price') is not None
            and data['home_service_price'] < 0
        ):
            raise serializers.ValidationError(
                {'home_service_price': 'El precio a domicilio no puede ser negativo.'}
            )
        return data


class ServiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Service
        fields = (
            'id', 'name', 'description', 'confirmation_in', 'remember_in',
            'only_home_service', 'price', 'home_service_price', 'state', 'gender',
            'service_category', 'service_duration', 'images', 'amenities',
            'rating', 'rating_count', 'can_rate', 'my_rating'
        )
        extra_kwargs = {
            'created_by_user_id': {'required': True},
        }

    price = serializers.SerializerMethodField()
    service_duration = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    amenities = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    can_rate = serializers.SerializerMethodField()
    my_rating = serializers.SerializerMethodField()

    def _get_hq_service(self, obj):
        hq = self.context.get('headquarter')
        if hq:
            return obj.headquarter_service.filter(headquarter=hq).first()
        return obj.headquarter_service.first()

    def get_can_rate(self, obj: models.Service):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
            
        from datetime import timedelta
        from django.utils import timezone
        one_year_ago = timezone.now() - timedelta(days=365)
        
        return models.AppointmentService.objects.filter(
            service=obj,
            appointment__user=request.user,
            appointment__status=models.Appointment.STATUS_COMPLETED,
            end_time__gte=one_year_ago
        ).exists()

    def get_my_rating(self, obj: models.Service):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
            
        hq_service = self._get_hq_service(obj)
        if not hq_service:
            return None
            
        from ratings.models import HeadquarterServiceRating
        rating_obj = HeadquarterServiceRating.objects.filter(
            headquarter_service=hq_service,
            user=request.user
        ).first()
        
        if rating_obj:
            return {
                'id': rating_obj.id,
                'rating': rating_obj.rating,
                'comment': rating_obj.comment
            }
        return None

    def get_price(self, obj: models.Service):
        return obj.price

    def get_service_duration(self, obj: models.Service):
        """Retorna la duración real del servicio en minutos desde TimeConfigurationService."""
        try:
            time_conf = obj.time_configuration_service.select_related(
                'time_configuration'
            ).first()
            if time_conf and time_conf.time_configuration:
                tc = time_conf.time_configuration
                hours = getattr(tc, 'hours', 0) or 0
                minutes = getattr(tc, 'minutes', 0) or 0
                total_minutes = hours * 60 + minutes
                return total_minutes if total_minutes > 0 else 30
        except Exception:
            pass
        return 30

    def get_images(self, obj: models.Service):
        host = self.context.get('request').build_absolute_uri('/')
        return obj.get_url_images(host)

    def get_amenities(self, obj: models.Service):
        return obj.get_amenities()

    def get_rating(self, obj: models.Service):
        hq_service = self._get_hq_service(obj)
        return hq_service.rating if hq_service else 0.0

    def get_rating_count(self, obj: models.Service):
        hq_service = self._get_hq_service(obj)
        return hq_service.rating_count if hq_service else 0


class ServiceDetailSerializer(serializers.ModelSerializer):
    """Serializer con detalle completo de un servicio individual."""

    images = serializers.SerializerMethodField()
    service_duration = serializers.SerializerMethodField()
    amenities = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    headquarter = serializers.SerializerMethodField()
    can_rate = serializers.SerializerMethodField()
    my_rating = serializers.SerializerMethodField()

    class Meta:
        model = models.Service
        fields = (
            'id', 'name', 'description', 'price', 'only_home_service',
            'home_service_price', 'state', 'gender', 'service_category',
            'category_name', 'service_duration', 'images', 'amenities',
            'rating', 'rating_count', 'headquarter',
            'can_rate', 'my_rating'
        )

    def _get_hq_service(self, obj):
        hq = self.context.get('headquarter')
        if hq:
            return obj.headquarter_service.filter(headquarter=hq).first()
        return obj.headquarter_service.first()

    def get_can_rate(self, obj: models.Service):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
            
        from datetime import timedelta
        from django.utils import timezone
        one_year_ago = timezone.now() - timedelta(days=365)
        
        return models.AppointmentService.objects.filter(
            service=obj,
            appointment__user=request.user,
            appointment__status=models.Appointment.STATUS_COMPLETED,
            end_time__gte=one_year_ago
        ).exists()

    def get_my_rating(self, obj: models.Service):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
            
        hq_service = self._get_hq_service(obj)
        if not hq_service:
            return None
            
        from ratings.models import HeadquarterServiceRating
        rating_obj = HeadquarterServiceRating.objects.filter(
            headquarter_service=hq_service,
            user=request.user
        ).first()
        
        if rating_obj:
            return {
                'id': rating_obj.id,
                'rating': rating_obj.rating,
                'comment': rating_obj.comment
            }
        return None

    def get_images(self, obj: models.Service):
        host = self.context.get('request').build_absolute_uri('/')
        return obj.get_url_images(host)

    def get_service_duration(self, obj: models.Service):
        try:
            time_conf = obj.time_configuration_service.select_related(
                'time_configuration'
            ).first()
            if time_conf and time_conf.time_configuration:
                tc = time_conf.time_configuration
                hours = getattr(tc, 'hours', 0) or 0
                minutes = getattr(tc, 'minutes', 0) or 0
                total_minutes = hours * 60 + minutes
                return total_minutes if total_minutes > 0 else 30
        except Exception:
            pass
        return 30

    def get_amenities(self, obj: models.Service):
        return list(obj.get_amenities())

    def get_category_name(self, obj: models.Service):
        return obj.service_category.description if obj.service_category else None

    def get_rating(self, obj: models.Service):
        hq_service = obj.headquarter_service.first()
        return hq_service.rating if hq_service else 0

    def get_rating_count(self, obj: models.Service):
        hq_service = obj.headquarter_service.first()
        return hq_service.rating_count if hq_service else 0

    def get_headquarter(self, obj: models.Service):
        hq_service = obj.headquarter_service.select_related('headquarter__company').first()
        if not hq_service:
            return None
        hq = hq_service.headquarter
        request = self.context.get('request')
        host = request.build_absolute_uri('/') if request else None
        return {
            'id': hq.id,
            'name': hq.name,
            'address': hq.address,
            'phone_number': hq.phone_number,
            'latitude': hq.latitude,
            'longitude': hq.longitude,
            'company_name': hq.company.name if hq.company else None,
            'image_url': hq.get_company_picture_url(host),
        }


class ServiceFileSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.ServiceFile
        fields = '__all__'
        extra_kwargs = {
            'created_by_user_id': {'required': True},
        }


class ServiceCategorySerializer(serializers.ModelSerializer):

    picture = serializers.SerializerMethodField()

    class Meta:
        model = models.ServiceCategory
        fields = '__all__'

    def get_picture(self, obj):
        import re
        request = self.context.get('request')

        if obj.picture:
            picture_url = obj.picture.url
            if not re.match(r'^https?://', picture_url):
                picture_url = 'http://' + request.get_host() + picture_url
            return picture_url
        return None


class CreateAppointmentSerializer(serializers.Serializer):
    service_id = serializers.IntegerField(required=True)
    worker_id = serializers.IntegerField(required=True)
    start_time = serializers.DateTimeField(
        required=True, input_formats=['iso-8601']
    )
    end_time = serializers.DateTimeField(
        required=True, input_formats=['iso-8601']
    )
    remember_in = serializers.DateTimeField(
        required=False, allow_null=True, input_formats=['iso-8601']
    )
    confirmation_in = serializers.DateTimeField(
        required=False, allow_null=True, input_formats=['iso-8601']
    )
    payment_method = serializers.ChoiceField(
        choices=['card', 'cash'], default='card', required=False
    )
    is_home_service = serializers.BooleanField(
        required=False,
        default=False,
    )
    home_address_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
    )
    addon_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )

    def validate(self, data):
        if data.get('is_home_service') and data.get('home_address_id') is None:
            raise serializers.ValidationError({
                'home_address_id': (
                    'home_address_id is required when is_home_service is true'
                )
            })
        return data

    def validate_start_time(self, value):
        return _validate_aware(value)

    def validate_end_time(self, value):
        return _validate_aware(value)

    def validate_remember_in(self, value):
        if value is None:
            return value
        return _validate_aware(value)

    def validate_confirmation_in(self, value):
        if value is None:
            return value
        return _validate_aware(value)


class AppointmentServiceSummarySerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_price = serializers.DecimalField(
        source='service.price', max_digits=10, decimal_places=2, read_only=True
    )
    worker_name = serializers.SerializerMethodField()
    worker_id = serializers.IntegerField(source='worker.id', read_only=True)
    start_time = serializers.DateTimeField(format=_DT_FORMAT, read_only=True)
    end_time = serializers.DateTimeField(format=_DT_FORMAT, read_only=True)
    service_image = serializers.SerializerMethodField()

    class Meta:
        model = models.AppointmentService
        fields = [
            'id', 'service_id', 'service_name', 'service_price',
            'worker_id', 'worker_name', 'start_time', 'end_time',
            'service_image',
        ]

    def get_worker_name(self, obj):
        if obj.worker and obj.worker.user:
            return obj.worker.user.full_name or obj.worker.user.username
        return None

    def get_service_image(self, obj):
        request = self.context.get('request')
        host = request.build_absolute_uri('/') if request else None
        images = obj.service.get_url_images(host)
        return images[0] if images else None


class TraceabilityAppointmentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format=_DT_FORMAT)

    class Meta:
        model = models.TraceabilityAppointment
        fields = [
            'id', 'previous_state', 'new_state', 'change_reason',
            'metadata', 'created_at', 'user_name', 'created_by_user_id'
        ]

    def get_user_name(self, obj):
        from users.models import User
        user = User.objects.filter(id=obj.created_by_user_id).first()
        if user:
            return user.full_name or user.username
        if obj.created_by_user_id == 1:
            return "Sistema"
        return f"Usuario {obj.created_by_user_id}"


class AppointmentListSerializer(serializers.ModelSerializer):
    appointment_services = AppointmentServiceSummarySerializer(
        source='appointment_service', many=True, read_only=True
    )
    state_description = serializers.SerializerMethodField()
    confirmation_in = serializers.DateTimeField(format=_DT_FORMAT, read_only=True)
    remember_in = serializers.DateTimeField(format=_DT_FORMAT, read_only=True)
    home_address = ListUserAddressSerializer(read_only=True)
    addons = AppointmentAddonSerializer(
        source='appointment_addons',
        many=True,
        read_only=True,
    )
    traceability = TraceabilityAppointmentSerializer(
        many=True, read_only=True
    )
    can_cancel = serializers.SerializerMethodField()
    can_reschedule = serializers.SerializerMethodField()
    reschedule_message = serializers.SerializerMethodField()

    class Meta:
        model = models.Appointment
        fields = [
            'id', 'status', 'price', 'confirmation_in', 'remember_in',
            'cancellation_reason', 'refund_pending', 'state_description',
            'payment_method', 'is_home_service', 'home_address',
            'appointment_services', 'addons', 'traceability', 'can_cancel', 'can_reschedule', 'reschedule_message',
        ]

    def get_state_description(self, obj):
        if obj.status == models.Appointment.STATUS_ACTIVE:
            from django.utils import timezone
            now = timezone.now()
            first_service = obj.appointment_service.first()
            if first_service and first_service.start_time and first_service.end_time:
                if first_service.start_time <= now <= first_service.end_time:
                    return 'En curso'
        return obj.state.description if obj.state else None

    def get_can_cancel(self, obj):
        return obj.status in [
            models.Appointment.STATUS_PENDING,
            models.Appointment.STATUS_ACTIVE,
        ]

    def get_can_reschedule(self, obj):
        if obj.status not in [
            models.Appointment.STATUS_PENDING,
            models.Appointment.STATUS_ACTIVE,
        ]:
            return False

        if obj.reschedule_count >= 1:
            return False

        from django.utils import timezone
        from datetime import timedelta
        first_service = obj.appointment_service.first()
        if not first_service or not first_service.start_time:
            return False

        if first_service.start_time < timezone.now() + timedelta(hours=10):
            return False

        return True

    def get_reschedule_message(self, obj):
        if obj.status not in [
            models.Appointment.STATUS_PENDING,
            models.Appointment.STATUS_ACTIVE,
        ]:
            return None

        if obj.reschedule_count >= 1:
            return "Ya has agotado el límite de 1 reprogramación para esta cita."

        from django.utils import timezone
        from datetime import timedelta
        first_service = obj.appointment_service.first()
        if first_service and first_service.start_time:
            if first_service.start_time < timezone.now() + timedelta(hours=10):
                return "No puedes reprogramar faltando menos de 10 horas para la cita."

        return None


class AppointmentDetailSerializer(serializers.ModelSerializer):
    appointment_services = AppointmentServiceSummarySerializer(
        source='appointment_service', many=True, read_only=True
    )
    state_description = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    can_reschedule = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()
    reschedule_message = serializers.SerializerMethodField()
    cancellation_fee_info = serializers.SerializerMethodField()
    confirmation_in = serializers.DateTimeField(format=_DT_FORMAT, read_only=True)
    remember_in = serializers.DateTimeField(format=_DT_FORMAT, read_only=True)
    home_address = ListUserAddressSerializer(read_only=True)
    addons = AppointmentAddonSerializer(
        source='appointment_addons',
        many=True,
        read_only=True,
    )
    traceability = TraceabilityAppointmentSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = models.Appointment
        fields = [
            'id', 'status', 'price', 'confirmation_in', 'remember_in',
            'cancellation_reason', 'refund_pending',
            'state_description', 'can_cancel', 'can_reschedule', 'can_review',
            'reschedule_message', 'cancellation_fee_info', 'payment_method', 'is_home_service', 'home_address',
            'appointment_services', 'addons', 'traceability',
        ]

    def get_state_description(self, obj):
        if obj.status == models.Appointment.STATUS_ACTIVE:
            from django.utils import timezone
            now = timezone.now()
            first_service = obj.appointment_service.first()
            if first_service and first_service.start_time and first_service.end_time:
                if first_service.start_time <= now <= first_service.end_time:
                    return 'En curso'
        return obj.state.description if obj.state else None

    def get_can_cancel(self, obj):
        return obj.status in [
            models.Appointment.STATUS_PENDING,
            models.Appointment.STATUS_ACTIVE,
        ]

    def get_cancellation_fee_info(self, obj):
        if obj.status == models.Appointment.STATUS_CANCELLED:
            return {
                'fee_amount': float(obj.cancellation_fee),
                'fee_level': obj.cancellation_fee_level,
                'penalty_pct': None,
                'refund_to_party': float(obj.price) - float(obj.cancellation_fee),
                'is_projected': False,
                'message': f"Multa aplicada: ${int(obj.cancellation_fee):,}".replace(',', '.')
            }

        if obj.status not in [
            models.Appointment.STATUS_PENDING,
            models.Appointment.STATUS_ACTIVE,
        ]:
            return None

        # 1. If PENDING, fee is 0 (User rule: no charge if not confirmed)
        if obj.status == models.Appointment.STATUS_PENDING:
            return {
                'fee_amount': 0.0,
                'fee_level': 'low',
                'penalty_pct': 0.0,
                'refund_to_party': float(obj.price),
                'is_projected': True,
                'message': 'Cancelación gratuita (Reserva aún no confirmada)'
            }

        # 2. If ACTIVE, calculate projected fee
        from core import utils
        first_service = obj.appointment_service.first()
        if first_service and first_service.start_time:
            fee_info = utils.calculate_cancellation_fee(
                appointment_start=first_service.start_time,
                service_total=obj.price
            )
            fee_info['is_projected'] = True
            if fee_info['fee_amount'] > 0:
                formatted_fee = f"${int(fee_info['fee_amount']):,}".replace(',', '.')
                fee_info['message'] = (
                    f"Se aplicará una multa de {int(fee_info['penalty_pct']*100)}% "
                    f"({formatted_fee}) por cancelación tardía."
                )
            else:
                fee_info['message'] = "Cancelación gratuita."
            return fee_info

        return None

    def get_can_reschedule(self, obj):
        if obj.status not in [
            models.Appointment.STATUS_PENDING,
            models.Appointment.STATUS_ACTIVE,
        ]:
            return False

        # Max 1 reschedule
        if obj.reschedule_count >= 1:
            return False

        # Min 10 hours notice
        from django.utils import timezone
        from datetime import timedelta
        first_service = obj.appointment_service.first()
        if not first_service or not first_service.start_time:
            return False

        if first_service.start_time < timezone.now() + timedelta(hours=10):
            return False

        return True

    def get_reschedule_message(self, obj):
        if obj.status not in [
            models.Appointment.STATUS_PENDING,
            models.Appointment.STATUS_ACTIVE,
        ]:
            return None

        if obj.reschedule_count >= 1:
            return "Ya has agotado el límite de 1 reprogramación para esta cita."

        from django.utils import timezone
        from datetime import timedelta
        first_service = obj.appointment_service.first()
        if first_service and first_service.start_time:
            if first_service.start_time < timezone.now() + timedelta(hours=10):
                return "No puedes reprogramar faltando menos de 10 horas para la cita."

        return None

    def get_can_review(self, obj):
        return obj.status == models.Appointment.STATUS_COMPLETED


class RescheduleAppointmentSerializer(serializers.Serializer):
    new_start_time = serializers.DateTimeField(
        required=True, input_formats=['iso-8601']
    )
    new_end_time = serializers.DateTimeField(
        required=True, input_formats=['iso-8601']
    )
    worker_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_new_start_time(self, value):
        return _validate_aware(value)

    def validate_new_end_time(self, value):
        return _validate_aware(value)
