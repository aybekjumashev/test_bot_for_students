# core/utils.py
import mammoth
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
import os
from django.contrib.staticfiles import finders
import zipfile
from lxml import etree
from django.utils.translation import gettext_lazy as _
from docx import Document as DocxDocument
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)

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

def get_photo(fullname, date_str, voucher_template_filename, num_code, score):
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
            font_fullname_obj = ImageFont.truetype(font_arial_path, 24)
        except IOError as e:
            print(f"Warning: Fonts not found ({e}), using default.")
            font_date_num = ImageFont.load_default()
            font_fullname_obj = ImageFont.load_default()

        # Matnlarni yozish (koordinatalar sizning shabloningizga mos bo'lishi kerak)
        # Bu koordinatalar eski loyihadagi get_photo dan olingan
        draw.text((250, 1500), date_str, fill="#000000", font=font_date_num)
        draw.text((325, 679), str(num_code[1]), fill="#000000", font=font_fullname_obj)
        draw.text((471, 713), str(num_code[0]), fill="#000000", font=font_fullname_obj)
        draw.text((528, 1155), str(score[0]), fill="#000000", font=font_date_num)
        draw.text((993, 1198), str(score[1])+'%', fill="#000000", font=font_date_num)

        name, surname, patronymic = fullname 

        # Boshlang'ich koordinatalar
        text_x = 250  # Chapdan qancha masofada yozilsin, o'zingiz moslashtiring
        text_y = 781  # Birinchi qatorning Y koordinatasi

        # Har bir qator uchun yozish
        line_spacing = 10  # Qatorlar oralig'i, kerak bo‘lsa sozlang

        for i, text_line in enumerate([surname, name, patronymic]):
            draw.text((text_x, text_y + i * (font_fullname_obj.size + line_spacing)),
                    text_line.upper(), 
                    fill="#000000",
                    font=font_fullname_obj)

        image_bytes = BytesIO()
        image.save(image_bytes, format='JPEG')
        image_bytes.seek(0)
        return image_bytes

    except Exception as e:
        print(f"Error in get_photo: {e}")
        # traceback.print_exc() # Batafsil xato uchun
        return None

