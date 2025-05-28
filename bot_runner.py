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

load_dotenv() # .env faylidagi o'zgaruvchilarni yuklash

API_TOKEN = os.getenv("BOT_TOKEN")
DJANGO_API_BASE_URL = os.getenv("DJANGO_API_URL", "http://127.0.0.1:8000/api/tg") 
WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL", "http://127.0.0.1:8000") 

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot va Dispatcher obyektlari
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# {"kaa": "", "ru": "","uz": ""}.get(lang_code, "")

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
    builder.button(text="Kanal 1", url="https://t.me/your_channel_1")
    builder.button(text="Kanal 2", url="https://t.me/your_channel_2")
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
            "🗺️ Til saylań / Выберите язык / Til tanlang:",
            reply_markup=language_keyboard()
        )
    elif api_response and "error" in api_response and api_response.get("status_code") == 400 and "telegram_id" in api_response["error"]:
         await message.answer("Botqa qaytadan /start basıń.") # Agar ID kelmasa
    else:
        await message.answer("Qátelik júz berdi.")
        logger.error(f"Failed to register/get user {user_id}: {api_response}")


@dp.callback_query(F.data.startswith("setlang_"))
async def process_language_select(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    lang_code = callback_query.data.split("_")[1]

    api_response = await api_request("POST", f"users/{user_id}/set-language/", data={"language_code": lang_code})

    if api_response and "error" not in api_response:
        await callback_query.message.edit_text(
            {"kaa": "Dawam etiw ushın kanallarımızǵa aǵza bolıń:", 
             "ru": "Для продолжения подпишитесь на наши каналы:",
             "uz": "Davom etish uchun kanallarimizga a'zo bo'ling:"}
            .get(lang_code, "Dawam etiw ushın kanallarımızǵa aǵza bolıń:"),
            reply_markup=channels_keyboard(lang_code)
        )
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
            {"kaa": "Raxmet!", "ru": "Спасибо!","uz": "Rahmat!"}.get(lang_code, "Raxmet!"), 
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


async def main():
    logger.info("Bot ishga tushmoqda...")
    # Django ilovasi bilan birga ishlash uchun await dp.start_polling() ni
    # Django management command ichida ishlatish mumkin.
    # Yoki alohida jarayon sifatida.
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())