# core/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid # Agar UUID ishlatmoqchi bo'lsangiz, lekin telegram_id unique bo'lgani uchun shart emas
from django.utils import translation # Joriy tilni olish uchun



class EducationType(models.Model):
    name_uz = models.CharField(max_length=100, verbose_name=_("Nomi (O'zbekcha)"))
    name_kaa = models.CharField(max_length=100, verbose_name=_("Nomi (Qoraqalpoqcha)"))
    name_ru = models.CharField(max_length=100, verbose_name=_("Nomi (Ruscha)"))
    is_otm = models.BooleanField(default=False, verbose_name=_("Bu OTMmi?")) # YANGI MAYDON
    # Agar kerak bo'lsa, API orqali dinamik selectlar uchun qisqa kod (slug)
    # slug = models.SlugField(max_length=50, unique=True, blank=True, null=True, help_text=_("API uchun qisqa nom (masalan, 'otm', 'kollej')"))

    def get_localized_name(self):
        lang = translation.get_language()
        if lang == 'kaa' and self.name_kaa:
            return self.name_kaa
        elif lang == 'ru' and self.name_ru:
            return self.name_ru
        return self.name_uz # Standart yoki name_uz

    def __str__(self):
        return self.get_localized_name()

    class Meta:
        verbose_name = _("Ta'lim muassasasi turi")
        verbose_name_plural = _("Ta'lim muassasasi turlari")
        ordering = ['name_uz']


class Institution(models.Model):
    education_type = models.ForeignKey(EducationType, on_delete=models.CASCADE, verbose_name=_("Ta'lim turi"))
    name_uz = models.CharField(max_length=255, verbose_name=_("Nomi (O'zbekcha)"))
    name_kaa = models.CharField(max_length=255, verbose_name=_("Nomi (Qoraqalpoqcha)"))
    name_ru = models.CharField(max_length=255, verbose_name=_("Nomi (Ruscha)"))

    def get_localized_name(self):
        lang = translation.get_language()
        if lang == 'kaa' and self.name_kaa:
            return self.name_kaa
        elif lang == 'ru' and self.name_ru:
            return self.name_ru
        return self.name_uz

    def __str__(self):
        return self.get_localized_name()

    class Meta:
        verbose_name = _("Ta'lim muassasasi")
        verbose_name_plural = _("Ta'lim muassasalari")
        ordering = ['education_type', 'name_uz']


# Faqat OTM uchun (Bakalavr, Magistr)
class EducationLevel(models.Model):
    name_uz = models.CharField(max_length=100, verbose_name=_("Nomi (O'zbekcha)"))
    name_kaa = models.CharField(max_length=100, verbose_name=_("Nomi (Qoraqalpoqcha)"))
    name_ru = models.CharField(max_length=100, verbose_name=_("Nomi (Ruscha)"))

    def get_localized_name(self):
        lang = translation.get_language()
        if lang == 'kaa' and self.name_kaa:
            return self.name_kaa
        elif lang == 'ru' and self.name_ru:
            return self.name_ru
        return self.name_uz

    def __str__(self):
        return self.get_localized_name()

    class Meta:
        verbose_name = _("Ta'lim bosqichi (OTM)")
        verbose_name_plural = _("Ta'lim bosqichlari (OTM)")
        ordering = ['name_uz']


class Faculty(models.Model):
    # Faqat OTM ga bog'liq bo'lishi kerak.
    # Agar Institution modelida 'OTM' degan alohida tur bo'lsa, o'shanga bog'lash mumkin.
    # Yoki Institution education_type ni tekshirish kerak.
    # Hozircha barcha Institution larga bog'laymiz, lekin form logikasida cheklaymiz.
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        verbose_name=_("Ta'lim muassasasi"),
        # limit_choices_to={'education_type__slug': 'otm'} # Agar EducationType da slug bo'lsa
    )
    name_uz = models.CharField(max_length=255, verbose_name=_("Nomi (O'zbekcha)"))
    name_kaa = models.CharField(max_length=255, verbose_name=_("Nomi (Qoraqalpoqcha)"))
    name_ru = models.CharField(max_length=255, verbose_name=_("Nomi (Ruscha)"))

    def get_localized_name(self):
        lang = translation.get_language()
        if lang == 'kaa' and self.name_kaa:
            return self.name_kaa
        elif lang == 'ru' and self.name_ru:
            return self.name_ru
        return self.name_uz

    def __str__(self):
        return f"{self.get_localized_name()} ({self.institution.get_localized_name()})"


    class Meta:
        verbose_name = _("Fakultet")
        verbose_name_plural = _("Fakultetlar")
        ordering = ['institution', 'name_uz']




class User(models.Model):
    # Agar alohida ID maydoni kerak bo'lsa:
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telegram_id = models.BigIntegerField(unique=True, verbose_name=_("Telegram ID")) # Buni primary_key qilish ham mumkin
    full_name = models.CharField(max_length=150, blank=True, null=True, verbose_name=_("Ism va sharif"))
    username = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Telegram Username")) # Telegramdan olish mumkin
    phone_number = models.CharField(max_length=20, blank=True, null=True, unique=True, verbose_name=_("Telefon raqami"))

    LANGUAGE_CHOICES = [
        ('uz', _('Uzbek')),
        ('kaa', _('Karakalpak')),
        ('ru', _('Russian')),
    ]
    language_code = models.CharField(
        max_length=3,
        choices=LANGUAGE_CHOICES,
        default='uz', # Yoki botdan birinchi so'ralgan tilni saqlaysiz
        verbose_name=_("Til")
    )
    education_type = models.ForeignKey(
        EducationType,
        on_delete=models.SET_NULL,
        null=True, blank=True, # Forma uchun majburiy, lekin DB da bo'sh bo'lishi mumkin
        verbose_name=_("Ta'lim muassasasi turi")
    )
    institution = models.ForeignKey(
        Institution,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Muassasa nomi")
    )
    # Faqat OTM tanlanganda to'ldiriladi
    education_level = models.ForeignKey(
        EducationLevel,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Ta'lim bosqichi (OTM)")
    )
    # Faqat OTM tanlanganda to'ldiriladi
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Fakultet (OTM)")
    )
    course_year = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name=_("Kurs (bosqich)")
        # validators=[MinValueValidator(1), MaxValueValidator(7)] # Agar kerak bo'lsa
    )

    is_active = models.BooleanField(default=True) # Foydalanuvchi aktivmi?
    is_admin = models.BooleanField(default=False) # Agar botda adminlar bo'lsa

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan sana"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Yangilangan sana"))

    def __str__(self):
        return self.full_name or str(self.telegram_id)

    class Meta:
        verbose_name = _("Foydalanuvchi")
        verbose_name_plural = _("Foydalanuvchilar")
        ordering = ['-created_at']

