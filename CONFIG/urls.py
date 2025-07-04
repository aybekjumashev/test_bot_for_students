from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns # Til prefikslari uchun
from tgbot.views import ExportTestsAPIView, GetAllUserTelegramIdsAPIView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Boshqa API yoki maxsus yo'llar (til prefiksisiz)
    path('api/tg/', include('tgbot.urls')), # Telegram bot API uchun
    path('api/export-all-tests/', ExportTestsAPIView.as_view(), name='export_all_tests_api'), 
    path('api/get-all-user-tg-ids/', GetAllUserTelegramIdsAPIView.as_view(), name='get_all_user_tg_ids_api'), 
]

urlpatterns += i18n_patterns(
    # Boshqa ilovalarning URLlari (agar kerak bo'lsa)
    path('', include('core.urls')),
    # prefix_default_language=False # Standart til uchun prefiks qo'shmaslik (masalan, /uz/ -> / )
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)