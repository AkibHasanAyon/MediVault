from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView,
    VerifyPhoneView,
    ResendOTPView,
    UserProfileView,
    RequestOTPView,
    LogoutView,
)

app_name = 'accounts'

urlpatterns = [
    # Frontend SPA Auth Routes
    path('otp/request/', RequestOTPView.as_view(), name='otp-request'),
    path('otp/verify/', VerifyPhoneView.as_view(), name='otp-verify'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # API Standard Routes
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-phone/', VerifyPhoneView.as_view(), name='verify-phone'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('me/', UserProfileView.as_view(), name='user-profile'),
]


