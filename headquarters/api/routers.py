"""
File for the API routes of the headquarters application
"""
from rest_framework import routers

from headquarters.api import views


router = routers.DefaultRouter()

router.register(
    r'create-headquarter', views.CreateHeadquarter,
    basename='create-headquarter'
)
router.register(
    r'update-headquarter', views.UpdateHeadquarter,
    basename='update-headquarter'
)
router.register(
    r'delete-headquarter', views.DeleteHeadquarter,
    basename='delete-headquarter'
)
router.register(
    r'create-week-day-time-configuration',
    views.CreateWeekDayTimeConfiguration,
    basename='create-week-day-time-configuration'
)
router.register(
    r'get-week-configuration-headquarter',
    views.GetHeadquarterWeekConfiguration,
    basename='get-week-configuration-headquarter'
)
router.register(
    r'headquarter-like', views.HeadquarterLikeView,
    basename='headquarter-like'
)
router.register(
    r'headquarter-dislike', views.HeadquarterDislikeView,
    basename='headquarter-dislike'
)
router.register(
    r'headquarter-detail', views.HeadquarterDetailView,
    basename='headquarter-detail'
)
