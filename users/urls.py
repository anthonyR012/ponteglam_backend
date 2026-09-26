# Third-party Libraries
from django.urls import path

# Local Modules
from users import views

app_name = 'users'

urlpatterns = [
    path(
        'delete-user-data',
        views.DeleteUserDataView.as_view(), name='delete_user_data'
    ),

]
