"""
File for the API routes of the companies application
"""
from rest_framework import routers

from companies.api import views


router = routers.DefaultRouter()

router.register(
    r'create-company', views.CreateCompany, basename='create-company'
)
router.register(
    r'list-companies', views.ListCompanies, basename='list-companies'
)
router.register(
    r'update-company', views.UpdateCompany,
    basename='update-company'
)
router.register(
    r'delete-company', views.DeleteCompany,
    basename='delete-company'
)
router.register(
    r'nequi', views.CompanyNequiViewSet, basename='companies-nequi'
)

