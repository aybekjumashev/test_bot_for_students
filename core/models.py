# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _
import uuid # Agar UUID ishlatmoqchi bo'lsangiz, lekin telegram_id unique bo'lgani uchun shart emas
from django.utils import translation # Joriy tilni olish uchun
from django.utils import timezone # datetime.now() o'rniga
from django.conf import settings



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



class UserManager(BaseUserManager):
    def create_user(self, telegram_id, password=None, **extra_fields):
        if not telegram_id:
            raise ValueError(_('The Telegram ID must be set'))
        
        # Agar username ham unique va majburiy bo'lsa, uni ham tekshirish mumkin
        # username = extra_fields.get('username')
        # if not username:
        #     raise ValueError(_('The username must be set'))

        user = self.model(telegram_id=telegram_id, **extra_fields)
        
        if password: # Faqat parol berilgan bo'lsa uni o'rnatamiz
            user.set_password(password)
        else:
            # Agar parol berilmagan bo'lsa (masalan, botdan ro'yxatdan o'tayotgan oddiy user)
            # Va bu superuser EMAS bo'lsa, parolni ishlatib bo'lmaydigan qilib qo'yish mumkin
            if not extra_fields.get('is_superuser'):
                user.set_unusable_password() # Bu parolni bo'sh va login qilib bo'lmaydigan qiladi

        user.save(using=self._db)
        return user

    def create_superuser(self, telegram_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        if not password: # Superuser uchun parol majburiy
            raise ValueError(_('Superusers must have a password.'))

        # create_user endi parolni to'g'ri o'rnatadi
        return self.create_user(telegram_id, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    telegram_id = models.BigIntegerField(unique=True, verbose_name=_("Telegram ID"))
    username = models.CharField(
        max_length=100, blank=True, null=True, unique=True, # unique=True qilish tavsiya etiladi agar USERNAME_FIELD bo'lsa
        verbose_name=_("Telegram Username")
    ) # Agar USERNAME_FIELD uchun ishlatsangiz, unique=True bo'lishi kerak
    full_name = models.CharField(max_length=150, blank=True, null=True, verbose_name=_("Ism va sharif"))
    phone_number = models.CharField(max_length=20, blank=True, null=True, unique=True, verbose_name=_("Telefon raqami"))

    LANGUAGE_CHOICES = [
        ('uz', _('Uzbek')),
        ('kaa', _('Karakalpak')),
        ('ru', _('Russian')),
    ]
    language_code = models.CharField(
        max_length=3,
        choices=LANGUAGE_CHOICES,
        default='uz',
        verbose_name=_("Til")
    )

    education_type = models.ForeignKey('EducationType', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Ta'lim muassasasi turi"))
    institution = models.ForeignKey('Institution', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Muassasa nomi"))
    education_level = models.ForeignKey('EducationLevel', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Ta'lim bosqichi (OTM)"))
    faculty = models.ForeignKey('Faculty', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Fakultet (OTM)"))
    course_year = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Kurs (bosqich)"))

    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    # is_superuser maydoni PermissionsMixin dan keladi

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan sana"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Yangilangan sana"))

    objects = UserManager() # Maxsus manager

    # USERNAME_FIELD foydalanuvchini unikal identifikatsiya qilish uchun ishlatiladi
    # Bu odatda username yoki email bo'ladi. Bizda telegram_id bor.
    USERNAME_FIELD = 'telegram_id'
    # createsuperuser buyrug'i so'raydigan qo'shimcha maydonlar (USERNAME_FIELD dan tashqari)
    REQUIRED_FIELDS = [] # Masalan, username ni ham so'rasin (garchi bizda u unique bo'lmasa ham)
                                  # Yoki bo'sh qoldiring: []

    def __str__(self):
        return str(self.telegram_id) # Yoki self.full_name or str(self.telegram_id)

    def get_full_name(self): # Django admin buni kutishi mumkin
        return self.full_name or str(self.telegram_id)

    def get_short_name(self): # Django admin buni kutishi mumkin
        return str(self.telegram_id)

    class Meta:
        verbose_name = _("Foydalanuvchi")
        verbose_name_plural = _("Foydalanuvchilar")
        ordering = ['-created_at']



class Subject(models.Model):
    name_uz = models.CharField(max_length=150, verbose_name=_("Nomi (O'zbekcha)"))
    name_kaa = models.CharField(max_length=150, verbose_name=_("Nomi (Qoraqalpoqcha)"))
    name_ru = models.CharField(max_length=150, verbose_name=_("Nomi (Ruscha)"))
    # Eski `min_klass`, `max_klass` o'rniga bizda `User.course_year` bor.
    # Bu fanning qaysi kurslarga/bosqichlarga tegishliligini aniqlash uchun
    # alohida M2M yoki boshqa yondashuv kerak bo'lishi mumkin.
    # Hozircha, fanni barcha uchun ochiq deb hisoblaymiz va viewda filtrlaymiz.
    # Yoki EducationLevel/CourseYear ga bog'lash mumkin.
    # Misol uchun, minimal va maksimal kurs:
    min_course_year = models.PositiveSmallIntegerField(default=1, verbose_name=_("Minimal kurs/bosqich"))
    max_course_year = models.PositiveSmallIntegerField(default=11, verbose_name=_("Maksimal kurs/bosqich")) # Masalan, 11-sinf/2-kurs litsey
    # Yoki qaysi EducationType larga tegishli ekanligini ko'rsatish
    # applicable_education_types = models.ManyToManyField(EducationType, blank=True, verbose_name=_("Qo'llaniladigan ta'lim turlari"))

    # Rasm shablonlari uchun nom (agar har bir fan uchun alohida voucher bo'lsa)
    voucher_template_name = models.CharField(
        max_length=50, blank=True, null=True,
        help_text=_("Voucher rasmi uchun shablon nomi (masalan, Matematika -> VoucherMatematika). Agar bo'sh bo'lsa, standart ishlatiladi."),
        verbose_name=_("Voucher shabloni nomi")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Aktiv"))


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
        verbose_name = _("Fan")
        verbose_name_plural = _("Fanlar")
        ordering = ['name_uz']


def question_file_path(instance, filename):
    # Fayl subjects/<subject_id>/questions/<filename> manziliga yuklanadi
    return f'subjects/{instance.subject.id}/questions/{filename}'

class Question(models.Model):
    subject = models.ForeignKey(Subject, related_name='questions', on_delete=models.CASCADE, verbose_name=_("Fan"))
    # Eski `data = Column(LargeBinary)` o'rniga `FileField`
    # DOCX fayllarni saqlash uchun maxsus papka (masalan, `media/questions/`)
    question_file = models.FileField(upload_to=question_file_path, verbose_name=_("Savol fayli (DOCX)"))
    # Javob variantlari odatda a, b, c, d bo'ladi
    ANSWER_CHOICES = [
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C'),
        ('d', 'D'),
    ]
    correct_answer = models.CharField(max_length=1, choices=ANSWER_CHOICES, verbose_name=_("To'g'ri javob"))
    is_active = models.BooleanField(default=True, verbose_name=_("Aktiv"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{_('Savol')} #{self.id} ({self.subject.get_localized_name()})"

    class Meta:
        verbose_name = _("Savol")
        verbose_name_plural = _("Savollar")
        ordering = ['subject', '-created_at']


class Test(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='tests', on_delete=models.CASCADE, verbose_name=_("Foydalanuvchi")) # AUTH_USER_MODEL = 'core.User'
    # `date` -> `started_at` va `completed_at` ga ajratish mumkin
    started_at = models.DateTimeField(default=timezone.now, verbose_name=_("Boshlangan vaqti"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Tugatilgan vaqti"))
    # `result` -> `score` (to'g'ri javoblar soni)
    score = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Natija (ball)"))
    # Testga berilgan savollar (M2M)
    questions = models.ManyToManyField(Question, related_name='tests', verbose_name=_("Berilgan savollar"))
    # Foydalanuvchining javoblari (JSON yoki alohida modelda saqlash mumkin)
    # Hozircha sodda qilamiz, natijani saqlaymiz xolos.
    # Agar har bir savolga berilgan javobni saqlash kerak bo'lsa, TestAttempt kabi model kerak.
    time_spent_seconds = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Sarflangan vaqt (sekund)"))
    voucher_sent = models.BooleanField(default=False, verbose_name=_("Voucher yuborildimi?"))
    voucher_code = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("Voucher kodi/raqami"))


    def __str__(self):
        return f"{self.user} - {_('Aralash Test')} ({self.started_at.strftime('%Y-%m-%d %H:%M')})"

    class Meta:
        verbose_name = _("Test")
        verbose_name_plural = _("Testlar")
        # Bir foydalanuvchi bitta fandan faqat bir marta (natijali) test topshirishi mumkin (agar shart bo'lsa)
        # unique_together = [['user', 'subject']] # Agar qayta topshirish mumkin bo'lmasa
        ordering = ['-started_at']