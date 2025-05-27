# core/admin.py
from django.contrib import admin
from .models import User, EducationType, Institution, EducationLevel, Faculty
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