# core/serializers.py
from rest_framework import serializers
from .models import EducationType, Institution, EducationLevel, Faculty
from django.utils import translation

class LocalizedModelSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        # Modelda get_localized_name() metodi bor deb taxmin qilamiz
        if hasattr(obj, 'get_localized_name'):
            return obj.get_localized_name()
        # Agar yo'q bo'lsa, standart nom (masalan, name_uz)
        return getattr(obj, 'name_uz', str(obj))

class EducationTypeSerializer(LocalizedModelSerializer):
    class Meta:
        model = EducationType
        fields = ['id', 'name', 'is_otm'] # Agar slug bo'lsa, 'slug' ni ham qo'shing

class InstitutionSerializer(LocalizedModelSerializer):
    class Meta:
        model = Institution
        fields = ['id', 'name', 'education_type'] # education_type ID sini ham qaytarish mumkin

class EducationLevelSerializer(LocalizedModelSerializer):
    class Meta:
        model = EducationLevel
        fields = ['id', 'name']

class FacultySerializer(LocalizedModelSerializer):
    class Meta:
        model = Faculty
        fields = ['id', 'name', 'institution']