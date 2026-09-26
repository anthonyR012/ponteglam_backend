"""
URL configuration for ponteglam project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from users.api.views import CustomAuthToken

from blogs.api.routers import router as blogs_router
from chats.api.routers import router as chats_ruoter
from companies.api.routers import router as companies_router
from core.api.routers import router as core_router
from headquarters.api.routers import router as headquarters_router
from ratings.api.routers import router as ratings_router
from reports.api.routers import router as reports_ruoter
from services.api.routers import router as services_router
from users.api.routers import router as users_ruoter
from workers.api.routers import router as workers_router
from addons.api.routers import router as addons_router

urlpatterns = [
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
    path('api-token-auth/', CustomAuthToken.as_view()),
    
    # Swagger & Redoc
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    path('pqrs/', include('pqrs.urls')),
    path('addons/api/', include(addons_router.urls)),
    path('blogs/api/', include(blogs_router.urls)),
    path('chats/api/', include(chats_ruoter.urls)),
    path('companies/api/', include(companies_router.urls)),
    path('core/api/', include(core_router.urls)),
    path('headquarters/api/', include(headquarters_router.urls)),
    path('ratings/api/', include(ratings_router.urls)),
    path('reports/api/', include(reports_ruoter.urls)),
    path('services/api/', include(services_router.urls)),
    path('users/', include('users.urls')),
    path('users/api/', include(users_ruoter.urls)),
    path('notifications/api/', include('notifications.urls')),
    path('workers/api/', include(workers_router.urls)),
    path('transactions/', include('transactions.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
