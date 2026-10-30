from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AskAIView, AIConversationViewSet

router = DefaultRouter()
router.register('conversations', AIConversationViewSet, basename='ai-conversations')

urlpatterns = [
    path('ask/', AskAIView.as_view(), name='ai-ask'),
    path('', include(router.urls)),
]

