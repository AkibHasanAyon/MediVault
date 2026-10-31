import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from django.conf import settings
from apps.common.channels_auth import JWTAuthMiddlewareStack
from config.routing import websocket_urlpatterns

# Wrap HTTP handler with ASGIStaticFilesHandler in DEBUG mode so Daphne
# can serve static files (e.g. Django Admin CSS/JS) dynamically.
if settings.DEBUG:
    from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
    http_handler = ASGIStaticFilesHandler(django_asgi_app)
else:
    http_handler = django_asgi_app

application = ProtocolTypeRouter({
    "http": http_handler,
    "websocket": JWTAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})

