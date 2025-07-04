# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages # Foydalanuvchiga xabar berish uchun
from django.urls import reverse_lazy, reverse # reverse_lazy FormView uchun, reverse redirect uchun
from django.utils.translation import gettext_lazy as _
from django.utils.translation import activate # Tilni aktivlashtirish uchun
from .forms import UserRegistrationInfoForm
from .models import User, EducationType, Institution, EducationLevel, Faculty, Test, Subject
from django.http import HttpRequest, HttpResponse
import random
from django.db import transaction # Atomik operatsiyalar uchun
from django.utils import timezone # datetime.now() o'rniga

from rest_framework.generics import ListAPIView
from .serializers import (
    EducationTypeSerializer, InstitutionSerializer,
    EducationLevelSerializer, FacultySerializer
)
from django.http import JsonResponse, Http404 # JsonResponse va Http404
from .utils import convert_docx_to_html # Avval yaratgan utils.py dan
from tgbot.utils import send_test_result_to_user
import logging
import os
from asgiref.sync import async_to_sync
logger = logging.getLogger(__name__)


class UserRegistrationInfoFormView(View):
    form_class = UserRegistrationInfoForm
    template_name = 'registration_info_form.html' # Shablon nomi

    def get(self, request: HttpRequest, *args, **kwargs):
        print(f"Current language in view: {request.LANGUAGE_CODE}")
        telegram_id = request.GET.get('tgWebAppStartParam')
        if not telegram_id:
            messages.error(request, _("Telegram ID topilmadi. Iltimos, bot orqali qayta urinib ko'ring."))
            # Yoki botga qaytaradigan sahifaga yo'naltirish
            return redirect(reverse('core:some_error_page')) # Misol, error page yaratish kerak bo'ladi

        try:
            user = User.objects.get(telegram_id=telegram_id)
            # Foydalanuvchi tilini aktivlashtirish
            if user.language_code:
                activate(user.language_code)
        except User.DoesNotExist:
            messages.error(request, _("Foydalanuvchi topilmadi. Iltimos, botda /start buyrug'ini bering."))
            return redirect(reverse('core:some_error_page')) # Misol
        
        if Test.objects.filter(user=user, score__isnull=False).exists():
            messages.info(request, _("Siz allaqachon test topshirgansiz."))
            # Natijalar sahifasiga yo'naltirish yoki boshqa joyga
            # Masalan, user_profile sahifasiga:
            # return redirect(reverse('core:user_profile') + f'?user_tg_id={user.telegram_id}')
            prepare_test_url = reverse('core:prepare_test') + f'?user_tg_id={user.telegram_id}'
            return redirect(prepare_test_url)
            # return render(request, 'test_already_completed.html', {'user': user})

        # Agar foydalanuvchi allaqachon ma'lumotlarini to'ldirgan bo'lsa (masalan, institution mavjud bo'lsa)
        # uni fanlar sahifasiga yo'naltirish mumkin. Bu logikani keyinroq qo'shamiz.
        # if user.institution:
        #     return redirect(reverse('core:subjects_list')) # Faraziy URL

        form = self.form_class(instance=user) # Mavjud ma'lumotlar bilan formani to'ldirish
        form.fields['telegram_id_hidden'].initial = telegram_id # Yashirin maydonni to'ldirish
        return render(request, self.template_name, {'form': form, 'telegram_user_id': telegram_id, 'lang': user.language_code})

    def post(self, request, *args, **kwargs):
        telegram_id_from_form = request.POST.get('telegram_id_hidden') # Yashirin maydondan olish
        # Yoki URL dan olish (agar URLda telegram_id bo'lsa, lekin WebApp URLida GET parametrda keladi)
        telegram_id_from_get = request.GET.get('tgWebAppStartParam')

        telegram_id = telegram_id_from_form or telegram_id_from_get
        print(telegram_id)

        if not telegram_id:
            print('tg_id')
            messages.error(request, _("Telegram ID topilmadi. Xatolik."))
            return redirect(reverse('core:some_error_page')) # Misol

        try:
            user = User.objects.get(telegram_id=telegram_id)
            if user.language_code:
                activate(user.language_code)
        except User.DoesNotExist:
            print('user')
            messages.error(request, _("Foydalanuvchi topilmadi. Qayta urinib ko'ring."))
            return redirect(reverse('core:some_error_page')) # Misol

        form = self.form_class(request.POST, instance=user) # POST ma'lumotlari va mavjud user bilan

        if form.is_valid():
            form.save()
            messages.success(request, _("Ma'lumotlaringiz muvaffaqiyatli saqlandi!"))
            prepare_test_url = reverse('core:prepare_test') + f'?user_tg_id={user.telegram_id}'
            return redirect(prepare_test_url)
        else:
            print(form.errors)
            # Xatoliklarni ko'rsatish uchun formani qayta render qilish
            # Yashirin maydonni qayta to'ldirish (agar yo'qolgan bo'lsa)
            if not form.data.get('telegram_id_hidden') and telegram_id:
                mutable_post = request.POST.copy()
                mutable_post['telegram_id_hidden'] = telegram_id
                form = self.form_class(mutable_post, instance=user)
                # Formani qayta validatsiya qilish shart emas, chunki xatolar allaqachon mavjud
            messages.error(request, _("Formani to'ldirishda xatoliklar mavjud. Iltimos, tekshirib qayta urinib ko'ring."))
        return render(request, self.template_name, {'form': form, 'telegram_user_id': telegram_id})


