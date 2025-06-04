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


async def send_telegram_text_message(chat_id: int, text: str, parse_mode: str = "HTML"):
    """
    Asinxron ravishda Telegramga matnli xabar yuboradi.
    """
    bot_token = settings.TELEGRAM_BOT_TOKEN  # settings.py ga qo'shing
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN topilmadi!")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, data=data)
            response.raise_for_status()
            logger.info(f"Telegramga matnli xabar yuborildi (chat_id: {chat_id}). Javob: {response.json()}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"Telegram API xatosi (sendMessage, chat_id: {chat_id}): {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Telegramga ulanishda xato (sendMessage, chat_id: {chat_id}): {e}")
        except Exception as e:
            logger.error(f"Telegramga matnli xabar yuborishda kutilmagan xato (chat_id: {chat_id}): {e}")
    return False




async def send_test_result_to_user(
    user_telegram_id: int,
    user_fullname: tuple,
    score: tuple,
    total_questions: int,
    voucher_code: str,
):
    logger.info(f"send_test_result_to_user chaqirildi: user_id={user_telegram_id}, fullname={user_fullname}")

    user_message_sent = False
    if score[1] > 80:
        message_to_user = f"<b>{' '.join(user_fullname)}, {_('sizning test natijangiz')}: {score[0]}/{total_questions}</b>\n\n"    
        message_to_user += f"🔥 {_('Ishtirokingiz uchun rahmat!')}\n\n"
        message_to_user += f"📞 {_('Toʻliq maʻlumot uchun telefon')}: +998997794345\n"

        voucher_template_filename = f"voucher.png"
        logger.info(f"Voucher shabloni izlanmoqda: {voucher_template_filename}")
        
        # get_photo sinxron funksiya, uni sync_to_async bilan chaqirish kerak
        image_bytes = await sync_to_async(get_photo, thread_sensitive=True)( # thread_sensitive=True Pillow uchun kerak bo'lishi mumkin
            fullname=user_fullname,
            date_str=timezone.now().strftime("%d.%m.%Y"),
            voucher_template_filename=voucher_template_filename,
            num_code=voucher_code,
            score=score,
        )

        
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
    else:        
        message_to_user = f"<b>{' '.join(user_fullname)}, {_('sizning test natijangiz')}: {score[0]}/{total_questions}</b>\n"    
        message_to_user += f"<b>{_("Foiz korsatkichi")}: {score[1]}%</b>\n\n"    
        message_to_user += f"❗️ {_('Natija 80 foizdan kam bo\'lsa sertifikat berilmaydi! Sizda testni qayta yechib ko\'rish imkoniyati bor.')}\n\n"
        message_to_user += f"📞 {_('Toʻliq maʻlumot uchun telefon')}: +998997794345\n"
        user_message_sent = await send_telegram_text_message(
            chat_id=user_telegram_id,
            text=message_to_user
        )
                
    return user_message_sent