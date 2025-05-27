# core/utils.py
import mammoth
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
import os

def convert_docx_to_html(docx_file_field):
    """
    Django FileField da saqlangan DOCX faylni HTML ga o'tkazadi.
    """
    if not docx_file_field:
        return ""
    try:
        # Faylni BytesIO obyektiga o'qish
        docx_bytes = BytesIO(docx_file_field.read())
        docx_file_field.seek(0) # Fayl pointerini boshiga qaytarish, agar qayta o'qish kerak bo'lsa
        
        result = mammoth.convert_to_html(docx_bytes)
        html = result.value # The raw HTML
        # messages = result.messages # Any messages (warnings, errors)
        return html
    except Exception as e:
        print(f"Error converting DOCX to HTML: {e}")
        return "<p>Error displaying question.</p>"


def get_photo(fullname, date_str, base_image_path, num_code, subjectname_text=''):
    """
    Generates a voucher image.
    base_image_path should be an absolute path to the template image.
    """
    try:
        # Asosiy rasmni ochish
        # Fayl yo'lini to'g'ri ko'rsatish kerak. Masalan, settings.STATIC_ROOT dan
        # yoki settings.BASE_DIR bilan birlashtirib.
        # Agar base_image_path nisbiy bo'lsa, uni to'liq yo'lga aylantirish kerak.
        # Masalan: os.path.join(settings.BASE_DIR, 'static', 'vouchers', 'VoucherMatematika1.jpg')
        
        # Agar base_image_path to'liq yo'l bo'lmasa:
        if not os.path.isabs(base_image_path):
            # Bu staticfiles_dirs dagi birinchi papkaga nisbatan bo'lishi mumkin
            # Yoki aniqroq qilib BASE_DIR ga bog'lash kerak
            full_path = os.path.join(settings.BASE_DIR, base_image_path) # Misol
            if not os.path.exists(full_path) and settings.STATICFILES_DIRS:
                 # Yoki STATICFILES_DIRS dagi birinchi papkani qidirish
                full_path = os.path.join(settings.STATICFILES_DIRS[0], base_image_path.replace('static/', '', 1))

            if not os.path.exists(full_path):
                print(f"Error: Voucher template image not found at {full_path} (original: {base_image_path})")
                return None
        else:
            full_path = base_image_path
            if not os.path.exists(full_path):
                print(f"Error: Voucher template image not found at {full_path}")
                return None

        image = Image.open(full_path)
        draw = ImageDraw.Draw(image)

        # Shriftlarni topish. STATICFILES_DIRS da bo'lishi kerak.
        # Yoki shrift fayllarini loyiha ildizidagi 'static/fonts/' kabi joyga qo'ying
        # va settings.STATICFILES_DIRS ga shu papkani qo'shing.
        try:
            font_path_arial = os.path.join(settings.STATICFILES_DIRS[0], "fonts/arial.ttf") if settings.STATICFILES_DIRS else "arial.ttf"
            font_path_fullname = os.path.join(settings.STATICFILES_DIRS[0], "fonts/forFullname.ttf") if settings.STATICFILES_DIRS else "static/forFullname.ttf" # Eski yo'l
            
            if not os.path.exists(font_path_arial): font_path_arial = "arial.ttf" # Fallback
            if not os.path.exists(font_path_fullname): font_path_fullname = font_path_arial # Fallback

            font_date_num = ImageFont.truetype(font_path_arial, 36)
            font_fullname = ImageFont.truetype(font_path_fullname, 72)
        except IOError:
            print("Warning: Fonts not found, using default.")
            font_date_num = ImageFont.load_default()
            font_fullname = ImageFont.load_default()


        # Matnlarni yozish (koordinatalar va ranglar sizning shabloningizga mos bo'lishi kerak)
        # draw.text((10, 10), subjectname_text, fill="black", font=font_date_num) # Agar fan nomi kerak bo'lsa
        draw.text((335, 970), date_str, fill="#400025", font=font_date_num)
        draw.text((695, 970), str(num_code), fill="#400025", font=font_date_num)

        # Ism-sharifni markazlashtirish
        try: # textbbox Pillow ning yangi versiyalarida (masalan, 9.0.0+)
            text_bbox = draw.textbbox((0, 0), fullname, font=font_fullname)
            text_width = text_bbox[2] - text_bbox[0]
        except AttributeError: # textsize eski versiyalar uchun
             # textsize dan qaytgan (width, height)
            text_size_tuple = draw.textsize(fullname, font=font_fullname)
            text_width = text_size_tuple[0]

        draw.text(((1560 - text_width) / 2, 420), fullname, fill="#400025", font=font_fullname) # 1560 rasmning taxminiy eni

        # Rasmni BytesIO obyektiga saqlash
        image_bytes = BytesIO()
        image.save(image_bytes, format='JPEG')
        image_bytes.seek(0)
        return image_bytes

    except FileNotFoundError:
        print(f"Error: Base image not found at {base_image_path} or {full_path if 'full_path' in locals() else ''}")
        return None
    except Exception as e:
        print(f"Error generating photo: {e}")
        return None