# core/utils.py
import mammoth
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
import os
from django.contrib.staticfiles import finders

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

def get_photo(fullname, date_str, voucher_template_filename, num_code, subjectname_text=''):
    """
    Generates a voucher image.
    voucher_template_filename - 'vouchers/' papkasidagi shablon fayl nomi (masalan, 'VoucherUmumiy1.jpg')
    """
    try:
        # Statik fayllar qidiruvchisi orqali shablon rasmini topish
        # Bu 'vouchers/VoucherUmumiy1.jpg' kabi yo'lni qidiradi
        base_image_full_path = finders.find(os.path.join('vouchers', voucher_template_filename))
        if not base_image_full_path or not os.path.exists(base_image_full_path):
            print(f"Error: Voucher template image not found: vouchers/{voucher_template_filename}")
            return None
        
        image = Image.open(base_image_full_path)
        draw = ImageDraw.Draw(image)

        # Shriftlarni topish
        font_arial_path = finders.find('fonts/arial.ttf')
        font_fullname_path = finders.find('fonts/forFullname.ttf') # Sizning fayl nomingiz

        if not font_arial_path: font_arial_path = "arial.ttf" # Fallback
        if not font_fullname_path: font_fullname_path = font_arial_path # Fallback

        try:
            font_date_num = ImageFont.truetype(font_arial_path, 36)
            font_fullname_obj = ImageFont.truetype(font_fullname_path, 72)
        except IOError as e:
            print(f"Warning: Fonts not found ({e}), using default.")
            font_date_num = ImageFont.load_default()
            font_fullname_obj = ImageFont.load_default()

        # Matnlarni yozish (koordinatalar sizning shabloningizga mos bo'lishi kerak)
        # Bu koordinatalar eski loyihadagi get_photo dan olingan
        draw.text((335, 970), date_str, fill="#400025", font=font_date_num)
        draw.text((695, 970), str(num_code), fill="#400025", font=font_date_num)

        # Ism-sharifni markazlashtirish
        # Pillow 9.0.0+ da textbbox, undan oldin textsize
        try:
            text_bbox = draw.textbbox((0, 0), fullname, font=font_fullname_obj)
            text_width = text_bbox[2] - text_bbox[0]
            # text_height = text_bbox[3] - text_bbox[1] # Agar balandlik ham kerak bo'lsa
        except AttributeError: # Eski Pillow uchun fallback
            text_width, _ = draw.textsize(fullname, font=font_fullname_obj)

        # Shablon rasmining eni (taxminan, o'zingiznikiga moslang)
        image_width = image.width # 1560
        # Yoziladigan joyning markazi (taxminan, o'zingiznikiga moslang)
        center_x_for_name = image_width / 2 # 780
        text_x = center_x_for_name - (text_width / 2)
        text_y = 420 # Eski kodingizdagi Y koordinata

        draw.text((text_x, text_y), fullname, fill="#400025", font=font_fullname_obj)

        if subjectname_text: # Agar fan nomi ham yozilishi kerak bo'lsa (eski kodda bor edi)
             # draw.text((10, 10), subjectname_text, fill="black", font=font_date_num)
             pass # Hozircha aralash test uchun bu shart emas

        image_bytes = BytesIO()
        image.save(image_bytes, format='JPEG')
        image_bytes.seek(0)
        return image_bytes

    except Exception as e:
        print(f"Error in get_photo: {e}")
        # traceback.print_exc() # Batafsil xato uchun
        return None