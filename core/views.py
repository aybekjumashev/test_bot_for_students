# tgbot/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models import User
from django.shortcuts import get_object_or_404 # Sinxron, asinxronga o'tkazamiz
from asgiref.sync import sync_to_async # Sinxron funksiyalarni asinxronda chaqirish uchun
from django.utils.translation import gettext_lazy as _