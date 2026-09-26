"""
ASGI config for ponteglam project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import services.ws.routing
import chats.ws.routing
from channels.routing import ProtocolTypeRouter, URLRouter
from ponteglam.middleware import TokenAuthMiddleware
import os
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ponteglam.settings')

urls = []

urls.extend(chats.ws.routing.websocket_urlpatterns)
urls.extend(services.ws.routing.websocket_urlpatterns)

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': TokenAuthMiddleware(
        URLRouter(
            urls
        )
    ),
})
