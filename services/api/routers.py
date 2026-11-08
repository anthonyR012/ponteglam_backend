"""
File for the API routes of the services application
"""

# Third-party Libraries
from rest_framework import routers

# Local Modules
from services.api import views


router = routers.DefaultRouter()

router.register(
    r'create-service', views.CreateService, basename='create-service'
)
router.register(
    r'update-service', views.UpdateService, basename='update-service'
)
router.register(
    r'delete-service', views.DeleteService, basename='delete-service'
)
router.register(
    r'service-detail', views.ServiceDetailView, basename='service-detail'
)
router.register(
    r'service-stats', views.ServiceStatsView, basename='service-stats'
)
router.register(
    r'list-services', views.ListServices, basename='list-services'
)
router.register(
    r'list-categories-services', views.ListCategoriesServices,
    basename='list-categories-services'
)
router.register(
    r'create-appointment', views.CreateAppointment, basename='create-appointment'
)
router.register(
    r'list-appointments', views.ListAppointments, basename='list-appointments'
)
router.register(
    r'supplier-appointments', views.SupplierServiceAppointmentsViewSet, basename='supplier-appointments'
)
router.register(
    r'appointment-detail', views.AppointmentDetail, basename='appointment-detail'
)
router.register(
    r'cancel-appointment', views.CancelAppointment, basename='cancel-appointment'
)
router.register(
    r'reschedule-appointment', views.RescheduleAppointment,
    basename='reschedule-appointment'
)
router.register(
    r'list-reschedule-slots', views.ListRescheduleSlots,
    basename='list-reschedule-slots'
)
router.register(
    r'update-appointment-status', views.UpdateAppointmentStatus,
    basename='update-appointment-status'
)
router.register(
    r'nearby-services', views.NearbyServices, basename='nearby-services'
)
router.register(
    r'confirm-cash-appointment', views.ConfirmCashAppointment,
    basename='confirm-cash-appointment'
)
