# Third-party Libraries
from rest_framework import routers

# Local Modules
from workers.api import views

router = routers.SimpleRouter()

router.register(r'create-worker', views.CreateWorker, basename='create-worker')
router.register(r'list-workers', views.ListWorkers, basename='list-workers')
router.register(r'list-available-workers',
                views.ListAvailableSlots, basename='list-available-workers')
router.register(r'appointments/scheduled', views.ScheduledAppointmentsViewSet,
                basename='appointments-scheduled')
router.register(r'manage-staff', views.StaffManagementViewSet, basename='manage-staff')
router.register(r'my-invitations', views.UserInvitationViewSet, basename='my-invitations')
router.register(r'worker-availability', views.WorkerAvailabilityView,
                basename='worker-availability')
