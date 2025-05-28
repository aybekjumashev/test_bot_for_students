# core/admin.py
from django.contrib import admin
from .models import User, EducationType, Institution, EducationLevel, Faculty, Subject, Question, Test
from django.utils.translation import gettext_lazy as _
import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages



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
    list_display = ('id', 'subject', 'get_available_files_summary', 'correct_answer', 'is_active', 'created_at')
    list_filter = ('subject', 'is_active', 'correct_answer')
    search_fields = ('subject__name_uz', 'id')
    autocomplete_fields = ['subject']
    # Endi bitta fayl o'rniga uchtasi bor
    fields = ('subject', 'correct_answer', 'is_active', 'question_file_uz', 'question_file_kaa', 'question_file_ru')
    # readonly_fields = ('get_question_preview_admin',) # Buni ham har bir til uchun alohida qilish kerak bo'ladi

    def get_available_files_summary(self, obj):
        langs = []
        if obj.question_file_uz: langs.append("UZ")
        if obj.question_file_kaa: langs.append("KAA")
        if obj.question_file_ru: langs.append("RU")
        return ", ".join(langs) if langs else _("Fayl yo'q")
    get_available_files_summary.short_description = _("Mavjud Tillar")


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
            'full_name': str(_('F.I.Sh.')),
            'phone': str(_('Telefon')),
            'edu_type': str(_('Ta\'lim Turi')),
            'institution': str(_('Muassasa')),
            'edu_level_otm': str(_('Bosqich (OTM)')),
            'faculty_otm': str(_('Fakultet (OTM)')),
            'course': str(_('Kurs/Sinf')),
            'test_date_started': str(_('Test Boshlangan Sanasi')),
            'test_date_completed': str(_('Test Tugatilgan Sanasi')),
            'score': str(_('Natija (Ball)')),
            'total_q': str(_('Jami Savollar')),
            'time_spent': str(_('Sarflangan Vaqt (s)')),
            'voucher_code': str(_('Voucher Kodi')),
            'voucher_sent': str(_('Voucher Yuborildi')),
            'test_subjects': str(_('Testdagi Fanlar')),
        }

        for test_obj in queryset:
            user = test_obj.user
            subject_names_in_test = str(_("Aralash Test"))
            if test_obj.questions.exists():
                unique_subject_names = list(set(
                    str(q.subject.get_localized_name()) for q in test_obj.questions.all()[:5]
                ))
                if unique_subject_names:
                    subject_names_in_test = ", ".join(unique_subject_names)
                    if test_obj.questions.count() > 5:
                        subject_names_in_test += "..."
            
            data_for_excel.append({
                column_names['test_id']: test_obj.id,
                column_names['tg_id']: user.telegram_id,
                column_names['full_name']: user.full_name or "",
                column_names['phone']: user.phone_number or "",
                column_names['edu_type']: str(user.education_type.get_localized_name()) if user.education_type else "",
                column_names['institution']: str(user.institution.get_localized_name()) if user.institution else "",
                column_names['edu_level_otm']: str(user.education_level.get_localized_name()) if user.education_level else "",
                column_names['faculty_otm']: str(user.faculty.get_localized_name()) if user.faculty else "",
                column_names['course']: user.course_year or "",
                column_names['test_date_started']: test_obj.started_at.strftime('%Y-%m-%d %H:%M') if test_obj.started_at else "",
                column_names['test_date_completed']: test_obj.completed_at.strftime('%Y-%m-%d %H:%M') if test_obj.completed_at else "",
                column_names['score']: test_obj.score,
                column_names['total_q']: test_obj.questions.count(),
                column_names['time_spent']: test_obj.time_spent_seconds,
                column_names['voucher_code']: test_obj.voucher_code or "",
                column_names['voucher_sent']: str(_("Ha")) if test_obj.voucher_sent else str(_("Yo'q")),
                column_names['test_subjects']: subject_names_in_test,
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