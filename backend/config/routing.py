from apps.appointments.routing import websocket_urlpatterns as appointments_ws_urls

websocket_urlpatterns = [
    *appointments_ws_urls,
]

