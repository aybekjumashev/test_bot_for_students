from django.urls import path
from .views import (
    UserRegisterAPIView,
    UserDetailAPIView,
    UserSetLanguageAPIView,
    UserSetPhoneAPIView
)

app_name = 'tgbot' # Agar reverse URL kerak bo'lsa

urlpatterns = [
    path('users/register/', UserRegisterAPIView.as_view(), name='user_register'),
    path('users/<int:telegram_id>/', UserDetailAPIView.as_view(), name='user_detail_update'),
    path('users/<int:telegram_id>/set-language/', UserSetLanguageAPIView.as_view(), name='user_set_language'),
    path('users/<int:telegram_id>/set-phone/', UserSetPhoneAPIView.as_view(), name='user_set_phone'),
]