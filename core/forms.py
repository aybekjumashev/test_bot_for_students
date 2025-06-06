# core/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import User, EducationType, Institution, EducationLevel, Faculty, Subject
from django.core.exceptions import ValidationError 

class UserRegistrationInfoForm(forms.ModelForm):
    # Telegram ID ni botdan yashirin maydon orqali olamiz
    telegram_id_hidden = forms.IntegerField(widget=forms.HiddenInput(), required=False) # JS orqali to'ldiriladi

    class Meta:
        model = User
        fields = [
            'name', 'surname', 'patronymic', 'education_type', 'institution',
            'education_level', 'faculty', 'course_year'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Ismingiz")}),
            'surname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Familiyangiz")}),
            'patronymic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Otangizning ismi")}),
            'education_type': forms.Select(attrs={'class': 'form-select'}),
            'institution': forms.Select(attrs={'class': 'form-select'}), # Dastlab bo'sh bo'ladi
            'education_level': forms.Select(attrs={'class': 'form-select'}), # Dastlab bo'sh/yashirin
            'faculty': forms.Select(attrs={'class': 'form-select'}), # Dastlab bo'sh/yashirin
            'course_year': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 7, 'placeholder': _("Masalan: 1")}),
        }
        labels = { # Maydon nomlarini o'zgartirish
            'name': _("Ismingiz"),
            'surname': _("Familiyangiz"),
            'patronymic': _("Otangizning ismi"),
            'education_type': _("Ta'lim muassasasi turi"),
            'institution': _("Muassasa nomi"),
            'education_level': _("Ta'lim bosqichi (OTM uchun)"),
            'faculty': _("Fakultet (OTM uchun)"),
            'course_year': _("Kurs (bosqich)"),
        }
        help_texts = {
            'course_year': _("Nechanchi kursda (yoki litsey/kollejda nechanchi bosqichda) o'qishingizni kiriting."),
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Name va surname ni required qilish
        self.fields['name'].required = True
        self.fields['surname'].required = True
        
        # Ularning widget attributes iga required qo'shish
        self.fields['name'].widget.attrs.update({'required': 'required'})
        self.fields['surname'].widget.attrs.update({'required': 'required'})

        # Dastlabki sozlamalar
        self.fields['education_type'].queryset = EducationType.objects.all()
        self.fields['education_type'].empty_label = _("Tanlang...")

        # Boshqa selectlarni dastlab bo'sh qoldirish
        initial_institution_queryset = Institution.objects.none()
        initial_education_level_queryset = EducationLevel.objects.none()
        initial_faculty_queryset = Faculty.objects.none()

        self.fields['institution'].empty_label = _("Avval ta'lim turini tanlang")
        self.fields['education_level'].empty_label = _("OTM tanlanganda ochiladi")
        self.fields['faculty'].empty_label = _("OTM tanlanganda ochiladi")

        # education_level va faculty dastlab majburiy emas
        self.fields['education_level'].required = False
        self.fields['faculty'].required = False

        # Agar forma POST so'rovi bilan kelgan bo'lsa (self.data mavjud)
        # yoki formaga instance berilgan bo'lsa (GET so'rovida oldindan to'ldirish uchun)
        # querysetlarni dinamik to'ldirish kerak.
        education_type_instance = None
        institution_instance = None

        if self.is_bound: # Agar POST yoki PUT/PATCH bo'lsa
            try:
                education_type_id = int(self.data.get('education_type'))
                if education_type_id:
                    education_type_instance = EducationType.objects.get(id=education_type_id)
            except (ValueError, TypeError, EducationType.DoesNotExist):
                education_type_instance = None
            
            try:
                institution_id = int(self.data.get('institution'))
                if institution_id:
                    institution_instance = Institution.objects.get(id=institution_id)
            except (ValueError, TypeError, Institution.DoesNotExist):
                institution_instance = None

        elif self.instance and self.instance.pk: # Agar GET va instance mavjud bo'lsa
            education_type_instance = self.instance.education_type
            institution_instance = self.instance.institution

        # Endi education_type_instance ga qarab querysetlarni o'rnatamiz
        if education_type_instance:
            initial_institution_queryset = Institution.objects.filter(education_type=education_type_instance)
            self.fields['institution'].empty_label = _("Tanlang...")
            if hasattr(education_type_instance, 'is_otm') and education_type_instance.is_otm:
                initial_education_level_queryset = EducationLevel.objects.all()
                self.fields['education_level'].empty_label = _("Tanlang...")
                # required atributini clean() metodi hal qiladi

        # Endi institution_instance ga qarab faculty querysetini o'rnatamiz
        if institution_instance and education_type_instance and \
        hasattr(education_type_instance, 'is_otm') and education_type_instance.is_otm:
            initial_faculty_queryset = Faculty.objects.filter(institution=institution_instance)
            self.fields['faculty'].empty_label = _("Tanlang...")

        self.fields['institution'].queryset = initial_institution_queryset
        self.fields['education_level'].queryset = initial_education_level_queryset
        self.fields['faculty'].queryset = initial_faculty_queryset
        
    def clean_telegram_id_hidden(self):
        # Bu maydonni formadan olib tashlaymiz, chunki viewda URL dan olamiz
        # Yoki uni saqlash uchun User modeliga qo'shish mumkin, ammo bizda User.telegram_id bor
        return None

    def clean(self):
        cleaned_data = super().clean()
        education_type = cleaned_data.get("education_type")
        education_level_value = cleaned_data.get("education_level")
        faculty_value = cleaned_data.get("faculty")

        print(f"--- Form Clean Method (forms.py) ---")
        print(f"Request POST data for education_level: {self.data.get('education_level')}") # KELAYOTGAN RAW QIYMATNI KO'RISH
        print(f"Education Type from cleaned_data: {education_type}")
        print(f"Education Type is_otm: {education_type.is_otm if hasattr(education_type, 'is_otm') else 'N/A'}")
        print(f"Education Level Value from cleaned_data: {education_level_value}") # BU ENG MUHIM!
        print(f"Faculty Value from cleaned_data: {faculty_value}")

        education_type_is_otm = False
        if education_type and hasattr(education_type, 'is_otm') and education_type.is_otm:
            education_type_is_otm = True
        
        print(f"Calculated is_otm: {education_type_is_otm}")

        if education_type_is_otm:
            if not education_level_value: # Agar bu None yoki bo'sh string bo'lsa, xato beradi
                print(f"Adding error for education_level because it's None or empty for OTM.")
                self.add_error('education_level', _("OTM uchun ta'lim bosqichini tanlang."))
            
            if not faculty_value:
                print(f"Adding error for faculty because it's None or empty for OTM.")
                self.add_error('faculty', _("OTM uchun fakultetni tanlang."))
        else:
            # Agar OTM bo'lmasa va qiymat kelgan bo'lsa (JSda xatolik yoki JS o'chiq bo'lsa)
            if education_level_value:
                print(f"Clearing education_level because not OTM.")
                cleaned_data["education_level"] = None
            if faculty_value:
                print(f"Clearing faculty because not OTM.")
                cleaned_data["faculty"] = None
        
        print(f"--- End of Form Clean Method ---")
        return cleaned_data


class BulkUploadQuestionsForm(forms.Form):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all().order_by('name_uz'),
        label=_("Fan"),
        empty_label=_("Fanni tanlang"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    questions_file_uz = forms.FileField(
        label=_("Savollar fayli (O'zbekcha, DOCX)"),
        required=False, # Kamida bitta fayl kerak, buni clean() da tekshiramiz
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    questions_file_kaa = forms.FileField(
        label=_("Savollar fayli (Qoraqalpoqcha, DOCX)"),
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    questions_file_ru = forms.FileField(
        label=_("Savollar fayli (Ruscha, DOCX)"),
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    answers_string = forms.CharField(
        label=_("Javoblar ketma-ketligi"),
        help_text=_("Masalan: ABADDCB... Har bir fayldagi savollar soniga mos kelishi kerak."),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCDABCD...'}),
        max_length=500 # Maksimal javoblar soni (ehtiyojga qarab)
    )
    delimiter = forms.CharField(
        label=_("Savol ajratuvchi belgi"),
        initial="###",
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text=_("DOCX faylida savollarni ajratib turuvchi belgi.")
    )

    def clean_answers_string(self):
        data = self.cleaned_data['answers_string'].upper().replace(" ", "")
        allowed_chars = {'A', 'B', 'C', 'D'}
        if not all(char in allowed_chars for char in data):
            raise ValidationError(_("Javoblar faqat A, B, C, D harflaridan iborat bo'lishi kerak."))
        return data

    def clean(self):
        cleaned_data = super().clean()
        file_uz = cleaned_data.get('questions_file_uz')
        file_kaa = cleaned_data.get('questions_file_kaa')
        file_ru = cleaned_data.get('questions_file_ru')
        answers = cleaned_data.get('answers_string')

        if not (file_uz or file_kaa or file_ru):
            raise ValidationError(_("Hech bo'lmaganda bitta tilda savollar faylini yuklang."))
        
        if not answers:
             raise ValidationError(_("Javoblar ketma-ketligini kiriting."))

        # Fayllar va javoblar sonini tekshirishni utils funksiyasiga qoldiramiz,
        # chunki u yerda DOCX ichidagi savollar soni aniqlanadi.
        return cleaned_data