# third-party Libraries
from rest_framework import serializers

# Local Modules
from services.models import AppointmentService
from workers import models
from users.api.serializers import BaseUserSerializer, PublicUserSerializer

_DT_FORMAT = '%Y-%m-%dT%H:%M:%S%z'


class WorkerSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Worker
        fields = '__all__'
        extra_kwargs = {
            'file': {'required': False},
            'status': {'required': False},
            'type': {'required': False}
        }


class WorkerUserSerializer(PublicUserSerializer):
    worker_id = serializers.SerializerMethodField()

    class Meta(PublicUserSerializer.Meta):
        fields = PublicUserSerializer.Meta.fields + ['worker_id']

    def get_worker_id(self, obj):
        worker = models.Worker.objects.filter(user=obj).first()
        return worker.pk if worker else None


class WorkerFlatSerializer(serializers.ModelSerializer):
    pk = serializers.IntegerField(source='user.pk', read_only=True)
    worker_id = serializers.IntegerField(source='id', read_only=True)
    full_name = serializers.SerializerMethodField()
    picture = serializers.SerializerMethodField()
    gender = serializers.IntegerField(source='user.gender_id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)

    class Meta:
        model = models.Worker
        fields = ['pk', 'worker_id', 'full_name', 'picture', 'gender', 'email', 'phone']

    def get_full_name(self, obj):
        if obj.user:
            return obj.user.full_name
        return obj.name

    def get_picture(self, obj):
        if obj.user and obj.user.picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.picture.url)
            return obj.user.picture.url
        return None


class WorkerAvailabilitySerializer(serializers.Serializer):
    """Serializer para la disponibilidad semanal de un trabajador."""
    WEEKDAY_CHOICES = [(i, name) for i, name in enumerate(
        ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    )]
    weekday = serializers.IntegerField(min_value=0, max_value=6)
    weekday_name = serializers.SerializerMethodField(read_only=True)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()

    def get_weekday_name(self, obj):
        names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        if hasattr(obj, 'weekday'):
            return names[obj.weekday] if 0 <= obj.weekday <= 6 else None
        return None

    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError(
                'start_time debe ser anterior a end_time.'
            )
        return data


class AvailableSlotSerializer(serializers.Serializer):
    worker_id = serializers.IntegerField()
    worker_name = serializers.CharField()
    start_time = serializers.DateTimeField(format=_DT_FORMAT)
    end_time = serializers.DateTimeField(format=_DT_FORMAT)
    only_home_service = serializers.BooleanField()
    home_service_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        allow_null=True,
    )


class AvailableDateWithSlotsSerializer(serializers.Serializer):
    date = serializers.CharField()
    slots = AvailableSlotSerializer(many=True)


class ScheduledAppointmentSerializer(serializers.ModelSerializer):
    appointment_id = serializers.IntegerField(source='appointment.id', read_only=True)
    service_id = serializers.IntegerField(source='service.id', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    worker_id = serializers.IntegerField(source='worker.id', read_only=True)
    worker_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    place = serializers.SerializerMethodField()
    confirmation_in = serializers.DateTimeField(
        source='appointment.confirmation_in', format=_DT_FORMAT, read_only=True
    )
    start_time = serializers.DateTimeField(format=_DT_FORMAT, read_only=True)
    end_time = serializers.DateTimeField(format=_DT_FORMAT, read_only=True)

    class Meta:
        model = AppointmentService
        fields = [
            'id',
            'appointment_id',
            'service_id',
            'service_name',
            'worker_id',
            'worker_name',
            'status',
            'place',
            'confirmation_in',
            'start_time',
            'end_time',
        ]

    def get_worker_name(self, obj):
        return str(obj.worker) if obj.worker else None

    def get_status(self, obj):
        if hasattr(obj.appointment, 'status') and obj.appointment.status:
            # status is a CharField (pending/active/cancelled/completed)
            return {
                'code': obj.appointment.status,
                'name': dict(obj.appointment.STATUS_CHOICES).get(
                    obj.appointment.status, obj.appointment.status
                )
            }
        return None

    def get_place(self, obj):
        if hasattr(obj.appointment, 'place') and obj.appointment.place:
            return str(obj.appointment.place)
        return None

class WorkerBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.WorkerBlock
        fields = '__all__'

    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError('start_time debe ser anterior a end_time.')
        
        # Validación de citas existentes se hará en la View para mayor flexibilidad
        return data


class WorkerInvitationSerializer(serializers.ModelSerializer):
    headquarter_name = serializers.CharField(
        source='headquarter.name', read_only=True
    )

    class Meta:
        model = models.WorkerInvitation
        fields = '__all__'


class StaffMemberSerializer(serializers.ModelSerializer):
    worker_id = serializers.IntegerField(source='id', read_only=True)
    user_details = PublicUserSerializer(source='user', read_only=True)
    services = serializers.SerializerMethodField()

    class Meta:
        model = models.Worker
        fields = [
            'worker_id', 'user_details', 'name', 'status', 'type', 'services'
        ]

    def get_services(self, obj):
        from services.models import WorkerService
        ws = WorkerService.objects.filter(worker=obj).select_related('service')
        return [
            {
                'id': s.service.id,
                'name': s.service.name,
                'code': getattr(s.service, 'code', None),
                'is_pending_removal': s.is_pending_removal,
                'removal_date': s.removal_date.isoformat() if s.removal_date else None
            } for s in ws
        ]


class OnboardWorkerSerializer(serializers.Serializer):
    headquarter_id = serializers.IntegerField(required=True)
    is_anonymous = serializers.BooleanField(default=False)
    name = serializers.CharField(required=False, allow_null=True)
    email = serializers.EmailField(required=False, allow_null=True)
    phone = serializers.CharField(required=False, allow_null=True)

    def validate(self, data):
        if data.get('is_anonymous') and not data.get('name'):
            raise serializers.ValidationError(
                {'name': 'El nombre es obligatorio para trabajadores anónimos.'}
            )
        if not data.get('is_anonymous') and not (data.get('email') or data.get('phone')):
            raise serializers.ValidationError(
                'Debe proporcionar email o teléfono para invitar a un trabajador.'
            )
        return data