from django.urls import path
from .views.assistant_views import (
    AssignQueueTokenView,
    TodayQueueRosterView,
    UpdateQueueStatusView,
    DailyQueueSummaryView,
)

urlpatterns = [
    path('assign-token/', AssignQueueTokenView.as_view(), name='assistant-queue-assign-token'),
    path('today/', TodayQueueRosterView.as_view(), name='assistant-queue-today'),
    path('<uuid:pk>/status/', UpdateQueueStatusView.as_view(), name='assistant-queue-status-update'),
    path('daily-summary/', DailyQueueSummaryView.as_view(), name='assistant-queue-daily-summary'),
]

