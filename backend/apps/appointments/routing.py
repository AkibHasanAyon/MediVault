from django.urls import re_path
from .consumers import ClinicQueueConsumer

websocket_urlpatterns = [
    re_path(r'^ws/queue/(?P<clinic_id>[0-9a-f-]+)/doctor/(?P<doctor_id>[0-9a-f-]+)/?$', ClinicQueueConsumer.as_asgi()),
    re_path(r'^ws/queue/(?P<clinic_id>[0-9a-f-]+)/?$', ClinicQueueConsumer.as_asgi()),
]

