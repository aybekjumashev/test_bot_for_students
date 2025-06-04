# bot_runner.py
import asyncio
import logging
import os

import httpx # Yoki aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder # Yangi InlineKeyboardBuilder
from dotenv import load_dotenv
from io import BytesIO
from aiogram.enums import ChatMemberStatus

load_dotenv(override=True) # .env faylidagi o'zgaruvchilarni yuklash


# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = os.getenv("BOT_TOKEN")
DJANGO_API_BASE_URL = os.getenv("DJANGO_API_URL", "http://127.0.0.1:8000/api/tg") 
WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL", "http://127.0.0.1:8000") 
CHANNELS_URL = os.getenv("CHANNELS_URL", "https://t.me/addlist/K4iMXLXFYLQzYzEy") 
TARGET_CHANNEL_ID = -1002514048287
CHANNELS_ENV = os.getenv("REQUIRED_CHANNELS", "")


REQUIRED_CHANNELS_LIST = []
if CHANNELS_ENV:
    for ch in CHANNELS_ENV.split(','):
        ch_stripped = ch.strip()
        if ch_stripped:
            if ch_stripped.startswith('@'):
                REQUIRED_CHANNELS_LIST.append(ch_stripped)
            else:
                try:
                    REQUIRED_CHANNELS_LIST.append(int(ch_stripped))
                except ValueError:
                    logger.warning(f"Noto'g'ri kanal IDsi yoki username formatı: {ch_stripped}")



# Bot va Dispatcher obyektlari
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# {"kaa": "", "ru": "","uz": ""}.get(lang_code, "")

async def check_all_channel_memberships(user_id: int) -> bool:
    """
    Foydalanuvchining berilgan barcha kanallarga a'zoligini tekshiradi.

    Args:
        bot_instance: Aiogram Bot obyekti.
        user_id: Tekshirilayotgan foydalanuvchining Telegram ID si.
        channel_ids_list: Tekshiriladigan kanallarning ID (int) yoki @username (str) ro'yxati.

    Returns:
        bool: Agar foydalanuvchi barcha kanallarga a'zo bo'lsa True, aks holda False.
    """
    bot_instance = bot
    channel_ids_list = REQUIRED_CHANNELS_LIST # Global o'zgaruvchini olish
    if not channel_ids_list: # Agar tekshiriladigan kanal bo'lmasa
        return True # Barcha (bo'sh) shartlar bajarildi deb hisoblash

    all_subscribed = True
    for channel_id_or_username in channel_ids_list:
        print(channel_id_or_username)
        try:
            # Agar bot_instance shu funksiya ichida global bo'lmasa, uni parametr orqali olish kerak.
            # Men bot_instance ni parametr sifatida qo'shdim.
            member = await bot_instance.get_chat_member(chat_id=channel_id_or_username, user_id=user_id)
            
            # Foydalanuvchi statusi 'member', 'administrator' yoki 'creator' bo'lishi kerak.
            # 'left' (chiqib ketgan) yoki 'kicked' (chetlatilgan) bo'lmasligi kerak.
            # 'restricted' statusi ham a'zo emas deb hisoblanishi mumkin (agar shunday xohlasangiz).
            if member.status not in [
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.CREATOR,
                # types.ChatMemberStatus.RESTRICTED # Agar restricted ham a'zo hisoblansa, qo'shing
            ]:
                all_subscribed = False
                logger.info(f"Foydalanuvchi {user_id} kanalga ({channel_id_or_username}) a'zo emas. Status: {member.status}")
                break # Bitta kanalga a'zo bo'lmasa, qolganini tekshirish shart emas
            else:
                logger.debug(f"Foydalanuvchi {user_id} kanalga ({channel_id_or_username}) a'zo. Status: {member.status}")

        except Exception as e:
            # Bu xatoliklar Telegram API tomonidan qaytarilishi mumkin:
            # - ChatNotFound: Agar kanal ID/username noto'g'ri bo'lsa.
            # - UserNotFound: Agar user_id noto'g'ri bo'lsa (bu kamdan-kam uchraydi, chunki user_id odatda message.from_user.id dan olinadi).
            # - BotKicked: Agar bot kanaldan chiqarib yuborilgan bo'lsa.
            # - BotIsNotAMember: Agar bot kanalga a'zo bo'lmasa va kanal public bo'lmasa (yoki maxsus huquqlar kerak bo'lsa).
            logger.warning(f"Kanalga ({channel_id_or_username}) a'zolikni tekshirishda xatolik (user: {user_id}): {e}")
            # Xatolik yuzaga kelganda, foydalanuvchi a'zo emas deb hisoblaymiz,
            # chunki a'zolikni tasdiqlay olmadik.
            all_subscribed = True
            break # Xatolik bo'lsa, davom etmaymiz

    return all_subscribed



