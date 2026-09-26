"""
File for the API routes of the users application
"""

# Python Standard Library

# Third-party Libraries
from rest_framework import routers

# Local Modules
from users.api import views

router = routers.SimpleRouter()

router.register(
    r'register-oauth', views.RegistrationOauthAPI, basename='register-oauth'
)
router.register(
    r'register-alternate', views.RegistrationAlternateAPI,
    basename='register-alternate'
)
router.register(
    r'verify-email', views.VerifyEmail, basename='verify-email'
)
router.register(
    r'forward-verification-email', views.ForwardVerificationEmail,
    basename='forward-verification-email'
)
router.register(
    r'request-recover-user', views.RequestRecoverUser,
    basename='request-recover-user'
)
router.register(
    r'verify-email-recover-user', views.VerifyEmailRecoverUser,
    basename='verify-email-recover-user'
)
router.register(
    r'request-create-password', views.RequestCreatePassword,
    basename='request-create-password'
)
router.register(
    r'confirm-create-password', views.ConfirmCreatePassword,
    basename='confirm-create-password'
)
router.register(
    r'update-password', views.UpdatePassword,
    basename='update-password'
)
router.register(
    r'update-information', views.UpdateUserInfo, basename='update-user-info'
)
router.register(
    r'create-user-address', views.CreateUserAddress,
    basename='create-user-address'
)
router.register(
    r'list-user-address', views.ListUserAddresses,
    basename='list-user-address'
)
router.register(
    r'update-user-address', views.UpdateUserAddress,
    basename='update-user-address'
)
router.register(
    r'delete-user-address', views.DeleteUserAddress,
    basename='delete-user-address'
)
router.register(
    r'me', views.MeView, basename='me'
)
router.register(
    r'terms-and-conditions', views.UserTermsAndConditionsView,
    basename='terms-and-conditions'
)
router.register(
    r'logout', views.LogoutUser, basename='logout'
)
