from rest_framework.routers import DefaultRouter

from addons.api.views import (
    ListServiceAddons,
    CreateServiceAddon,
    UpdateServiceAddon,
    DeleteServiceAddon,
    LinkAddonToService,
    UnlinkAddonFromService
)

router = DefaultRouter()

router.register(
    r'list-service-addons',
    ListServiceAddons,
    basename='list-service-addons'
)
router.register(
    r'create-service-addon',
    CreateServiceAddon,
    basename='create-service-addon'
)
router.register(
    r'update-service-addon',
    UpdateServiceAddon,
    basename='update-service-addon'
)
router.register(
    r'delete-service-addon',
    DeleteServiceAddon,
    basename='delete-service-addon'
)
router.register(
    r'link-addon-to-service',
    LinkAddonToService,
    basename='link-addon-to-service'
)
router.register(
    r'unlink-addon-from-service',
    UnlinkAddonFromService,
    basename='unlink-addon-from-service'
)

urlpatterns = router.urls