# Vaqtinchalik sahifalar (keyinroq to'g'rilanadi)
def some_error_page_view(request):
    return render(request, 'error_page.html', {'message': _("Xatolik yuz berdi.")})

def registration_success_page_view(request):
    # Foydalanuvchiga telegram orqali WebAppni yopishni aytish kerak bo'lishi mumkin
    # Bu yerda telegram.WebApp.close() ni chaqirish uchun JS kerak bo'ladi
    return render(request, 'registration_success.html', {'message': _("Muvaffaqiyatli ro'yxatdan o'tdingiz!")})




class EducationTypeListAPIView(ListAPIView):
    queryset = EducationType.objects.all().order_by('id') # Yoki name_uz bo'yicha
    serializer_class = EducationTypeSerializer
    # permission_classes = [AllowAny] # Hamma uchun ochiq

class InstitutionListAPIView(ListAPIView):
    serializer_class = InstitutionSerializer
    # permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Institution.objects.all()
        education_type_id = self.request.query_params.get('education_type_id')
        if education_type_id:
            queryset = queryset.filter(education_type_id=education_type_id)
        return queryset.order_by('id') # Yoki name_uz bo'yicha

class EducationLevelListAPIView(ListAPIView): # OTM uchun
    queryset = EducationLevel.objects.all().order_by('id')
    serializer_class = EducationLevelSerializer
    # permission_classes = [AllowAny]
    # Agar faqat OTM tanlanganda kerak bo'lsa, bu yerda ham filtr qo'shish mumkin,
    # lekin hozircha barchasini qaytaramiz, JS logikasi hal qiladi.

class FacultyListAPIView(ListAPIView):
    serializer_class = FacultySerializer
    # permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Faculty.objects.all()
        institution_id = self.request.query_params.get('institution_id')
        if institution_id:
            queryset = queryset.filter(institution_id=institution_id)
        return queryset.order_by('id') # Yoki name_uz bo'yicha




