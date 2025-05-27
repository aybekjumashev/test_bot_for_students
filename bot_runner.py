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
    builder.button(text="🇺🇿 O'zbekcha", callback_data="setlang_uz")
    builder.button(text="ҚҚ Қарақалпақша", callback_data="setlang_kaa") # To'g'ri qoraqalpoqcha yozing
    builder.button(text="🇷🇺 Русский", callback_data="setlang_ru")
    builder.adjust(1) # Har bir tugma yangi qatorda
    return builder.as_markup()

def request_contact_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def channels_keyboard(subscribed_all=False): # Kanallarga a'zolikni tekshirish uchun
    builder = InlineKeyboardBuilder()
    # Kanallaringiz linklarini qo'shing
    builder.button(text="Kanal 1", url="https://t.me/your_channel_1")
    builder.button(text="Kanal 2", url="https://t.me/your_channel_2")
    if subscribed_all: # Bu funksiya hozircha to'liq ishlamaydi, shunchaki keyingi qadam uchun
        builder.button(text="✅ Tekshirildi, davom etish", callback_data="channels_checked_proceed")
    else:
        builder.button(text="🔁 Tekshirish", callback_data="check_channels") # Haqiqiy tekshiruv yo'q
    builder.adjust(1)
    return builder.as_markup()

def start_test_webapp_keyboard(user_id: int, lang_code: str):
    # Domen nomini .env dan oling yoki to'g'ridan-to'g'ri yozing
    # Masalan, WEBAPP_URL="https://seningdomening.com"
    # Til prefiksini qo'shish kerak
    webapp_url = f"{WEBAPP_BASE_URL}" # URL ni to'g'rilang
    logger.info(f"Generated WebApp URL: {webapp_url}")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Testni Boshlash", url=webapp_url)]
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
            "Assalomu alaykum! Tilni tanlang:\n"
            "Ҳүрметли қатнасыўшы! Тилди сайлаң:\n"
            "Здравствуйте! Выберите язык:",
            reply_markup=language_keyboard()
        )
    elif api_response and "error" in api_response and api_response.get("status_code") == 400 and "telegram_id" in api_response["error"]:
         await message.answer("Botga qayta /start bosing.") # Agar ID kelmasa
    else:
        await message.answer("Xatolik yuz berdi. Keyinroq urinib ko'ring.")
        logger.error(f"Failed to register/get user {user_id}: {api_response}")


@dp.callback_query(F.data.startswith("setlang_"))
async def process_language_select(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    lang_code = callback_query.data.split("_")[1]

    api_response = await api_request("POST", f"users/{user_id}/set-language/", data={"language_code": lang_code})

    if api_response and "error" not in api_response:
        await callback_query.message.edit_text(
            {"uz": "Til tanlandi. Davom etish uchun kanallarimizga a'zo bo'ling:",
             "kaa": "Тил сайланды. Даўам етиў ушын каналларымызға ағза болың:", # To'g'rilang
             "ru": "Язык выбран. Для продолжения подпишитесь на наши каналы:"}
            .get(lang_code, "Kanallarimizga a'zo bo'ling:"),
            reply_markup=channels_keyboard()
        )
    else:
        await callback_query.message.answer("Tilni saqlashda xatolik. Qaytadan urinib ko'ring.")
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
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logger.warning(f"Could not edit reply markup for user {user_id}: {e}")


    # 2. Yangi xabar yuborish va unga ReplyKeyboardMarkup biriktirish
    await callback_query.message.answer( # Yoki bot.send_message(chat_id=callback_query.message.chat.id, ...)
        text=(
            {"uz": "Rahmat! Endi telefon raqamingizni yuboring.",
             "kaa": "Рахмет! Енди телефон номериңизди жибериң.", # To'g'rilang
             "ru": "Спасибо! Теперь отправьте свой номер телефона."}
            .get(lang_code, "Telefon raqamingizni yuboring.")
        ),
        reply_markup=request_contact_keyboard()
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
    lang_code = user_data.get("user", {}).get("language_code", "uz") if user_data and "user" in user_data else "uz"

    if api_response and "error" not in api_response:        
        await message.answer(
            "...", # Qandaydir kichik xabar, masalan, nuqtalar
            reply_markup=types.ReplyKeyboardRemove()
        )
        await message.answer(
            {"uz": "Telefon raqamingiz qabul qilindi! Testni boshlash uchun quyidagi tugmani bosing.",
             "kaa": "Телефоныңыз қабыл етилди! Тестти баслаў ушын төмендеги дүймени басың.", # To'g'rilang
             "ru": "Ваш номер телефона принят! Нажмите кнопку ниже, чтобы начать тест."}
            .get(lang_code, "Testni boshlash uchun quyidagi tugmani bosing."),
            reply_markup=start_test_webapp_keyboard(user_id, lang_code)
        )
    elif api_response and "error" in api_response and "phone_number" in api_response.get("error", {}):
        # Agar telefon raqami band bo'lsa (API dan keladigan xato)
         await message.answer(api_response["error"]["phone_number"][0]) # Xato matnini ko'rsatish
    else:
        await message.answer(
            {"uz": "Telefon raqamini saqlashda xatolik. Qaytadan urinib ko'ring.",
             "kaa": "Телефон номерин сақлаўда қәтелик. Қайтадан урынып көриң.", # To'g'rilang
             "ru": "Ошибка при сохранении номера телефона. Пожалуйста, попробуйте еще раз."}
            .get(lang_code, "Xatolik. Qaytadan urinib ko'ring.")
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