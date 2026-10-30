from django.urls import re_path
from .consumers import ClinicQueueConsumer

websocket_urlpatterns = [
    re_path(r'^ws/queue/(?P<clinic_id>[^/]+)/doctor/(?P<doctor_id>[^/]+)/?$', ClinicQueueConsumer.as_asgi()),
    re_path(r'^ws/queue/(?P<clinic_id>[^/]+)/?$', ClinicQueueConsumer.as_asgi()),
]