class PrepareTestView(View): # Nomini o'zgartirdim, bu sahifa testga tayyorgarlikni ko'rsatadi
    template_name = 'prepare_test.html'

    def get(self, request, *args, **kwargs):
        user_telegram_id = request.GET.get('user_tg_id')
        print('prep')
        if not user_telegram_id:            
            # ... xatolikni boshqarish ...
            return redirect(reverse('core:user_registration_info'))
        try:
            user = User.objects.get(telegram_id=user_telegram_id)
            if user.language_code:
                activate(user.language_code)
        except User.DoesNotExist:
            # ... xatolikni boshqarish ...
            print('user not found')
            return redirect(reverse('core:user_registration_info'))

        # Foydalanuvchi allaqachon ARALASH test topshirganmi?
        # Buni aniqlash uchun Test modelida "test_type" kabi maydon qo'shish mumkin,
        # yoki hozircha, agar subject bo'lmagan test bo'lsa, uni aralash deb hisoblash.
        # Yoki user uchun faqat bitta topshirilgan test bo'lishini tekshirish.
        # Hozircha, agar user uchun score bilan tugagan test bo'lsa, qayta topshirmaydi deb hisoblaymiz.
        back = True
        if Test.objects.filter(user=user, score__isnull=False).exists():
            back = False
        #     messages.info(request, _("Siz allaqachon test topshirgansiz."))
        #     # Natijalar sahifasiga yo'naltirish yoki boshqa joyga
        #     # Masalan, user_profile sahifasiga:
        #     # return redirect(reverse('core:user_profile') + f'?user_tg_id={user.telegram_id}')
        #     return render(request, 'test_already_completed.html', {'user': user})


        # Qancha savol borligini va test haqida ma'lumotni shablonga yuborish
        user_course = user.course_year if user.course_year else 0
        active_subjects = Subject.objects.filter(
            is_active=True,
            min_course_year__lte=user_course,
            max_course_year__gte=user_course
        ).prefetch_related('questions')

        total_questions_for_test = 0
        questions_per_subject = 3
        possible_subjects_for_test = []

        for subject in active_subjects:
            num_available_questions = subject.questions.filter(is_active=True).count()
            if num_available_questions >= questions_per_subject:
                total_questions_for_test += questions_per_subject
                possible_subjects_for_test.append(subject.get_localized_name())
            elif num_available_questions > 0 : # Agar 5 tadan kam bo'lsa, borini oladi
                total_questions_for_test += num_available_questions
                possible_subjects_for_test.append(subject.get_localized_name())


        if total_questions_for_test == 0:
            print('no questions')
            messages.error(request, _("Test uchun savollar mavjud emas."))
            # Bosh sahifaga yoki xatolik sahifasiga
            return redirect(reverse('core:user_registration_info')) # Yoki boshqa joyga

        context = {
            'user': user,
            'total_questions_for_test': total_questions_for_test,
            'subjects_in_test': ", ".join(possible_subjects_for_test),
            'questions_per_subject': questions_per_subject, # Bu shartli bo'lishi mumkin
            'back': back
        }
        return render(request, self.template_name, context)


class StartMixedTestView(View):
    @transaction.atomic # Test yaratish va savollarni biriktirish atomik bo'lishi uchun
    def post(self, request, *args, **kwargs): # GET o'rniga POST, chunki test yaratiladi
        user_telegram_id = request.POST.get('user_tg_id') # Formadan keladi
        if not user_telegram_id:
            # ... xatolik ...
            return redirect(reverse('core:user_registration_info'))
        try:
            user = User.objects.get(telegram_id=user_telegram_id)
            if user.language_code:
                activate(user.language_code)
        except User.DoesNotExist:
            # ... xatolik ...
            return redirect(reverse('core:user_registration_info'))

        # if Test.objects.filter(user=user, score__isnull=False).exists():
        #     return redirect(reverse('core:prepare_test') + f'?user_tg_id={user_telegram_id}') # Qayta prepare sahifasiga

        user_course = user.course_year if user.course_year else 0
        active_subjects = Subject.objects.filter(
            is_active=True,
            min_course_year__lte=user_course,
            max_course_year__gte=user_course
        ).prefetch_related('questions')

        all_selected_questions = []
        questions_per_subject = 3

        for subject in active_subjects:
            # Joriy til uchun fayli bor aktiv savollarni olish
            # Bu qism biroz murakkab, chunki har bir savolni tekshirish kerak
            # Yaxshiroq yo'li - Question modeliga property qo'shish yoki queryni optimallashtirish
            
            potential_questions = []
            for q in subject.questions.filter(is_active=True):
                if q.get_question_file_for_current_lang(): # Joriy til uchun fayl bormi?
                    potential_questions.append(q)

            if len(potential_questions) >= questions_per_subject:
                all_selected_questions.extend(random.sample(potential_questions, questions_per_subject))
            elif len(potential_questions) > 0:
                 all_selected_questions.extend(potential_questions)

        if not all_selected_questions:
            messages.error(request, _("Test uchun savollar topilmadi."))
            return redirect(reverse('core:prepare_test') + f'?user_tg_id={user_telegram_id}')

        # Yangi Test obyektini yaratish (subject endi yo'q)
        new_test = Test.objects.create(user=user, started_at=timezone.now())
        new_test.questions.set(all_selected_questions)
        
        request.session['current_test_id'] = new_test.id
        request.session['current_question_index'] = 0
        
        return redirect(reverse('core:test_in_progress')) # Keyingi qadamda yaratiladi
    


