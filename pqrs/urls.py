from django.urls import path
from pqrs import views

app_name = 'pqrs'

urlpatterns = [
    path('', views.PQRSHomeView.as_view(), name='home'),
    path('crear/', views.PQRSCrearView.as_view(), name='crear'),
    path('consultar/', views.PQRSConsultarView.as_view(), name='consultar'),
    path('detalle/<str:radicado>/', views.PQRSDetalleView.as_view(), name='detalle'),
    path('confirmacion/<str:radicado>/', views.PQRSConfirmacionView.as_view(), name='confirmacion'),
]