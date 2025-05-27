# core/urls.py
from django.urls import path
from .views import (
    UserRegistrationInfoFormView, some_error_page_view, registration_success_page_view,
    EducationTypeListAPIView, InstitutionListAPIView, EducationLevelListAPIView, FacultyListAPIView,
    PrepareTestView, StartMixedTestView, TestInProgressView, SubmitTestView
)
from django.http import HttpResponse # Vaqtinchalik view uchun

# Vaqtinchalik SubmitTestView (keyinroq haqiqiysiga almashtiriladi)
def dummy_submit_test_view(request):
    test_id = request.session.get('current_test_id')
    user_answers = request.session.get(f'test_{test_id}_answers', {})
    time_spent = request.session.get('time_spent_on_test', 'N/A')

    # Bu yerda natijalarni hisoblash va saqlash logikasi bo'ladi
    # Hozircha, shunchaki ma'lumotlarni ko'rsatamiz
    response_html = f"<h1>Test Yakunlandi (Test ID: {test_id})</h1>"
    response_html += f"<p>Sarflangan vaqt: {time_spent} sekund</p>"
    response_html += "<h2>Javoblar:</h2><ul>"
    for q_id, ans in user_answers.items():
        response_html += f"<li>Savol ID {q_id}: Javob {ans}</li>"
    response_html += "</ul> <p>Bu sahifa hali to'liq tayyor emas. Natijalar hisoblanadi...</p>"
    
    # Sessiondagi test ma'lumotlarini tozalash (ixtiyoriy, test tugagandan keyin)
    # request.session.pop('current_test_id', None)
    # request.session.pop('current_question_index', None)
    # request.session.pop(f'test_{test_id}_answers', None)
    # request.session.pop('time_spent_on_test', None)
    # request.session.pop('test_submitted_for_processing', None)

    return HttpResponse(response_html)


app_name = 'core'

urlpatterns = [
    path('register-info/', UserRegistrationInfoFormView.as_view(), name='user_registration_info'),
    path('error-page/', some_error_page_view, name='some_error_page'),
    path('registration-success/', registration_success_page_view, name='registration_success_page'),

    # API endpointlari
    path('api/education-types/', EducationTypeListAPIView.as_view(), name='api_education_types'),
    path('api/institutions/', InstitutionListAPIView.as_view(), name='api_institutions'),
    path('api/education-levels/', EducationLevelListAPIView.as_view(), name='api_education_levels'),
    path('api/faculties/', FacultyListAPIView.as_view(), name='api_faculties'),

    # Test bilan bog'liq URLlar
    path('prepare-test/', PrepareTestView.as_view(), name='prepare_test'),
    path('start-mixed-test/', StartMixedTestView.as_view(), name='start_mixed_test'),
    path('test-in-progress/', TestInProgressView.as_view(), name='test_in_progress'),
    
    # Testni yakunlash/natijalarni ko'rish uchun URL (vaqtinchalik view bilan)
    path('submit-test/', SubmitTestView.as_view(), name='submit_test'),
]