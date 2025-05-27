# core/management/commands/create_test_data.py

import random
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from django.core.files.base import ContentFile # Fayl yaratish uchun
from io import BytesIO # DOCX uchun BytesIO
from docx import Document as DocxDocument # python-docx dan Document
from django.db import transaction

# Modellarni import qilish
from core.models import Subject, Question, EducationType, User # EducationType va User kerak bo'lishi mumkin

# Agar EducationType kerak bo'lsa, uni topish yoki yaratish
def get_or_create_default_education_type():
    # Barcha uchun umumiy bo'lgan ta'lim turini topish yoki yaratish
    # Bu sizning EducationType modelingizga bog'liq
    # Masalan, "Umumiy" yoki "Barcha bosqichlar uchun"
    obj, created = EducationType.objects.get_or_create(
        name_uz="Umumiy Ta'lim",
        defaults={
            'name_kaa': "Улыўма Билимлендириў", # To'g'rilang
            'name_ru': "Общее Образование",
            'is_otm': False # Yoki True, feyk dataga bog'liq
        }
    )
    return obj


# Oddiy DOCX fayl kontentini generatsiya qilish uchun funksiya
def generate_dummy_docx_content(subject_name, question_num):
    document = DocxDocument()
    document.add_heading(f"{subject_name} - Savol #{question_num}", level=1)
    document.add_paragraph(
        f"Bu {subject_name} fanidan {question_num}-savolning matni. "
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Variantlar quyidagicha bo'lishi mumkin:"
    )
    document.add_paragraph("A) Variant A matni")
    document.add_paragraph("B) Variant B matni")
    document.add_paragraph("C) Variant C matni")
    document.add_paragraph("D) Variant D matni")

    # BytesIO obyektiga saqlash
    file_stream = BytesIO()
    document.save(file_stream)
    file_stream.seek(0) # Pointerni boshiga qaytarish
    return file_stream


class Command(BaseCommand):
    help = 'Creates fake data for subjects and questions for testing purposes.'

    @transaction.atomic # Barcha operatsiyalar bitta tranzaksiyada bo'lishi uchun
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Feyk ma\'lumotlarni yaratish boshlandi...'))

        # Mavjud ma'lumotlarni o'chirish (ixtiyoriy, ehtiyot bo'ling!)
        # Subject.objects.all().delete()
        # Question.objects.all().delete()
        # self.stdout.write(self.style.WARNING('Mavjud fanlar va savollar o\'chirildi.'))

        default_education_type = get_or_create_default_education_type()

        subject_names_uz = [
            "Matematika", "Fizika", "Ona Tili va Adabiyot", "Tarix", "Ingliz Tili"
        ]
        subject_names_kaa = [
            "Математика", "Физика", "Ана Тили ҳәм Әдебияты", "Тарийх", "Инглис Тили" # To'g'rilang
        ]
        subject_names_ru = [
            "Математика", "Физика", "Родной Язык и Литература", "История", "Английский Язык"
        ]

        num_subjects = 5
        questions_per_subject = 10
        answer_choices = ['a', 'b', 'c', 'd']

        for i in range(num_subjects):
            subject_name_uz = subject_names_uz[i % len(subject_names_uz)] + (f" {i//len(subject_names_uz) + 1}" if i >= len(subject_names_uz) else "")
            subject_name_kaa = subject_names_kaa[i % len(subject_names_kaa)] + (f" {i//len(subject_names_kaa) + 1}" if i >= len(subject_names_kaa) else "")
            subject_name_ru = subject_names_ru[i % len(subject_names_ru)] + (f" {i//len(subject_names_ru) + 1}" if i >= len(subject_names_ru) else "")

            # Feyk Subject yaratish
            subject, created = Subject.objects.get_or_create(
                name_uz=subject_name_uz,
                defaults={
                    'name_kaa': subject_name_kaa,
                    'name_ru': subject_name_ru,
                    'min_course_year': 1,  # Barcha kurslar uchun
                    'max_course_year': 11, # Barcha kurslar uchun
                    'is_active': True,
                    'voucher_template_name': subject_name_uz.replace(" ", "") # Masalan, "Matematika"
                }
            )
            # Agar Subject modelida applicable_education_types M2M bo'lsa:
            # subject.applicable_education_types.add(default_education_type)

            if created:
                self.stdout.write(self.style.SUCCESS(f'"{subject.name_uz}" fani yaratildi.'))
            else:
                self.stdout.write(self.style.NOTICE(f'"{subject.name_uz}" fani allaqachon mavjud.'))


            # Har bir fan uchun 10 ta savol yaratish
            # Agar fan allaqachon mavjud bo'lsa va savollari bo'lsa, yangi savol qo'shmaslik uchun
            # if subject.questions.count() >= questions_per_subject and not created:
            #     self.stdout.write(self.style.NOTICE(f'"{subject.name_uz}" fani uchun savollar yetarli.'))
            #     continue

            current_question_count = subject.questions.count()
            for j in range(questions_per_subject - current_question_count):
                question_number_in_subject = current_question_count + j + 1
                
                # Feyk DOCX kontentini generatsiya qilish
                docx_content_stream = generate_dummy_docx_content(subject.name_uz, question_number_in_subject)
                
                # Django ContentFile yaratish
                django_file = ContentFile(docx_content_stream.read(), name=f'question_{subject.id}_{question_number_in_subject}.docx')

                Question.objects.create(
                    subject=subject,
                    question_file=django_file, # Django FileField ga ContentFile beriladi
                    correct_answer=random.choice(answer_choices),
                    is_active=True
                )
            self.stdout.write(self.style.SUCCESS(f'"{subject.name_uz}" fani uchun {questions_per_subject - current_question_count} ta yangi savol yaratildi.'))


        self.stdout.write(self.style.SUCCESS('Feyk ma\'lumotlarni yaratish tugallandi!'))