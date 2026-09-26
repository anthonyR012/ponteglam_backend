# Third-party Libraries
from rest_framework import routers

# Local Modules
from notifications.api import views

router = routers.SimpleRouter()

router.register(r'list-user-notifications',
                views.ListUserNotifications,
                basename='user-notifications')


router.register(r'send-user-app-notifications',
                views.SendAppNotificationsViewSet,
                basename='send-app-notifications')


router.register(r'create-campaign-app-notifications',
                views.CreateCampaignAppNotificationsViewSet,
                basename='send-campaign-app-notifications')


router.register(r'send-push-notifications',
                views.SendPushNotificationsViewSet,
                basename='send-push-notifications')

router.register(r'unread-count',
                views.UnreadNotificationsCountViewSet,
                basename='unread-count')

# register-device and token are wired explicitly in notifications/urls.py
# because SimpleRouter cannot map POST + DELETE to the same no-pk URL.
