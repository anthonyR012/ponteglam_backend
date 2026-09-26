"""
File for the API routes of the ratings application
"""
from rest_framework import routers

from ratings.api import views


router = routers.DefaultRouter()

router.register(
    r'create-rating-headquarter-service', views.CreateHeadquarterServiceRating,
    basename='create-rating-headquarter-service'
)
router.register(
    r'list-ratings-headquarter-service', views.ListHeadquarterServiceRatings,
    basename='list-ratings-headquarter-service'
)
router.register(
    r'create-rating-headquarter', views.CreateHeadquarterRating,
    basename='create-rating-headquarter'
)
router.register(
    r'list-ratings-headquarter', views.ListHeadquarterRatings,
    basename='list-ratings-headquarter'
)

router.register(
    r'reply-rating', views.ReplyHeadquarterServiceRating,
    basename='reply-rating'
)