class TestInProgressView(View):
    template_name = 'test_in_progress.html'

    def get_current_test_and_user(self, request):
        test_id = request.session.get('current_test_id')
        if not test_id:
            raise Http404(_("Aktiv test topilmadi. Iltimos, testni qayta boshlang."))
        
        try:
            # Testni va unga bog'liq user va questions'ni oldindan yuklash
            test_instance = Test.objects.select_related('user').prefetch_related('questions__subject').get(id=test_id)
            user = test_instance.user
            if user.language_code:
                activate(user.language_code)
            return test_instance, user
        except Test.DoesNotExist:
            raise Http404(_("Test topilmadi."))

    def get(self, request, *args, **kwargs):
        try:
            test_instance, user = self.get_current_test_and_user(request)
        except Http404 as e:
            messages.error(request, str(e))
            # Agar user_id ni bilsak, prepare_test ga qaytarish yaxshiroq
            # Hozircha, xatolik sahifasiga
            return redirect(reverse('core:some_error_page'))


        # Sessiondan joriy savol indeksini olish
        question_index = request.session.get('current_question_index', 0)
        all_questions_in_test = list(test_instance.questions.all().order_by('id')) # Yoki boshqa tartibda

        if not all_questions_in_test:
            messages.error(request, _("Testda savollar topilmadi."))
            return redirect(reverse('core:prepare_test') + f'?user_tg_id={user.telegram_id}')

        if question_index >= len(all_questions_in_test):
            # Barcha savollar tugagan, natijalar sahifasiga o'tish kerak
            # Bu holat GET so'rovida bo'lmasligi kerak, lekin har ehtimolga qarshi
            return redirect(reverse('core:submit_test')) # SubmitTestView ni hali yaratmadik

        current_question = all_questions_in_test[question_index]
        question_file_to_render = current_question.get_question_file_for_current_lang() # YANGILANDI

        if not question_file_to_render:
            # Bu holat bo'lmasligi kerak, agar savollar to'g'ri filtrlangan bo'lsa
            logger.error(f"Test {test_instance.id}, Savol {current_question.id} uchun joriy tilda fayl topilmadi!")
            question_html = f"<p>{_('Savol matni topilmadi.')}</p>"
        else:
            question_html = convert_docx_to_html(question_file_to_render) # YANGILANDI

        # Foydalanuvchining bu savolga bergan javobini sessiondan olish (agar mavjud bo'lsa)
        user_answers = request.session.get(f'test_{test_instance.id}_answers', {})
        previous_answer = user_answers.get(str(current_question.id))

        context = {
            'test': test_instance,
            'user': user,
            'current_question': current_question,
            'question_html': question_html,
            'question_number': question_index + 1,
            'total_questions': len(all_questions_in_test),
            'previous_answer': previous_answer, # Oldingi javobni shablonga yuborish
            'time_limit_minutes': len(all_questions_in_test),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs): # Javobni qabul qilish va keyingi savolga o'tish
        try:
            test_instance, user = self.get_current_test_and_user(request)
        except Http404 as e:
            return JsonResponse({'error': str(e), 'success': False}, status=404)

        data = request.POST
        question_id = data.get('question_id')
        selected_answer = data.get('answer') # 'a', 'b', 'c', 'd'
        action = data.get('action') # 'next', 'prev', 'submit'

        if not question_id or not selected_answer:
            # Agar javob berilmagan bo'lsa ham, action 'next' bo'lsa o'tkazish mumkin
            if action != 'next_unanswered' and action != 'prev': # Javobsiz o'tish uchun alohida action
                # Bu yerda xatolik berish shart emas, agar foydalanuvchi javob bermasdan o'tkazsa
                pass
                # return JsonResponse({'error': _("Savol ID si yoki javob yetishmayapti."), 'success': False}, status=400)


        # Foydalanuvchi javoblarini sessionda saqlash
        user_answers = request.session.get(f'test_{test_instance.id}_answers', {})
        if question_id and selected_answer: # Faqat javob berilgan bo'lsa saqlash
            user_answers[str(question_id)] = selected_answer
        request.session[f'test_{test_instance.id}_answers'] = user_answers
        request.session.modified = True # Session o'zgartirilganini bildirish

        # Joriy savol indeksini olish va yangilash
        question_index = request.session.get('current_question_index', 0)
        all_questions_in_test = list(test_instance.questions.all().order_by('id'))

        if action == 'next' or action == 'next_unanswered':
            question_index += 1
        elif action == 'prev':
            question_index -= 1
        elif action == 'submit_test': # Testni yakunlash
            # Vaqtni ham POSTda olish kerak yoki serverda hisoblash
            time_spent = data.get('time_spent') # Frontenddan keladigan vaqt
            request.session['time_spent_on_test'] = time_spent # Sessionga saqlash

            # Bu yerda Test.objects.update(...) qilish o'rniga,
            # alohida SubmitTestView ga redirect qilish yaxshiroq.
            # Hozircha, sessiyaga 'test_submitted' flagini qo'yib, GETga redirect qilamiz.
            request.session['test_submitted_for_processing'] = True
            return JsonResponse({'success': True, 'redirect_url': reverse('core:submit_test')})


        # Indeks chegaralarini tekshirish
        if question_index < 0:
            question_index = 0
        # Agar oxirgi savoldan o'tib ketsa, lekin hali submit qilinmagan bo'lsa
        # (bu holat bo'lmasligi kerak, frontendda submit tugmasi bo'ladi)
        # if question_index >= len(all_questions_in_test):
        #     return JsonResponse({'success': True, 'finished': True, 'redirect_url': reverse('core:submit_test')})


        request.session['current_question_index'] = question_index
        request.session.modified = True

        # Agar barcha savollar tugagan bo'lsa va keyingi bosilsa (yoki oxirgi savoldan keyin)
        if question_index >= len(all_questions_in_test):
             return JsonResponse({'success': True, 'finished': True, 'message': _("Barcha savollarga javob berildi. Testni yakunlang.")})


        # Keyingi savolni yuklash uchun ma'lumotlarni qaytarish (AJAX so'rovi uchun)
        next_question_obj = all_questions_in_test[question_index]
        next_question_file_to_render = next_question_obj.get_question_file_for_current_lang() # YANGILANDI

        if not next_question_file_to_render:
            logger.error(f"Test {test_instance.id}, Keyingi savol {next_question_obj.id} uchun joriy tilda fayl topilmadi!")
            next_question_html = f"<p>{_('Savol matni topilmadi.')}</p>"
        else:
            next_question_html = convert_docx_to_html(next_question_file_to_render) # YANGILANDI
            
        previous_answer_for_next_q = user_answers.get(str(next_question_obj.id))


        return JsonResponse({
            'success': True,
            'question_id': next_question_obj.id,
            'question_html': next_question_html,
            'question_number': question_index + 1,
            'total_questions': len(all_questions_in_test),
            'previous_answer': previous_answer_for_next_q, # Yangi savol uchun oldingi javob (agar bo'lsa)
            'is_first': question_index == 0,
            'is_last': question_index == len(all_questions_in_test) - 1,
        })


