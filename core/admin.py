# core/admin.py
from .models import User, EducationType, Institution, EducationLevel, Faculty, Subject, Question, Test
from django.utils.translation import gettext_lazy as _
import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone

from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from .forms import BulkUploadQuestionsForm # Yangi forma
from .utils import split_docx_into_questions # Yangi util funksiya
from django.core.files.base import ContentFile # Question modeliga saqlash uchun


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'telegram_id', 'full_name', 'phone_number', 'language_code',
        'education_type', 'institution', 'course_year', 'created_at', 'is_active'
    )
    list_filter = ('language_code', 'education_type', 'institution', 'is_active', 'created_at')
    search_fields = ('full_name', 'telegram_id__iexact', 'phone_number__icontains', 'username__icontains')
    readonly_fields = ('telegram_id', 'username', 'created_at', 'updated_at') # Ba'zi maydonlarni o'zgartirib bo'lmaydigan qilish
    list_editable = ('is_active',) # is_active ni ro'yxatdan o'zgartirish

    fieldsets = (
        (None, {'fields': ('telegram_id', 'username', 'language_code', 'is_active')}),
        (_('Shaxsiy maʻlumotlar'), {'fields': ('full_name', 'phone_number')}),
        (_('Taʻlim maʻlumotlari'), {'fields': ('education_type', 'institution', 'education_level', 'faculty', 'course_year')}),
        (_('Vaqt belgilari'), {'fields': ('created_at', 'updated_at')}),
    )
    # Agar User modelida ko'p maydon bo'lsa, fieldsets qulay

@admin.register(EducationType)
class EducationTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_uz', 'name_kaa', 'name_ru')
    search_fields = ('name_uz', 'name_kaa', 'name_ru')
    # Agar slug maydoni bo'lsa:
    # prepopulated_fields = {'slug': ('name_uz',)}

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_uz', 'education_type', 'name_kaa', 'name_ru')
    list_filter = ('education_type',)
    search_fields = ('name_uz', 'name_kaa', 'name_ru')
    autocomplete_fields = ['education_type'] # Agar EducationType ko'p bo'lsa qulay

@admin.register(EducationLevel)
class EducationLevelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_uz', 'name_kaa', 'name_ru')
    search_fields = ('name_uz', 'name_kaa', 'name_ru')

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_uz', 'institution', 'name_kaa', 'name_ru')
    list_filter = ('institution__education_type', 'institution') # Institution ning turi bo'yicha ham filtr
    search_fields = ('name_uz', 'name_kaa', 'name_ru', 'institution__name_uz')
    autocomplete_fields = ['institution']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_localized_name', 'min_course_year', 'max_course_year', 'voucher_template_name', 'is_active')
    list_editable = ('is_active', 'min_course_year', 'max_course_year', 'voucher_template_name')
    search_fields = ('name_uz', 'name_kaa', 'name_ru')

    def get_localized_name(self, obj): # Admin panelda ham tarjima qilingan nomni ko'rsatish
        return obj.get_localized_name()
    get_localized_name.short_description = _("Nomi")


class QuestionInline(admin.TabularInline): # Yoki StackedInline
    model = Question
    extra = 1 # Nechta bo'sh forma ko'rsatish kerakligi
    fields = ('question_file', 'correct_answer', 'is_active')
    # readonly_fields = ('get_question_preview',) # Savolni admin panelda ko'rsatish uchun (murakkabroq)

    # def get_question_preview(self, obj):
    #     # Bu yerda mammoth bilan HTML generatsiya qilib, uni xavfsiz qaytarish kerak
    #     # from django.utils.safestring import mark_safe
    #     # return mark_safe("...")
    #     return "Preview not available"
    # get_question_preview.short_description = _("Savol ko'rinishi")


