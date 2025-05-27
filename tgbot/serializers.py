from rest_framework import serializers
from core.models import User
from django.utils.translation import gettext_lazy as _

class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['telegram_id', 'username'] # Botdan keladigan dastlabki ma'lumotlar
        # `username` majburiy emas, shuning uchun `required=False` qo'shish mumkin
        # extra_kwargs = {'username': {'required': False, 'allow_null': True}}

class UserLanguageUpdateSerializer(serializers.Serializer): # ModelSerializer emas, chunki faqat bitta maydonni yangilaymiz
    language_code = serializers.ChoiceField(choices=User.LANGUAGE_CHOICES)

    def update(self, instance, validated_data):
        instance.language_code = validated_data.get('language_code', instance.language_code)
        instance.save()
        return instance

class UserPhoneUpdateSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

    def update(self, instance, validated_data):
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        try:
            instance.save()
        except Exception as e: # Masalan, IntegrityError (unique constraint)
            raise serializers.ValidationError({"phone_number": _("Bu telefon raqami allaqachon mavjud.")})
        return instance

class UserDetailSerializer(serializers.ModelSerializer): # Foydalanuvchi ma'lumotlarini qaytarish uchun
    class Meta:
        model = User
        fields = ['telegram_id', 'full_name', 'username', 'phone_number', 'language_code']