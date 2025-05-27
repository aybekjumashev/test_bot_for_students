# core/admin.py
from django.contrib import admin
from .models import User, EducationType, Institution, EducationLevel, Faculty, Subject, Question, Test
from django.utils.translation import gettext_lazy as _

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
    list_display = ('id', 'subject', 'correct_answer', 'is_active', 'created_at')
    list_filter = ('subject', 'is_active', 'correct_answer')
    search_fields = ('subject__name_uz', 'id') # Savol matnini qidirish qiyin, chunki u faylda
    autocomplete_fields = ['subject']
    # readonly_fields = ('get_question_preview',)


class TestQuestionsInline(admin.TabularInline): # Testga qaysi savollar tushganini ko'rsatish
    model = Test.questions.through # M2M uchun through model
    extra = 0
    verbose_name = _("Test Savoli")
    verbose_name_plural = _("Test Savollari")
    # fields = ('question',) # Faqat savolni ko'rsatish
    # readonly_fields = ('question',)

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'get_test_description', 'score', 'started_at', 'completed_at', 'voucher_sent') # 'subject' o'rniga 'get_test_description'
    list_filter = ('voucher_sent', 'started_at', 'user') # 'subject' olib tashlandi, 'user' qo'shilishi mumkin
    search_fields = ('user__full_name', 'user__telegram_id', 'voucher_code', 'id') # 'subject__name_uz' olib tashlandi
    readonly_fields = ('started_at', 'completed_at', 'get_questions_display') # 'questions' o'rniga 'get_questions_display'
    autocomplete_fields = ['user'] # 'subject' olib tashlandi
    # inlines = [TestQuestionsInline] # Agar savollarni inline ko'rsatmoqchi bo'lsangiz

    fieldsets = (
        (None, {'fields': ('user', 'score', 'voucher_sent', 'voucher_code')}),
        (_("Vaqt belgilari"), {'fields': ('started_at', 'completed_at', 'time_spent_seconds')}),
        (_("Test Savollari"), {'fields': ('get_questions_display',)}), # Savollarni ko'rsatish uchun
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user') # 'subject' olib tashlandi

    def get_test_description(self, obj):
        # Test qaysi fanlarni o'z ichiga olganini ko'rsatish (agar kerak bo'lsa)
        # Bu sekin ishlashi mumkin, agar savollar ko'p bo'lsa
        # Yaxshiroq yechim - Test modeliga qaysi fanlardan ekanligini saqlash (masalan, M2M bilan)
        # Hozircha, birinchi bir nechta savolning fanlarini ko'rsatamiz yoki "Aralash Test" deymiz
        # questions_qs = obj.questions.all().select_related('subject')[:3] # Birinchi 3 savol
        # if questions_qs:
        #     subject_names = list(set([q.subject.get_localized_name() for q in questions_qs]))
        #     return ", ".join(subject_names) + ("..." if obj.questions.count() > 3 else "")
        return _("Aralash Test") # Yoki obj.__str__() dan foydalanish
    get_test_description.short_description = _("Test Tavsifi")

    def get_questions_display(self, obj):
        # Testdagi savollarni admin panelda chiroyli ko'rsatish uchun
        from django.utils.html import format_html
        questions_html = "<ul>"
        for question in obj.questions.all()[:15]: # Ko'p bo'lsa, birinchi 15 tasini ko'rsatish
            questions_html += f"<li>{question.id}: {question.subject.get_localized_name()} ({question.correct_answer})</li>"
        questions_html += "</ul>"
        if obj.questions.count() > 15:
            questions_html += f"<p>{_('va yana')} {obj.questions.count() - 15} {_('ta savol...')}</p>"
        return format_html(questions_html)
    get_questions_display.short_description = _("Test Savollari")