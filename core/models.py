# core/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid # Agar UUID ishlatmoqchi bo'lsangiz, lekin telegram_id unique bo'lgani uchun shart emas

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

    # Keyingi bosqichlarda qo'shiladigan ta'limga oid maydonlar
    # education_type = models.ForeignKey('EducationType', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Ta'lim muassasasi turi")))
    # institution = models.ForeignKey('Institution', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Muassasa nomi")))
    # education_level = models.ForeignKey('EducationLevel', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Ta'lim bosqichi (OTM uchun)")))
    # faculty = models.ForeignKey('Faculty', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Fakultet (OTM uchun)")))
    # course_year = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Kurs (bosqich)")))

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