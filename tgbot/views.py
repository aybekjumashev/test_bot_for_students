# tgbot/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models import User
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