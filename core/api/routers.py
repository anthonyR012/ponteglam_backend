"""
File for the API routes of the core application
"""

# Python Standard Library
from rest_framework import routers

# Local Modules
from core.api import views


router = routers.DefaultRouter()

router.register(
    r'list-types', views.ListTypes, basename='list-types'
)
router.register(
    r'list-countries', views.ListCountries, basename='list-countries'
)
router.register(
    r'list-cities', views.ListCities, basename='list-cities'
)
router.register(
    r'create-mobile-app-log', views.CreateMobileAppLogView,
    basename='create-mobile-app-log'
)
router.register(
    r'list-amenities', views.ListAmenities, basename='list-amenities'
)
router.register(
    r'list-legal-content', views.ListLegalContent, basename='list-legal-content'
)
