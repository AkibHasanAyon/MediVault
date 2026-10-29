from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, VerifyPhoneView, ResendOTPView, UserProfileView

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-phone/', VerifyPhoneView.as_view(), name='verify-phone'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('me/', UserProfileView.as_view(), name='user-profile'),
]