async def get_all_user_ids_from_api():
    """Django API orqali barcha foydalanuvchi Telegram IDlarini oladi."""
    base_url = DJANGO_API_BASE_URL.replace("/tg", "")  # /tg ni olib tashlash, agar kerak bo'lsa
    DJANGO_API_URL_FOR_IDS = f"{base_url}/get-all-user-tg-ids/"  # API endpointini to'g'rilang

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(DJANGO_API_URL_FOR_IDS)
            response.raise_for_status()
            data = response.json()
            if data.get("success") and "telegram_ids" in data:
                return data["telegram_ids"]
            else:
                logger.error(f"API dan IDlarni olishda xatolik: {data.get('error', 'Nomalum javob')}")
                return []
        except httpx.HTTPStatusError as e:
            logger.error(f"API ga IDlar uchun murojaatda HTTP xatosi: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"API dan IDlarni olishda kutilmagan xato: {e}", exc_info=True)
            return []


# --- API bilan ishlash uchun yordamchi funksiyalar ---
async def api_request(method: str, endpoint: str, data: dict = None, params: dict = None):
    url = f"{DJANGO_API_BASE_URL}/{endpoint}"
    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, params=params)
            elif method.upper() == "POST":
                response = await client.post(url, json=data, params=params)
            elif method.upper() == "PUT":
                response = await client.put(url, json=data, params=params)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None

            response.raise_for_status() # Agar 4xx yoki 5xx status kodi bo'lsa xatolik chiqaradi
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"API request failed to {url} with status {e.response.status_code}: {e.response.text}")
            return {"error": e.response.json() if e.response.content else str(e), "status_code": e.response.status_code}
        except httpx.RequestError as e:
            logger.error(f"API request failed to {url}: {str(e)}")
            return {"error": str(e), "status_code": None}
        except Exception as e:
            logger.error(f"An unexpected error occurred during API request to {url}: {str(e)}")
            return {"error": str(e), "status_code": None}


# --- Keyboardlar ---
def language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Qaraqalpaqsha", callback_data="setlang_kaa")
    builder.button(text="Русский", callback_data="setlang_ru")
    builder.button(text="O'zbekcha", callback_data="setlang_uz")
    builder.adjust(1) # Har bir tugma yangi qatorda
    return builder.as_markup()

def request_contact_keyboard(lang_code):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text={"kaa": "📱 Telefon nomerdi jiberiw", "ru": "📱 Отправить номер телефона","uz": "📱 Telefon raqamni yuborish"}.get(lang_code, "📱 Telefon nomerdi jiberiw"), request_contact=True)]],    
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def channels_keyboard(lang_code): # Kanallarga a'zolikni tekshirish uchun
    builder = InlineKeyboardBuilder()
    # Kanallaringiz linklarini qo'shing
    builder.button(text="Nukus-2025", url=CHANNELS_URL)
    builder.button(text={"kaa": "🔁 Tekseriw", "ru": "🔁 Проверить","uz": "🔁 Tekshirish"}.get(lang_code, "🔁 Tekseriw"), callback_data="check_channels")  
    builder.adjust(1)
    return builder.as_markup()

def start_test_webapp_keyboard(user_id: int, lang_code: str):
    # Domen nomini .env dan oling yoki to'g'ridan-to'g'ri yozing
    # Masalan, WEBAPP_URL="https://seningdomening.com"
    # Til prefiksini qo'shish kerak
    webapp_url = f"{WEBAPP_BASE_URL}/?startapp={user_id}" # URL ni to'g'rilang
    logger.info(f"Generated WebApp URL: {webapp_url}")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text={"kaa": "🚀 Testti Baslaw", "ru": "🚀 Начать тест","uz": "🚀 Testni Boshlash"}.get(lang_code, "🚀 Testti Baslaw"), url=webapp_url)] 
    ])
    return keyboard

