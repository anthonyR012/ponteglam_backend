
# Third-party Libraries
from django.urls import path

# Local Modules
from core import views

urlpatterns = [
    path(
        '',
        views.hello_world, name='hello_world'
    ),

]