class SubmitTestView(View):
    template_name = 'test_results.html' # Shablon nomini to'g'riladim

    @transaction.atomic
    def get(self, request, *args, **kwargs):
        test_id = request.session.get('current_test_id')
        user_answers_session = request.session.get(f'test_{test_id}_answers', {})
        time_spent_str = request.session.get('time_spent_on_test', '0')
        
        if not request.session.get('test_submitted_for_processing', False):
            # ... (avvalgidek) ...
            messages.warning(request, _("Test hali yakunlanmagan yoki allaqachon qayta ishlangan."))
            return redirect(reverse('core:some_error_page'))


        if not test_id:
            # ... (avvalgidek) ...
            messages.error(request, _("Test ID si topilmadi. Natijalarni ko'rsatib bo'lmaydi."))
            return redirect(reverse('core:some_error_page'))

        try:
            test_instance = Test.objects.select_related('user').prefetch_related('questions__subject').get(id=test_id)
            user = test_instance.user
            if user.language_code:
                activate(user.language_code)
        except Test.DoesNotExist:
            # ... (avvalgidek) ...
            messages.error(request, _("Test topilmadi."))
            return redirect(reverse('core:some_error_page'))

        if test_instance.score is not None and test_instance.completed_at is not None:
            # ... (avvalgidek) ...
            # Agar test allaqachon qayta ishlangan bo'lsa va voucher yuborilgan bo'lsa,
            # shunchaki natijalar sahifasini context bilan render qilish yaxshiroq.
            # Hozircha HttpResponse qoldiramiz, keyin yaxshilaymiz.
            return HttpResponse(f"Test {test_id} allaqachon yakunlangan. Natija: {test_instance.score}")


        correct_answers_count = 0
        test_questions = test_instance.questions.all()
        detailed_results = []

        for question in test_questions:
            user_answer = user_answers_session.get(str(question.id))
            is_correct = (user_answer == question.correct_answer)
            if is_correct:
                correct_answers_count += 1
            detailed_results.append({
                'question_id': question.id,
                'question_text_preview': "%s - %s %s" % (question.subject.get_localized_name(),_('Savol'),question.id),
                'user_answer': user_answer,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct,
                'question_file_url': question.get_question_file_for_current_lang().url if question.get_question_file_for_current_lang() else None,
            })
        
        test_instance.score = correct_answers_count
        test_instance.completed_at = timezone.now()
        try:
            test_instance.time_spent_seconds = int(time_spent_str)
        except ValueError:
            test_instance.time_spent_seconds = 0
        
        total_q_count = test_questions.count() if test_questions.exists() else 1 # exists() bilan tekshirish yaxshiroq
        percentage_correct = (correct_answers_count / total_q_count) * 100 if total_q_count > 0 else 0
        test_instance.voucher_code = f"IBT{timezone.now().strftime('%m%d')}{test_instance.id}{random.randint(1, 9)}"   
        
        # test_instance ni birinchi marta saqlash (voucher_code bilan, voucher_sent hali False)
        test_instance.save()
        logger.info(f"Test {test_id} natijalari saqlandi. Hisob: {test_instance.score}, Voucher kodi: {test_instance.voucher_code}")

        # Telegramga xabar yuborish
        message_was_sent_to_user = False
        if user.telegram_id: 
            logger.info(f"Telegramga yuborish boshlandi: User {user.telegram_id}")
            try:
                message_was_sent_to_user = async_to_sync(send_test_result_to_user)(
                    user_telegram_id=int(user.telegram_id), # Int ga o'tkazish
                    user_fullname=(user.name or '', user.surname or '', user.patronymic or ''), # Foydalanuvchi ismi va familiyasini olish
                    score=(correct_answers_count, round(percentage_correct, 1)),
                    total_questions=total_q_count,
                    voucher_code=(test_instance.id, test_instance.voucher_code),
                )
                logger.info(f"Telegramga yuborish statusi (user {user.telegram_id}): {message_was_sent_to_user}")

                if message_was_sent_to_user:
                    test_instance.voucher_sent = True
                    test_instance.save(update_fields=['voucher_sent'])
                    logger.info(f"Test {test_id} uchun voucher_sent=True qilib saqlandi.")
                else:
                    logger.error(f"Test {test_id} uchun Telegramga xabar YUBORILMADI (send_test_result_to_user False qaytardi).")

            except Exception as e:
                logger.error(f"SubmitTestView: Telegramga xabar yuborishda KRITIK xatolik (test {test_id}): {e}", exc_info=True)
        elif not user.telegram_id:
            logger.warning(f"Test {test_id} uchun foydalanuvchining telegram_id si yo'q.")


        context = {
            'test': test_instance,
            'user': user,
            'correct_answers_count': correct_answers_count,
            'total_questions': total_q_count,
            'percentage_correct': round(percentage_correct, 1),
            'detailed_results': detailed_results,
            'user_answers_session': user_answers_session,
            'voucher_type': "",
            'voucher_amount_text': "", 
            'voucher_code': test_instance.voucher_code,
            'voucher_sent_to_telegram': message_was_sent_to_user,
        }

        # Sessiondagi testga oid ma'lumotlarni tozalash
        request.session.pop('current_test_id', None)
        request.session.pop('current_question_index', None)
        request.session.pop(f'test_{test_id}_answers', None)
        request.session.pop('time_spent_on_test', None)
        request.session.pop('test_submitted_for_processing', None)
        request.session.modified = True
        logger.info(f"Test {test_id} uchun session ma'lumotlari tozalandi.")

        return render(request, self.template_name, context)