def split_docx_into_questions(docx_file_bytes, answers_string, delimiter="###"):
    """
    Parses DOCX file bytes, splits it by a delimiter, and associates
    each part with a correct answer from the answers_string.
    Creates a minimal but valid DOCX for each part.
    """
    if not docx_file_bytes:
        return [], _("Fayl yuklanmagan.")
    if not answers_string:
        return [], _("Javoblar ketma-tetligi kiritilmagan.")
    
    print(answers_string)
    print(f"split_docx_into_questions: Fayl hajmi: {len(docx_file_bytes)} bayt.")

    # # python-docx bilan dastlabki tekshiruv (ixtiyoriy)
    # check_stream = BytesIO(docx_file_bytes)
    # try:
    #     from docx import Document as DocxDocumentForCheck
    #     DocxDocumentForCheck(check_stream)
    #     print("Fayl python-docx tomonidan dastlabki tekshiruvdan o'tdi.")
    # except Exception as e_check:
    #     print(f"python-docx tekshiruvida xato: {e_check}")
    #     # return [], _("DOCX fayl yaroqsiz (dastlabki tekshiruv).") # Agar bu xato bo'lsa, davom etmaslik mumkin
    # finally:
    #     check_stream.close()

    # Asosiy zip faylni ochish uchun yangi BytesIO
    main_zip_stream = BytesIO(docx_file_bytes)
    try:
        with zipfile.ZipFile(main_zip_stream, 'r') as docx_zip:
            if "word/document.xml" not in docx_zip.namelist():
                return [], _("DOCX fayl yaroqsiz (document.xml topilmadi).")

            xml_content = docx_zip.read("word/document.xml")
            original_root = etree.fromstring(xml_content) # Asl XML ildizi
            
            namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            body_elements_from_original = original_root.xpath("//w:body/*", namespaces=namespaces)
            
            parsed_sections_elements = [] # Har bir section uchun elementlar ro'yxatini saqlaydi
            current_section_elements = []
            found_first_delimiter_or_content = False # Delimiter yoki kontent topilganini belgilash

            # Faylda delimiter borligini tekshirish
            has_delimiter_in_file = any(
                delimiter in "".join(el.xpath(".//w:t/text()", namespaces=namespaces))
                for el in body_elements_from_original if el.tag.endswith("p")
            )

            if not has_delimiter_in_file and body_elements_from_original:
                # Agar delimiter yo'q bo'lsa, butun body ni bitta section deb hisoblash
                parsed_sections_elements.append(list(body_elements_from_original))
                found_first_delimiter_or_content = True
            else:
                for element in body_elements_from_original:
                    is_paragraph = element.tag.endswith("p")
                    text_in_element = "".join(element.xpath(".//w:t/text()", namespaces=namespaces)) if is_paragraph else ""
                    
                    # Agar elementning o'zi delimiter bilan boshlansa
                    # Yoki element ichidagi biror w:r/w:t delimiter bilan boshlansa
                    # Bu qismni soddalashtirish kerak bo'lishi mumkin
                    # Hozircha, faqat to'liq paragraf matni delimiter bilan boshlanishini tekshiramiz
                    if text_in_element.strip().startswith(delimiter):
                        if current_section_elements: # Oldingi sectionni saqlash
                            parsed_sections_elements.append(deepcopy(current_section_elements))
                        current_section_elements = [] # Yangisi uchun tozalash
                        found_first_delimiter_or_content = True
                        # Delimiterli paragrafdan keyingi matnni olish (agar bo'lsa)
                        # Hozircha, delimiterli paragrafni o'zini qo'shmaymiz
                    elif found_first_delimiter_or_content: # Delimiter topilgandan keyingi elementlar
                        current_section_elements.append(element)
                    elif not found_first_delimiter_or_content and element.xpath("string()").strip(): # Delimiterdan oldingi birinchi kontentli element
                        # Bu logikani soddalashtirish mumkin: faqat delimiterdan keyingi qismlarni olish
                        # Hozircha, agar delimiter topilmagan bo'lsa, lekin kontent bo'lsa, uni current_section ga qo'shamiz
                        # Bu agar fayl ### bilan boshlanmasa, birinchi qismni ham olishga harakat qiladi
                        # Lekin bu chalkashlik tug'dirishi mumkin. Eng yaxshisi, ### dan boshlash.
                        # Agar fayl ### bilan boshlanmasa, birinchi ### gacha bo'lgan qismni tashlab yuboramiz.
                        pass # ### dan oldingi kontentni o'tkazib yuborish


            if current_section_elements: # Oxirgi sectionni saqlash
                parsed_sections_elements.append(deepcopy(current_section_elements))
            
            num_parsed_sections = len(parsed_sections_elements)
            num_answers = len(answers_string)

            if num_parsed_sections == 0:
                if num_answers > 0:
                    return [], _("DOCX faylidan savollar ajratib olinmadi (ehtimol delimiter \"{}\" topilmadi yoki fayl formati noto'g'ri), lekin javoblar mavjud.").format(delimiter)
                else: # Hech qanday savol va hech qanday javob
                    return [], _("DOCX fayli bo'sh yoki savol topilmadi va javoblar ham kiritilmagan.")


            if num_parsed_sections != num_answers:
                return [], _("Ajratilgan savollar soni ({}) kiritilgan javoblar soniga ({}) mos kelmadi.").format(num_parsed_sections, num_answers)

            output_questions_data = []
            for i, section_elements_list in enumerate(parsed_sections_elements):
                if not section_elements_list: continue

                # Har bir yangi DOCX uchun asosiy XML tuzilmasini yaratish
                new_doc_root_for_section = etree.Element(original_root.tag, nsmap=original_root.nsmap)
                
                # Asl XMLdan bodydan boshqa barcha kerakli qismlarni nusxalash
                # Bu qism DOCX stillari va formatlashini saqlab qolish uchun muhim
                # Masalan, settings, styles, fontTable, theme, va hokazo.
                # Buni to'g'ri qilish murakkab, chunki bog'liqliklar bo'lishi mumkin.
                # Hozircha minimal yondashuv: faqat body yaratamiz.
                # Yaxshiroq yondashuv - python-docx bilan yangi hujjat yaratib, elementlarni ko'chirish.
                
                body_for_section = etree.SubElement(new_doc_root_for_section, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body")
                for el_instance in section_elements_list:
                    body_for_section.append(deepcopy(el_instance)) # Elementlarni to'liq nusxalash
                
                # Word fayli to'g'ri ochilishi uchun oxirgi sectPr ni qo'shish
                original_sect_pr = original_root.find("w:body/w:sectPr", namespaces=namespaces)
                if original_sect_pr is not None:
                    body_for_section.append(deepcopy(original_sect_pr))
                else: # Minimal oxirgi paragraf
                    final_p = etree.SubElement(body_for_section, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p")
                    etree.SubElement(final_p, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r")

                # Yangi DOCX faylini BytesIO ga yozish
                single_question_docx_stream = BytesIO()
                with zipfile.ZipFile(single_question_docx_stream, 'w', zipfile.ZIP_DEFLATED) as new_single_docx_zip:
                    # Yangi document.xml ni yozish
                    new_single_docx_zip.writestr(
                        "word/document.xml",
                        etree.tostring(new_doc_root_for_section, xml_declaration=True, encoding='UTF-8', standalone="yes")
                    )
                    
                    # Asl DOCXdagi BA'ZI MUHIM fayllarni nusxalash
                    # Bu ro'yxatni ehtiyotkorlik bilan tanlash kerak, chunki ba'zilari document.xml ga bog'liq.
                    # Masalan, _rels/document.xml.rels ni nusxalashda ehtiyot bo'lish kerak.
                    # Hozircha, faqat rasmlar (media) va stillarni (styles.xml) nusxalashga harakat qilamiz.
                    # Va content types, asosiy rels.
                    files_to_copy_from_original = {
                        "[Content_Types].xml",
                        "_rels/.rels",
                        # "word/_rels/document.xml.rels", # Bu yangi document.xml ga mos kelmasligi mumkin
                        "word/styles.xml", # Yoki stylesWithEffects.xml
                        "word/theme/theme1.xml", # Agar mavjud bo'lsa
                        "word/fontTable.xml", # Agar mavjud bo'lsa
                        "word/settings.xml", # Agar mavjud bo'lsa
                    }
                    # Papkalarni ham qo'shish (rekursiv nusxalash kerak bo'ladi)
                    # Hozircha faqat fayllar
                    
                    for item_info in docx_zip.infolist():
                        if item_info.is_dir(): # Papkalarni o'tkazib yuborish
                            continue

                        # Media papkasidagi barcha fayllarni nusxalash
                        if item_info.filename.startswith("word/media/"):
                            try:
                                content = docx_zip.read(item_info.filename)
                                new_single_docx_zip.writestr(item_info.filename, content)
                            except Exception as e_copy_media:
                                logger.warning(f"Media faylni nusxalashda xato '{item_info.filename}': {e_copy_media}")
                        elif item_info.filename in files_to_copy_from_original:
                            try:
                                content = docx_zip.read(item_info.filename)
                                new_single_docx_zip.writestr(item_info.filename, content)
                            except Exception as e_copy_essential:
                                logger.warning(f"Muhim faylni nusxalashda xato '{item_info.filename}': {e_copy_essential}")
                
                single_question_docx_stream.seek(0)
                output_questions_data.append((single_question_docx_stream.getvalue(), answers_string[i].upper()))
            
            return output_questions_data, None
    
    except zipfile.BadZipFile:
        logger.error("BadZipFile error in split_docx_into_questions (main zip)", exc_info=True)
        return [], _("DOCX fayl yaroqsiz zip arxiv (asosiy fayl).")
    except etree.XMLSyntaxError as e:
        logger.error("XMLSyntaxError in split_docx_into_questions", exc_info=True)
        return [], _("DOCX fayl yaroqsiz XML tuzilishiga ega: {}").format(str(e))
    except Exception as e:
        logger.error("Unexpected error in split_docx_into_questions", exc_info=True)
        return [], _("DOCX faylini qayta ishlashda kutilmagan xato: {}").format(str(e))
    finally:
        if 'main_zip_stream' in locals() and main_zip_stream:
            main_zip_stream.close()