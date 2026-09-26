from django.urls import include, path

from notifications.api.routers import router
from notifications.api.views import (
    DeleteFcmToken,
    RegisterDeviceViewSet,
    RegisterFcmToken,
)

_FcmTokenView = type(
    '_FcmTokenView',
    (RegisterFcmToken, DeleteFcmToken),
    {},
).as_view({'post': 'create', 'delete': 'destroy'})

_RegisterDeviceView = RegisterDeviceViewSet.as_view(
    {'post': 'create', 'delete': 'destroy'}
)

urlpatterns = [
    path('', include(router.urls)),
    path('token/', _FcmTokenView, name='fcm-token'),
    path('register-device/', _RegisterDeviceView, name='register-device'),
]
