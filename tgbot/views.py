# tgbot/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models import User, Test
from .serializers import (
    UserCreateSerializer,
    UserLanguageUpdateSerializer,
    UserPhoneUpdateSerializer,
    UserDetailSerializer
)
from django.utils.translation import gettext_lazy as _
from asgiref.sync import sync_to_async # Import qilingan

# aget_object_or_404 ni ham sync_to_async bilan ishlatish kerak bo'ladi
# yoki get_object_or_404 dan foydalanish
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
import pandas as pd
from io import BytesIO



class UserRegisterAPIView(APIView):
    # async def post(...) o'rniga def post(...)
    def post(self, request, *args, **kwargs):
        telegram_id = request.data.get('telegram_id')
        if not telegram_id:
            return Response({"error": _("Telegram ID majburiy.")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # User.objects.aget o'rniga User.objects.get
            user = User.objects.get(telegram_id=telegram_id)
            serializer = UserDetailSerializer(user)
            return Response({"message": _("Foydalanuvchi allaqachon mavjud."), "user": serializer.data}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            serializer = UserCreateSerializer(data=request.data)
            if serializer.is_valid():
                # User.objects.acreate o'rniga serializer.save() (agar ModelSerializer bo'lsa)
                # Yoki User.objects.create()
                user = serializer.save() # ModelSerializer.save() sinxron
                response_serializer = UserDetailSerializer(user)
                return Response({"message": _("Foydalanuvchi muvaffaqiyatli ro'yxatdan o'tkazildi."), "user": response_serializer.data}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailAPIView(APIView):
    def get(self, request, telegram_id, *args, **kwargs):
        user = get_object_or_404(User, telegram_id=telegram_id)
        serializer = UserDetailSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PUT metodi ham sinxron qilinadi
    def put(self, request, telegram_id, *args, **kwargs):
        user = get_object_or_404(User, telegram_id=telegram_id)
        serializer_instance = None # O'zgaruvchini e'lon qilish

        if 'language_code' in request.data and len(request.data) == 1:
             serializer_instance = UserLanguageUpdateSerializer(user, data=request.data, partial=True)
        elif 'phone_number' in request.data and len(request.data) == 1:
             serializer_instance = UserPhoneUpdateSerializer(user, data=request.data, partial=True)
        else:
            return Response({"error": _("Faqat til yoki telefon raqamini yangilash mumkin.")}, status=status.HTTP_400_BAD_REQUEST)

        if serializer_instance.is_valid():
            serializer_instance.save()
            return Response(UserDetailSerializer(user).data, status=status.HTTP_200_OK)
        return Response(serializer_instance.errors, status=status.HTTP_400_BAD_REQUEST)


class UserSetLanguageAPIView(APIView):
    def post(self, request, telegram_id, *args, **kwargs):
        user = get_object_or_404(User, telegram_id=telegram_id)
        serializer = UserLanguageUpdateSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": _("Til muvaffaqiyatli yangilandi."), "language_code": user.language_code}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserSetPhoneAPIView(APIView):
    def post(self, request, telegram_id, *args, **kwargs):
        user = get_object_or_404(User, telegram_id=telegram_id)
        serializer = UserPhoneUpdateSerializer(user, data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response({"message": _("Telefon raqami muvaffaqiyatli yangilandi."), "phone_number": user.phone_number}, status=status.HTTP_200_OK)
            except serializers.ValidationError as e:
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





class ExportTestsAPIView(APIView):
    # Bu viewni himoyalash kerak (masalan, faqat adminlar uchun)
    # permission_classes = [IsAdminUser] # Agar DRF ishlatsangiz
    # Yoki custom decorator bilan

    def get(self, request, *args, **kwargs):
        # Xavfsizlik tekshiruvi (masalan, maxsus token yoki admin huquqi)
        # Misol uchun, oddiy 'secret_key' parametri bilan tekshirish (production uchun yaroqsiz!)
        # secret_key_from_request = request.GET.get('secret_key')
        # if not secret_key_from_request or secret_key_from_request != "SIZNING_MAXFIY_KALITINGIZ":
        #     return JsonResponse({"error": "Unauthorized"}, status=401)

        try:
            tests_queryset = Test.objects.select_related(
                'user__education_type',
                'user__institution__education_type',
                'user__education_level',
                'user__faculty'
            ).prefetch_related(
                'questions__subject' # Testdagi savollar va ularning fanlari
            ).order_by('-started_at').all()

            if not tests_queryset.exists():
                return JsonResponse({"message": _("Eksport uchun test ma'lumotlari topilmadi.")}, status=404)

            data_for_excel = []
            # DataFrame uchun ustun nomlari (tarjima qilingan)
            column_names = {
                'test_id': str(_('Test ID')),
                'tg_id': str(_('Telegram ID')),
                'name': str(_('Atı')),
                'surname': str(_('Familiyası')),
                'patronymic': str(_('Ákesiniń Atı')),
                'phone': str(_('Telefon')),
                'edu_type': str(_('Bilimlendiriw Túri')),
                'institution': str(_('Mákeme')),
                'edu_level_otm': str(_('Basqısh (JOO)')),
                'faculty_otm': str(_('Fakultet (JOO)')),
                'course': str(_('Kurs')),
                'test_date_started': str(_('Test Baslanıw Waqıtı')),
                'test_date_completed': str(_('Test Tamamlanıw Waqıtı')),
                'score': str(_('Nátiyje (Ball)')),
                'total_q': str(_('Jámi Sorawlar')),
                'time_spent': str(_('Sarplaǵan Waqıtı (s)')),
                'voucher_code': str(_('Sertifikat Kodı')),
            }
            # Agar User modelida name, surname, patronymic alohida bo'lsa:
            # column_names['name'] = str(_('Atı'))
            # column_names['surname'] = str(_('Familiyası'))
            # column_names['patronymic'] = str(_('Ákesiniń Atı'))


            for test_obj in tests_queryset:
                user = test_obj.user
                
                row_data = {
                    column_names['test_id']: test_obj.id,
                    column_names['tg_id']: user.telegram_id,
                    column_names['name']: user.name or "",
                    column_names['surname']: user.surname or "",
                    column_names['patronymic']: user.patronymic or "",
                    column_names['phone']: user.phone_number or "",
                    column_names['edu_type']: str(user.education_type.name_kaa) if user.education_type else "",
                    column_names['institution']: str(user.institution.name_kaa) if user.institution else "",
                    column_names['edu_level_otm']: str(user.education_level.name_kaa) if user.education_level else "",
                    column_names['faculty_otm']: str(user.faculty.name_kaa) if user.faculty else "",
                    column_names['course']: user.course_year or "",
                    column_names['test_date_started']: timezone.localtime(test_obj.started_at).strftime('%Y-%m-%d %H:%M') if test_obj.started_at else "",
                    column_names['test_date_completed']: timezone.localtime(test_obj.completed_at).strftime('%Y-%m-%d %H:%M') if test_obj.completed_at else "",
                    column_names['score']: test_obj.score if test_obj.score is not None else "",
                    column_names['total_q']: test_obj.questions.count(),
                    column_names['time_spent']: test_obj.time_spent_seconds if test_obj.time_spent_seconds is not None else "",
                    column_names['voucher_code']: test_obj.voucher_code or "",
                }
                # Agar User modelida name, surname, patronymic alohida bo'lsa:
                # row_data[column_names['name']] = user.name or ""
                # row_data[column_names['surname']] = user.surname or ""
                # row_data[column_names['patronymic']] = user.patronymic or ""
                data_for_excel.append(row_data)

            df = pd.DataFrame(data_for_excel)
            
            output = BytesIO()
            sheet_name_str = str(_('Test_Natijalari'))

            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name=sheet_name_str)
                worksheet = writer.sheets[sheet_name_str]
                for idx, col_name_proxy in enumerate(df.columns):
                    col_name_str = str(col_name_proxy)
                    series = df[col_name_proxy]
                    try:
                        data_max_len = series.fillna('').astype(str).map(len).max()
                    except Exception:
                        data_max_len = 0
                    header_len = len(col_name_str)
                    max_len = max(data_max_len, header_len) + 2
                    worksheet.set_column(idx, idx, max_len)

            output.seek(0)

            filename = f"test_results_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            response = HttpResponse(
                output,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            # logger.error(f"Error exporting tests to Excel via API: {e}", exc_info=True) # Agar logger sozlagan bo'lsangiz
            print(f"Error exporting tests to Excel via API: {e}") # Oddiy print
            import traceback
            traceback.print_exc() # Batafsil xato uchun
            return JsonResponse({"error": _("Excel faylini yaratishda xatolik yuz berdi."), "details": str(e)}, status=500)