# SubjectAdmin ni o'zgartirib, QuestionInline ni qo'shish mumkin
# admin.site.unregister(Subject) # Agar avval registratsiya qilingan bo'lsa
# @admin.register(Subject)
# class SubjectAdminWithQuestions(SubjectAdmin): # Yuqoridagi SubjectAdmin dan meros olish
#     inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'get_available_files_summary_admin', 'correct_answer', 'is_active', 'created_at')
    list_filter = ('subject', 'is_active', 'correct_answer')
    search_fields = ('subject__name_uz', 'id')
    autocomplete_fields = ['subject']
    # Endi bitta fayl o'rniga uchtasi bor
    fields = ('subject', 'correct_answer', 'is_active', 'question_file_uz', 'question_file_kaa', 'question_file_ru')
    # readonly_fields = ('get_question_preview_admin',) # Buni ham har bir til uchun alohida qilish kerak bo'ladi

    def get_available_files_summary_admin(self, obj):
        langs = []
        if obj.question_file_uz: langs.append("UZ")
        if obj.question_file_kaa: langs.append("KAA")
        if obj.question_file_ru: langs.append("RU")
        return ", ".join(langs) if langs else _("Fayl yo'q")
    get_available_files_summary_admin.short_description = _("Mavjud Tillar")

    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'bulk-upload/',
                self.admin_site.admin_view(self.bulk_upload_view),
                name='core_question_bulk_upload'
            ),
        ]
        return custom_urls + urls

    def bulk_upload_view(self, request):
        if request.method == 'POST':
            form = BulkUploadQuestionsForm(request.POST, request.FILES)
            if form.is_valid():
                subject = form.cleaned_data['subject']
                answers_str = form.cleaned_data['answers_string']
                delimiter = form.cleaned_data['delimiter']
                
                file_uz_bytes = form.cleaned_data['questions_file_uz'].read() if form.cleaned_data['questions_file_uz'] else None
                file_kaa_bytes = form.cleaned_data['questions_file_kaa'].read() if form.cleaned_data['questions_file_kaa'] else None
                file_ru_bytes = form.cleaned_data['questions_file_ru'].read() if form.cleaned_data['questions_file_ru'] else None

                # Har bir til uchun savollarni ajratib olish
                # Bu yerda har bir fayldagi savollar soni bir xil bo'lishi va javoblar soniga mos kelishi kerak.
                # split_docx_into_questions buni tekshiradi.

                parsed_q_uz, error_uz = split_docx_into_questions(file_uz_bytes, answers_str, delimiter)
                parsed_q_kaa, error_kaa = split_docx_into_questions(file_kaa_bytes, answers_str, delimiter)
                parsed_q_ru, error_ru = split_docx_into_questions(file_ru_bytes, answers_str, delimiter)
                print(parsed_q_uz)
                # Xatoliklarni tekshirish
                errors = []
                if error_uz: errors.append(f"UZ: {error_uz}")
                if error_kaa: errors.append(f"KAA: {error_kaa}")
                if error_ru: errors.append(f"RU: {error_ru}")

                # Turli tillardagi savollar soni mos kelishini tekshirish (agar kamida ikkita fayl yuklangan bo'lsa)
                counts = []
                if parsed_q_uz: counts.append(len(parsed_q_uz))
                if parsed_q_kaa: counts.append(len(parsed_q_kaa))
                if parsed_q_ru: counts.append(len(parsed_q_ru))

                if len(counts) > 1 and len(set(counts)) > 1: # Agar yuklangan fayllarda savollar soni har xil bo'lsa
                    errors.append(_("Turli tillardagi fayllarda savollar soni mos kelmadi: {}").format(counts))

                if errors:
                    for error_msg in errors:
                        messages.error(request, error_msg)
                    # Formani xatolar bilan qayta ko'rsatish
                    context = self.admin_site.each_context(request)
                    context['opts'] = self.model._meta
                    context['form'] = form
                    context['title'] = _("Savollarni ommaviy yuklash xatosi")
                    return render(request, 'bulk_upload_form.html', context)

                # Agar xatolik bo'lmasa, savollarni bazaga saqlash
                # parsed_q_uz, parsed_q_kaa, parsed_q_ru ichida (docx_bytes, answer_char) tuple'lari bor.
                # Ularning soni bir xil bo'lishi kerak (yuqorida tekshirildi).
                # Qaysi birida eng ko'p savol bo'lsa (yoki birinchisida), o'sha bo'yicha aylanamiz.
                
                num_questions_to_save = 0
                if parsed_q_uz: num_questions_to_save = len(parsed_q_uz)
                elif parsed_q_kaa: num_questions_to_save = len(parsed_q_kaa)
                elif parsed_q_ru: num_questions_to_save = len(parsed_q_ru)

                if num_questions_to_save == 0:
                     messages.warning(request, _("Yuklash uchun savollar topilmadi (fayllar bo'sh yoki ajratilmadi)."))
                else:
                    saved_count = 0
                    for i in range(num_questions_to_save):
                        q_data_uz = parsed_q_uz[i][0] if parsed_q_uz and i < len(parsed_q_uz) else None
                        q_data_kaa = parsed_q_kaa[i][0] if parsed_q_kaa and i < len(parsed_q_kaa) else None
                        q_data_ru = parsed_q_ru[i][0] if parsed_q_ru and i < len(parsed_q_ru) else None
                        
                        # Javobni birinchi mavjud parse qilingan ro'yxatdan olish
                        correct_ans = None
                        if parsed_q_uz and i < len(parsed_q_uz): correct_ans = parsed_q_uz[i][1]
                        elif parsed_q_kaa and i < len(parsed_q_kaa): correct_ans = parsed_q_kaa[i][1]
                        elif parsed_q_ru and i < len(parsed_q_ru): correct_ans = parsed_q_ru[i][1]

                        if not correct_ans: # Bu holat bo'lmasligi kerak
                            messages.error(request, _("{}-savol uchun javob topilmadi.").format(i+1))
                            continue

                        new_question = Question(subject=subject, correct_answer=correct_ans.lower(), is_active=True)
                        
                        if q_data_uz:
                            new_question.question_file_uz.save(f"q_uz_{subject.id}_{i+1}.docx", ContentFile(q_data_uz), save=False)
                        if q_data_kaa:
                            new_question.question_file_kaa.save(f"q_kaa_{subject.id}_{i+1}.docx", ContentFile(q_data_kaa), save=False)
                        if q_data_ru:
                            new_question.question_file_ru.save(f"q_ru_{subject.id}_{i+1}.docx", ContentFile(q_data_ru), save=False)
                        
                        new_question.save() # Barcha fayllar biriktirilgandan keyin saqlash
                        saved_count +=1

                    messages.success(request, _("{} ta savol muvaffaqiyatli yuklandi.").format(saved_count))
                
                return redirect('admin:core_question_changelist') # Savollar ro'yxatiga qaytish
        else:
            form = BulkUploadQuestionsForm()

        context = self.admin_site.each_context(request)
        context['opts'] = self.model._meta # Question modeli uchun meta ma'lumotlar
        context['form'] = form
        context['title'] = _("Savollarni Ommaviy Yuklash")
        # Shablon admin papkasi ichida bo'lishi kerak
        return render(request, 'bulk_upload_form.html', context)

    # Question ro'yxati sahifasiga "Ko'p savol yuklash" tugmasini qo'shish
    change_list_template = "question_changelist.html"


