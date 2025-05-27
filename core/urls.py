# core/urls.py
from django.urls import path
from .views import (
    UserRegistrationInfoFormView, some_error_page_view, registration_success_page_view,
    EducationTypeListAPIView, InstitutionListAPIView, EducationLevelListAPIView, FacultyListAPIView # Qo'shildi
)
# Keyingi bosqichlarda API viewlarni import qilamiz

app_name = 'core'

urlpatterns = [
    path('register-info/', UserRegistrationInfoFormView.as_view(), name='user_registration_info'),
    # Vaqtinchalik
    path('error-page/', some_error_page_view, name='some_error_page'),
    path('registration-success/', registration_success_page_view, name='registration_success_page'),

    path('api/education-types/', EducationTypeListAPIView.as_view(), name='api_education_types'),
    path('api/institutions/', InstitutionListAPIView.as_view(), name='api_institutions'),
    path('api/education-levels/', EducationLevelListAPIView.as_view(), name='api_education_levels'),
    path('api/faculties/', FacultyListAPIView.as_view(), name='api_faculties'),
]