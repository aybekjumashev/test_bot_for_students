# tgbot/bot_utils.py (yoki core/bot_integration.py)
import httpx
import os
from io import BytesIO
from django.utils.translation import gettext_lazy as _ # Agar Django sozlamalaridan til kerak bo'lsa
from django.conf import settings # BOT_TOKEN ni olish uchun
from django.utils import timezone
from core.models import User # Funksiya ichidan tashqariga olib chiqish mumkin, agar circular import muammosi bo'lmasa
from asgiref.sync import sync_to_async
# Agar get_photo utils.py da bo'lsa:
from core.utils import get_photo # Yoki to'g'ri import yo'li

# Logging sozlamalari (agar kerak bo'lsa)
import logging
logger = logging.getLogger(__name__)

async def send_telegram_photo_message(chat_id: int, caption: str, photo_bytes: BytesIO, parse_mode: str = "HTML"):
    """
    Asinxron ravishda Telegramga rasm bilan xabar yuboradi.
    """
    bot_token = settings.TELEGRAM_BOT_TOKEN # settings.py ga qo'shing
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN topilmadi!")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    
    # photo_bytes ni o'qib, fayl sifatida tayyorlash
    photo_bytes.seek(0) # Pointerni boshiga
    files = {'photo': ('voucher.jpg', photo_bytes, 'image/jpeg')}
    data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': parse_mode}

    async with httpx.AsyncClient(timeout=30.0) as client: # Timeout qo'shish
        try:
            response = await client.post(url, data=data, files=files)
            response.raise_for_status() # Agar 4xx yoki 5xx bo'lsa xato chiqaradi
            logger.info(f"Telegramga xabar muvaffaqiyatli yuborildi (chat_id: {chat_id}). Javob: {response.json()}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"Telegram API xatosi (sendPhoto, chat_id: {chat_id}): {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Telegramga ulanishda xato (sendPhoto, chat_id: {chat_id}): {e}")
        except Exception as e:
            logger.error(f"Telegramga rasm yuborishda kutilmagan xato (chat_id: {chat_id}): {e}")
    return False


async def send_test_result_to_user(
    user_telegram_id: int,
    user_fullname: str,
    score: int,
    total_questions: int,
    voucher_amount_text: str,
    voucher_code: str,
    voucher_image_postfix: str,
    admin_chat_id: int = None
):
    logger.info(f"send_test_result_to_user chaqirildi: user_id={user_telegram_id}, fullname={user_fullname}, voucher_postfix={voucher_image_postfix}")
    
    future_date = (timezone.now() + timezone.timedelta(weeks=1)).strftime("%d.%m.%Y")
    
    message_to_user = f"<b>{user_fullname}, {_('sizning test natijangiz')}: {score}/{total_questions}</b>\n\n"
    if voucher_amount_text and voucher_code:
        message_to_user += f"✅ {_('Siz')} {str(voucher_amount_text)} {_('voucherni qoʻlga kiritdingiz.')}\n" # str() qo'shildi
        message_to_user += f"❗️ {_('Voucherning amal qilish muddati')} {future_date} {_('sanasigacha.')}\n\n"
    else:
        message_to_user += f"{_('Ishtirokingiz uchun rahmat!')}\n\n"
    message_to_user += f"📞 {_('Toʻliq maʻlumot uchun telefon')}: +998 XX XXX XX XX\n"
    message_to_user += f"📌 {_('Manzil')}: Manzilingiz shu yerda\n"

    voucher_template_filename = f"voucher.jpg"
    logger.info(f"Voucher shabloni izlanmoqda: {voucher_template_filename}")

    # get_photo sinxron funksiya, uni sync_to_async bilan chaqirish kerak
    image_bytes = await sync_to_async(get_photo, thread_sensitive=True)( # thread_sensitive=True Pillow uchun kerak bo'lishi mumkin
        fullname=user_fullname,
        date_str=future_date,
        voucher_template_filename=voucher_template_filename,
        num_code=voucher_code,
        subjectname_text=""
    )

    user_message_sent = False
    if image_bytes:
        logger.info(f"Foydalanuvchi {user_telegram_id} uchun voucher rasmi generatsiya qilindi. Telegramga yuborilmoqda...")
        image_bytes.seek(0)
        user_message_sent = await send_telegram_photo_message(
            chat_id=user_telegram_id,
            caption=message_to_user,
            photo_bytes=image_bytes
        )
        if not user_message_sent:
             logger.error(f"Foydalanuvchi {user_telegram_id} ga rasm bilan xabar yuborishda XATOLIK.")
    else:
        logger.warning(f"Foydalanuvchi {user_telegram_id} uchun voucher rasmi generatsiya QILINMADI.")
        # Rasm bo'lmasa, oddiy matnli xabar yuborish
        # Hozircha bu qismni qo'shmaymiz, rasm bilan yuborishga e'tibor qaratamiz

    if admin_chat_id and user_message_sent:
        logger.info(f"Adminga ({admin_chat_id}) natija yuborilmoqda...")
        user_phone = _("Noma'lum")
        user_course = _("Noma'lum")
        user_institution_name = _("Noma'lum")
        user_education_type_name = _("Noma'lum")
        user_education_level_name = _("Noma'lum")
        user_faculty_name = _("Noma'lum")

        try:
            # User obyektini kerakli bog'liq maydonlar bilan birga olish
            user_obj = await User.objects.select_related(
                'institution__education_type', # institution va uning education_type'i
                'education_level',
                'faculty'
            ).aget(telegram_id=user_telegram_id) # aget ishlatiladi

            user_phone = user_obj.phone_number or _("Noma'lum")
            user_course = user_obj.course_year or _("Noma'lum")
            
            if user_obj.institution:
                user_institution_name = user_obj.institution.get_localized_name()
                if user_obj.institution.education_type:
                     user_education_type_name = user_obj.institution.education_type.get_localized_name()
            if user_obj.education_level:
                user_education_level_name = user_obj.education_level.get_localized_name()
            if user_obj.faculty:
                user_faculty_name = user_obj.faculty.get_localized_name()

        except User.DoesNotExist:
            logger.warning(f"Adminga xabar uchun User {user_telegram_id} topilmadi (bu bo'lmasligi kerak edi).")
        except Exception as e: # Boshqa kutilmagan xatolar
            logger.error(f"Adminga xabar tayyorlashda user ma'lumotlarini olishda xato: {e}", exc_info=True)


        admin_caption = (
            f"<b>{_('Yangi Test Natijasi!')}</b>\n\n"
            f"👤 {_('F.I.Sh')}: {user_fullname}\n"
            f"🆔 Telegram ID: {user_telegram_id}\n"
            f"📞 {_('Telefon')}: {user_phone}\n"
            f"🎓 {_('Ta\'lim Turi')}: {user_education_type_name}\n"
            f"🏛️ {_('Muassasa')}: {user_institution_name}\n"
            f"🪜 {_('Bosqich (OTM)')}: {user_education_level_name}\n"
            f"📚 {_('Fakultet (OTM)')}: {user_faculty_name}\n"
            f"📈 {_('Kurs/Sinf')}: {user_course}\n"
            f"📊 {_('Natija')}: {score}/{total_questions}\n"
            f"🎟️ {_('Voucher')}: {str(voucher_amount_text)} ({voucher_code})\n"
            f"🕒 {_('Vaqt')}: {timezone.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        if image_bytes:
            image_bytes.seek(0)
            admin_send_status = await send_telegram_photo_message(
                chat_id=admin_chat_id,
                caption=admin_caption,
                photo_bytes=image_bytes
            )
            if not admin_send_status:
                logger.error(f"Adminga ({admin_chat_id}) rasm bilan xabar yuborishda XATOLIK.")
        else: # Agar rasm bo'lmasa, adminga faqat matn yuborish
            # Hozircha matnli xabar yuborish funksiyasi yo'q, shuning uchun pass
            logger.warning(f"Adminga ({admin_chat_id}) yuborish uchun rasm yo'q, matnli xabar yuborilmadi.")
            pass

    elif admin_chat_id and not user_message_sent:
        logger.warning(f"Foydalanuvchiga xabar yuborilmagani uchun adminga ({admin_chat_id}) yuborilmadi.")
            
    return user_message_sent