class TestQuestionsInline(admin.TabularInline): # Testga qaysi savollar tushganini ko'rsatish
    model = Test.questions.through # M2M uchun through model
    extra = 0
    verbose_name = _("Test Savoli")
    verbose_name_plural = _("Test Savollari")
    # fields = ('question',) # Faqat savolni ko'rsatish
    # readonly_fields = ('question',)
    
@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    # ... (list_display, list_filter, etc. avvalgidek, subject bilan bog'liq qismlar olib tashlangan) ...
    list_display = ('id', 'user', 'get_test_description_admin', 'score', 'started_at', 'completed_at', 'voucher_sent')
    list_filter = ('voucher_sent', 'started_at', 'user')
    search_fields = ('user__full_name', 'user__telegram_id', 'voucher_code', 'id')
    readonly_fields = ('started_at', 'completed_at', 'get_questions_display_admin')
    autocomplete_fields = ['user']
    
    fieldsets = (
        (None, {'fields': ('user', 'score', 'voucher_sent', 'voucher_code')}),
        (_("Vaqt belgilari"), {'fields': ('started_at', 'completed_at', 'time_spent_seconds')}),
        (_("Test Savollari"), {'fields': ('get_questions_display_admin',)}),
    )

    actions = ['export_selected_tests_as_excel']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def get_test_description_admin(self, obj): # Nomini o'zgartirdim, boshqa get_test_description bilan chalkashmaslik uchun
        return str(_("Aralash Test")) # str() bilan o'rash
    get_test_description_admin.short_description = str(_("Test Tavsifi")) # str() bilan o'rash

    def get_questions_display_admin(self, obj): # Nomini o'zgartirdim
        from django.utils.html import format_html
        questions_html = "<ul>"
        for question in obj.questions.all()[:15]:
            # Bu yerda ham str() ishlatish mumkin, lekin format_html odatda __proxy__ ni to'g'ri hal qiladi
            questions_html += f"<li>{question.id}: {str(question.subject.get_localized_name())} ({question.correct_answer})</li>"
        questions_html += "</ul>"
        if obj.questions.count() > 15:
            questions_html += f"<p>{str(_('va yana'))} {obj.questions.count() - 15} {str(_('ta savol...'))}</p>"
        return format_html(questions_html)
    get_questions_display_admin.short_description = str(_("Test Savollari")) # str() bilan o'rash


    @admin.action(description=str(_("Tanlangan testlarni Excelga eksport qilish"))) # str() bilan o'rash
    def export_selected_tests_as_excel(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, str(_("Eksport uchun testlar tanlanmadi.")), level=messages.WARNING) # str()
            return

        queryset = queryset.select_related(
            'user__education_type', # User ga bog'liq ForeignKeylarni oldindan yuklash
            'user__institution__education_type', # Institution va uning turi
            'user__education_level',
            'user__faculty'
        ).prefetch_related('questions__subject')


        data_for_excel = []
        # DataFrame uchun ustun nomlarini oldindan stringga aylantirish
        column_names = {
            'test_id': str(_('Test ID')),
            'tg_id': str(_('Telegram ID')),
            'full_name': str(_('F.A.Á.')),
            'phone': str(_('Telefon')),
            'edu_type': str(_('Bilimlendiriw Túri')),
            'institution': str(_('Mákeme')),
            'edu_level_otm': str(_('Basqısh (JOO)')),
            'faculty_otm': str(_('Fakultet (JOO)')),
            'course': str(_('Kurs')),
            'test_date_started': str(_('Test Baslanıw Waqıtı')),
            'test_date_completed': str(_('Test Tamamlanıw Waqıtı')),
            'score': str(_('Nátiyje (Ball)')),
            'total_q': str(_('Jámi Sorawlar')),
            'time_spent': str(_('Sarplaǵan Waqıtı (s)')),
            'voucher_code': str(_('Sertifikat Kodı')),
            'voucher_sent': str(_('Sertifikat Jiberildi')),
        }

        for test_obj in queryset:
            user = test_obj.user
            
            data_for_excel.append({
                column_names['test_id']: test_obj.id,
                column_names['tg_id']: user.telegram_id,
                column_names['full_name']: user.full_name or "",
                column_names['phone']: user.phone_number or "",
                column_names['edu_type']: str(user.education_type.name_kaa) if user.education_type else "",
                column_names['institution']: str(user.institution.name_kaa) if user.institution else "",
                column_names['edu_level_otm']: str(user.education_level.name_kaa) if user.education_level else "",
                column_names['faculty_otm']: str(user.faculty.name_kaa) if user.faculty else "",
                column_names['course']: user.course_year or "",
                column_names['test_date_started']: test_obj.started_at.strftime('%Y-%m-%d %H:%M') if test_obj.started_at else "",
                column_names['test_date_completed']: test_obj.completed_at.strftime('%Y-%m-%d %H:%M') if test_obj.completed_at else "",
                column_names['score']: test_obj.score,
                column_names['total_q']: test_obj.questions.count(),
                column_names['time_spent']: test_obj.time_spent_seconds,
                column_names['voucher_code']: test_obj.voucher_code or "",
                column_names['voucher_sent']: str(_("Awa")) if test_obj.voucher_sent else str(_("Yaq")),
            })

        if not data_for_excel:
            self.message_user(request, str(_("Eksport uchun ma'lumot topilmadi.")), level=messages.INFO) # str()
            return

        df = pd.DataFrame(data_for_excel)
        
        output = BytesIO()
        sheet_name_str = str(_('Test_Natijalari')) # Varaq nomini aniq stringga aylantirish

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name_str)
            
            # Ustun kengliklarini avtomatik sozlash (ixtiyoriy)
            worksheet = writer.sheets[sheet_name_str]
            for idx, col_name_proxy in enumerate(df.columns): # df.columns endi string bo'lishi kerak
                col_name_str = str(col_name_proxy) # Har ehtimolga qarshi
                series = df[col_name_proxy] # Original __proxy__ bilan olish kerak bo'lishi mumkin
                
                # Ma'lumotlar uzunligi
                try:
                    # Agar seriyada None qiymatlar bo'lsa, map(len) xato berishi mumkin
                    # None larni bo'sh stringga almashtirish
                    data_max_len = series.fillna('').astype(str).map(len).max()
                except Exception:
                    data_max_len = 0 # Agar xato bo'lsa
                
                # Ustun nomi uzunligi
                header_len = len(col_name_str)
                
                max_len = max(data_max_len, header_len) + 2 # Qo'shimcha joy
                worksheet.set_column(idx, idx, max_len)

        output.seek(0)

        filename = f"test_results_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response