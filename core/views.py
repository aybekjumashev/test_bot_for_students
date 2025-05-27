# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages # Foydalanuvchiga xabar berish uchun
from django.urls import reverse_lazy, reverse # reverse_lazy FormView uchun, reverse redirect uchun
from django.utils.translation import gettext_lazy as _
from django.utils.translation import activate # Tilni aktivlashtirish uchun
from .forms import UserRegistrationInfoForm
from .models import User, EducationType, Institution, EducationLevel, Faculty
from django.http import HttpRequest

from rest_framework.generics import ListAPIView
from .serializers import (
    EducationTypeSerializer, InstitutionSerializer,
    EducationLevelSerializer, FacultySerializer
)

class UserRegistrationInfoFormView(View):
    form_class = UserRegistrationInfoForm
    template_name = 'registration_info_form.html' # Shablon nomi

    def get(self, request: HttpRequest, *args, **kwargs):
        telegram_id = request.GET.get('tgWebAppStartParam')
        if not telegram_id:
            messages.error(request, _("Telegram ID topilmadi. Iltimos, bot orqali qayta urinib ko'ring."))
            # Yoki botga qaytaradigan sahifaga yo'naltirish
            return redirect(reverse('core:some_error_page')) # Misol, error page yaratish kerak bo'ladi

        try:
            user = User.objects.get(telegram_id=telegram_id)
            # Foydalanuvchi tilini aktivlashtirish
            if user.language_code:
                activate(user.language_code)
        except User.DoesNotExist:
            messages.error(request, _("Foydalanuvchi topilmadi. Iltimos, botda /start buyrug'ini bering."))
            return redirect(reverse('core:some_error_page')) # Misol

        # Agar foydalanuvchi allaqachon ma'lumotlarini to'ldirgan bo'lsa (masalan, institution mavjud bo'lsa)
        # uni fanlar sahifasiga yo'naltirish mumkin. Bu logikani keyinroq qo'shamiz.
        # if user.institution:
        #     return redirect(reverse('core:subjects_list')) # Faraziy URL

        form = self.form_class(instance=user) # Mavjud ma'lumotlar bilan formani to'ldirish
        form.fields['telegram_id_hidden'].initial = telegram_id # Yashirin maydonni to'ldirish
        return render(request, self.template_name, {'form': form, 'telegram_user_id': telegram_id})

    def post(self, request, *args, **kwargs):
        telegram_id_from_form = request.POST.get('telegram_id_hidden') # Yashirin maydondan olish
        # Yoki URL dan olish (agar URLda telegram_id bo'lsa, lekin WebApp URLida GET parametrda keladi)
        telegram_id_from_get = request.GET.get('tgWebAppStartParam')

        telegram_id = telegram_id_from_form or telegram_id_from_get

        if not telegram_id:
            messages.error(request, _("Telegram ID topilmadi. Xatolik."))
            return redirect(reverse('core:some_error_page')) # Misol

        try:
            user = User.objects.get(telegram_id=telegram_id)
            if user.language_code:
                activate(user.language_code)
        except User.DoesNotExist:
            messages.error(request, _("Foydalanuvchi topilmadi. Qayta urinib ko'ring."))
            return redirect(reverse('core:some_error_page')) # Misol

        form = self.form_class(request.POST, instance=user) # POST ma'lumotlari va mavjud user bilan

        if form.is_valid():
            form.save()
            messages.success(request, _("Ma'lumotlaringiz muvaffaqiyatli saqlandi!"))
            # Keyingi sahifaga yo'naltirish (masalan, fanlar ro'yxati)
            # Bu URLni hali yaratmadik, shuning uchun vaqtinchalik bosh sahifaga
            # `user` obyekti endi `request.user` emas, shuning uchun `user.id` yoki `user.telegram_id` dan foydalanish kerak
            # subjects_url = reverse('core:subjects_list_url_name') + f'?user_id={user.telegram_id}' # Yoki User.id
            # return redirect(subjects_url)
            # Hozircha dummy redirect
            # Botga xabar yuborish kerakki, forma to'ldirildi. Buni signal orqali qilish mumkin.
            return redirect(reverse('core:registration_success_page')) # Yoki fanlar sahifasi
        else:
            print(form.errors)
            # Xatoliklarni ko'rsatish uchun formani qayta render qilish
            # Yashirin maydonni qayta to'ldirish (agar yo'qolgan bo'lsa)
            if not form.data.get('telegram_id_hidden') and telegram_id:
                mutable_post = request.POST.copy()
                mutable_post['telegram_id_hidden'] = telegram_id
                form = self.form_class(mutable_post, instance=user)
                # Formani qayta validatsiya qilish shart emas, chunki xatolar allaqachon mavjud
            messages.error(request, _("Formani to'ldirishda xatoliklar mavjud. Iltimos, tekshirib qayta urinib ko'ring."))
        return render(request, self.template_name, {'form': form, 'telegram_user_id': telegram_id})


# Vaqtinchalik sahifalar (keyinroq to'g'rilanadi)
def some_error_page_view(request):
    return render(request, 'error_page.html', {'message': _("Xatolik yuz berdi.")})

def registration_success_page_view(request):
    # Foydalanuvchiga telegram orqali WebAppni yopishni aytish kerak bo'lishi mumkin
    # Bu yerda telegram.WebApp.close() ni chaqirish uchun JS kerak bo'ladi
    return render(request, 'registration_success.html', {'message': _("Muvaffaqiyatli ro'yxatdan o'tdingiz!")})




class EducationTypeListAPIView(ListAPIView):
    queryset = EducationType.objects.all().order_by('id') # Yoki name_uz bo'yicha
    serializer_class = EducationTypeSerializer
    # permission_classes = [AllowAny] # Hamma uchun ochiq

class InstitutionListAPIView(ListAPIView):
    serializer_class = InstitutionSerializer
    # permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Institution.objects.all()
        education_type_id = self.request.query_params.get('education_type_id')
        if education_type_id:
            queryset = queryset.filter(education_type_id=education_type_id)
        return queryset.order_by('id') # Yoki name_uz bo'yicha

class EducationLevelListAPIView(ListAPIView): # OTM uchun
    queryset = EducationLevel.objects.all().order_by('id')
    serializer_class = EducationLevelSerializer
    # permission_classes = [AllowAny]
    # Agar faqat OTM tanlanganda kerak bo'lsa, bu yerda ham filtr qo'shish mumkin,
    # lekin hozircha barchasini qaytaramiz, JS logikasi hal qiladi.

class FacultyListAPIView(ListAPIView):
    serializer_class = FacultySerializer
    # permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Faculty.objects.all()
        institution_id = self.request.query_params.get('institution_id')
        if institution_id:
            queryset = queryset.filter(institution_id=institution_id)
        return queryset.order_by('id') # Yoki name_uz bo'yicha