# --- Handlerlar ---
@dp.message(CommandStart())
async def send_welcome(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Django API ga foydalanuvchini ro'yxatdan o'tkazish/tekshirish uchun so'rov
    api_response = await api_request("POST", "users/register/", data={"telegram_id": user_id, "username": username})

    if api_response and "error" not in api_response:
        await message.answer(
            "🗺️ Ózińizge qolaylı tildi saylań \n🗺️ Выберите удобный для вас язык \n🗺️ O'zingiz uchun qulayli tilni tanlang",
            reply_markup=language_keyboard()
        )
    elif api_response and "error" in api_response and api_response.get("status_code") == 400 and "telegram_id" in api_response["error"]:
         await message.answer("Botqa qaytadan /start basıń.") # Agar ID kelmasa
    else:
        await message.answer("Qátelik júz berdi.")
        logger.error(f"Failed to register/get user {user_id}: {api_response}")



@dp.message(Command("export_data"))
async def export_all_data_command(message: types.Message):
    # if message.from_user.id not in TELEGRAM_ADMIN_IDS: # Agar IsAdmin filtrini ishlatmasangiz
    #     await message.reply("Sizda bu buyruqni bajarish uchun ruxsat yo'q.")
    #     return

    load_msg = await message.reply("Maǵlıwmatlar Excel faylına tayarlanbaqta...")

    # API endpointiga so'rov yuborish
    # API_EXPORT_URL = f"{os.getenv('DJANGO_BASE_URL', 'http://127.0.0.1:8000')}/api/export-all-tests/"
    # Agar DJANGO_API_BASE_URL da /api/tg/ bo'lsa, undan /tg/ ni olib tashlash kerak
    # Yoki yangi DJANGO_CORE_API_URL yaratish
    base_django_url = DJANGO_API_BASE_URL.replace("/tg", "") # Taxminiy
    api_export_url = f"{base_django_url}/export-all-tests/" # CONFIG/urls.py dagi yo'lga moslang

    # Agar API himoyalangan bo'lsa, token yoki boshqa parametr qo'shish kerak
    # params = {"secret_key": "SIZNING_MAXFIY_KALITINGIZ"} # Misol uchun

    async with httpx.AsyncClient(timeout=60.0) as client: # Kattaroq timeout
        try:
            # response = await client.get(api_export_url, params=params)
            response = await client.get(api_export_url) # Hozircha himoyasiz
            response.raise_for_status()

            # Faylni Telegramga yuborish
            file_bytes = BytesIO(response.content)
            file_name = response.headers.get(
                "Content-Disposition", "attachment; filename=test_results.xlsx"
            ).split("filename=")[1].strip('"') or "test_results.xlsx"
            
            input_file = types.BufferedInputFile(file_bytes.getvalue(), filename=file_name)
            await message.reply_document(input_file, caption="Barlıq test nátiyjeleri.")
            await load_msg.delete() # Yuklash xabarini o'chirish

        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            try:
                error_json = e.response.json()
                error_text = error_json.get("error", error_json.get("detail", str(error_json)))
            except:
                pass
            await message.reply(f"Excel faylın alıwda qátelik júz berdi (Server qátesi {e.response.status_code}):\n{error_text}")
            logger.error(f"Failed to get Excel export from API: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            await message.reply(f"Excel faylın alıwda jalǵanıwda qátelik: {e}")
            logger.error(f"Failed to connect for Excel export: {e}")
        except Exception as e:
            await message.reply(f"Excel faylın alıwda kútilmegen qátelik: {e}")
            logger.error(f"Unexpected error during Excel export: {e}", exc_info=True)


@dp.callback_query(F.data.startswith("setlang_"))
async def process_language_select(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    lang_code = callback_query.data.split("_")[1]

    api_response = await api_request("POST", f"users/{user_id}/set-language/", data={"language_code": lang_code})

    if api_response and "error" not in api_response:
        if not await check_all_channel_memberships(user_id):
            await callback_query.message.edit_text(
                {"kaa": "Telegram bottan paydalanıp arnawlı sertifikattı alıw ushın tómendegi kanallarǵa aǵza bolıń 👇👇👇", 
                "ru": "Подпишитесь на каналы ниже, чтобы получить специальный сертификат с помощью Telegram-бота 👇👇👇",
                "uz": "Telegram bottan foydalanib maxsus sertifikatni olish uchun pastdagi kanallarga a'zo bo'ling 👇👇👇"}
                .get(lang_code, "Dawam etiw ushın kanallarımızǵa aǵza bolıń:"),
                reply_markup=channels_keyboard(lang_code)
            )
        else:
            await callback_query.message.answer( # Yoki bot.send_message(chat_id=callback_query.message.chat.id, ...)
                text=(
                    {"uz": "Telefon raqamingizni yuboring.",
                    "kaa": "Telefon nomerińizdi jiberiń.", # To'g'rilang
                    "ru": "Теперь отправьте свой номер телефона."}
                    .get(lang_code, "Telefon nomerińizdi jiberiń.")
                ),
                reply_markup=request_contact_keyboard(lang_code)
            )
            await callback_query.message.delete() # Inline klaviaturani olib tashlash
    else:
        await callback_query.message.answer("Tildi saylawda qátelik.")
        logger.error(f"Failed to set language for {user_id}: {api_response}")
    await callback_query.answer()


@dp.callback_query(F.data == "check_channels") # Yoki "channels_checked_proceed"
async def process_channels_check(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    # Foydalanuvchidan tilni olamiz (agar saqlangan bo'lsa)
    user_api_response = await api_request("GET", f"users/{user_id}/") # O'zgaruvchi nomini aniqroq qildim
    lang_code = user_api_response.get("language_code", "uz") if user_api_response and "error" not in user_api_response else "uz" # API javobini tekshirish

    if not await check_all_channel_memberships(user_id):
        await callback_query.answer(
            text={"kaa": "Telegram kanallarǵa tolıq aǵza bolıwıńız kerek!", "ru": "Подпишитесь на все каналы, чтобы продолжить!","uz": "Telegram kanallarga to'liq a'zo bo'ling!"}.get(lang_code, "Telegram kanallarǵa tolıq aǵza bolıwıńız kerek!"), 
            show_alert=True
        )
        return

    # 1. Avvalgi inline klaviaturani olib tashlash uchun xabarni tahrirlash (ixtiyoriy, lekin chiroyli)
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.warning(f"Could not edit reply markup for user {user_id}: {e}")


    # 2. Yangi xabar yuborish va unga ReplyKeyboardMarkup biriktirish
    await callback_query.message.answer( # Yoki bot.send_message(chat_id=callback_query.message.chat.id, ...)
        text=(
            {"uz": "Telefon raqamingizni yuboring.",
             "kaa": "Telefon nomerińizdi jiberiń.", # To'g'rilang
             "ru": "Теперь отправьте свой номер телефона."}
            .get(lang_code, "Telefon nomerińizdi jiberiń.")
        ),
        reply_markup=request_contact_keyboard(lang_code)
    )
    await callback_query.answer() # Callback query ga javob berishni unutmang


@dp.message(F.contact)
async def process_contact(message: Message):
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    api_response = await api_request("POST", f"users/{user_id}/set-phone/", data={"phone_number": phone_number})

    user_data = await api_request("GET", f"users/{user_id}/") # Tilni olish uchun
    lang_code = user_data.get("language_code", "uz") if user_data and "error" not in user_data else "uz"

    if api_response and "error" not in api_response:        
        msg = await message.answer(
            {"kaa": "Maǵlıwmatlarıńız saqlandi.", "ru": "Ваши данные сохранены.","uz": "Ma'lumotlaringiz saqlandi."}.get(lang_code, "Raxmet!"), 
            reply_markup=types.ReplyKeyboardRemove()
        )
        await message.answer(
            {"uz": "Testni boshlash uchun quyidagi tugmani bosing.",
             "kaa": "Testti baslaw ushın tómendegi túymeni basıń.", # To'g'rilang
             "ru": "Нажмите кнопку ниже, чтобы начать тест."}
            .get(lang_code, "Testti baslaw ushın tómendegi túymeni basıń."),
            reply_markup=start_test_webapp_keyboard(user_id, lang_code)
        )
        await msg.delete()
    elif api_response and "error" in api_response and "phone_number" in api_response.get("error", {}):
        # Agar telefon raqami band bo'lsa (API dan keladigan xato)
         await message.answer(api_response["error"]["phone_number"][0]) # Xato matnini ko'rsatish
    else:
        await message.answer(
            {"uz": "Telefon raqamini saqlashda xatolik.",
             "kaa": "Telefon nomerin anıqlawda qátelik.", # To'g'rilang
             "ru": "Ошибка при сохранении номера телефона."}
            .get(lang_code, "Telefon nomerin anıqlawda qátelik.")
        )
        logger.error(f"Failed to set phone for {user_id}: {api_response}")







@dp.channel_post() # Barcha kanallardagi postlarni ushlaydi
async def handle_channel_post(message: types.Message): # Funksiya nomini o'zgartirdim, "post" bilan chalkashmasligi uchun
    if message.chat.id == TARGET_CHANNEL_ID:
        logger.info(f"Kanal ({TARGET_CHANNEL_ID}) dan yangi post qabul qilindi. Foydalanuvchilarga yuborish boshlandi...")
        loading_message = None
        try:
            loading_message = await message.reply('Xabar uzatılmaqta...') # reply() kanal postiga javob qaytaradi
        except Exception as e:
            logger.warning(f"Kanalga 'Xabar uzatilmaqta...' deb javob qaytarib bo'lmadi: {e}")
            # Agar reply ishlamasa (masalan, botda kanalga yozish huquqi yo'q bo'lsa),
            # adminlardan biriga xabar yuborish mumkin
            # await bot.send_message(chat_id=TELEGRAM_ADMIN_IDS[0], text="Kanal postini tarqatish boshlandi...")


        users_telegram_ids = await get_all_user_ids_from_api()

        if not users_telegram_ids:
            logger.warning("API dan foydalanuvchi IDlari olinmadi yoki ro'yxat bo'sh.")
            if loading_message:
                await loading_message.edit_text('Paydalanıwshılar tabılmadı. Xabar jiberiw toxtatıldı.') # loading_message ni tahrirlash
            else:
                # Agar loading_message yuborilmagan bo'lsa, asl postga javob qaytarish
                try:
                    await message.reply('Paydalanıwshılar tabılmadı. Xabar jiberiw toxtatıldı.')
                except Exception as e_reply:
                     logger.error(f"Kanalga xatolik haqida javob qaytarib bo'lmadi: {e_reply}")
            return

        successful_sends = 0
        failed_sends = 0
        
        # Asl xabarni nusxalash (forward o'rniga, "forwarded from" yozuvi bo'lmasligi uchun)
        # send_copy har doim ham barcha turdagi xabarlar uchun ishlamasligi mumkin (masalan, poll)
        # Agar muammo bo'lsa, message.forward() ni ishlatish mumkin.
        for user_id in users_telegram_ids:
            try:
                # message.forward(chat_id=int(user_id)) # Forward qilish varianti
                await bot.copy_message(
                    chat_id=int(user_id),
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    reply_markup=message.reply_markup # Agar asl xabarda inline tugmalar bo'lsa
                )
                successful_sends += 1
                logger.info(f"Xabar {user_id} ga muvaffaqiyatli yuborildi.")
                # Telegram API limitlariga duch kelmaslik uchun pauza
                if successful_sends % 20 == 0: # Har 20 ta xabardan keyin
                    await asyncio.sleep(0.5) # 1 sekund kutish
            except Exception as e:
                failed_sends += 1
                logger.error(f"Xabarni {user_id} ga yuborishda xatolik: {e}")
                # Bu yerda xatolik turlarini aniqroq ushlash mumkin (masalan, BotBlocked, UserDeactivated)
                # if isinstance(e, aiogram.exceptions.TelegramForbiddenError): # Bot bloklangan
                #     logger.warning(f"Foydalanuvchi {user_id} botni bloklagan.")
                # elif isinstance(e, aiogram.exceptions.TelegramNotFound): # Chat topilmadi
                #     logger.warning(f"Foydalanuvchi {user_id} uchun chat topilmadi.")

        result_text = f"✅ Xabar {successful_sends} paydalanıwshıǵa jetkerildi."
        if failed_sends > 0:
            result_text += f"\n❌ {failed_sends} paydalanıwshıǵa jetkeriwde qátelik júz berdi."
        
        if loading_message:
            try:
                await loading_message.edit_text(text=result_text)
            except Exception as e_edit:
                 logger.error(f"loading_message ni tahrirlashda xatolik: {e_edit}")
                 # Agar edit_text ishlamasa, yangi xabar yuborish
                 try:
                    await message.reply(text=result_text)
                 except Exception as e_reply_final:
                     logger.error(f"Kanalga yakuniy javob qaytarib bo'lmadi: {e_reply_final}")

        elif message.chat.id == TARGET_CHANNEL_ID: # Agar loading_message bo'lmasa ham, kanaldan bo'lsa
            try:
                await message.reply(text=result_text)
            except Exception as e_reply_final_alt:
                logger.error(f"Kanalga yakuniy javob qaytarib bo'lmadi (alt): {e_reply_final_alt}")





async def main():
    logger.info("Bot ishga tushmoqda...")
    # Django ilovasi bilan birga ishlash uchun await dp.start_polling() ni
    # Django management command ichida ishlatish mumkin.
    # Yoki alohida jarayon sifatida.
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())