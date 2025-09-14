from PIL import Image, ImageEnhance
import pytesseract
import re
import json
import logging

# Укажи путь к Tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OCRProcessor:
    def __init__(self):
        self.initialized = True

    def process_image(self, image: Image.Image) -> str:
        """OCR + извлечение данных (полностью бесплатно, без API)"""
        try:
            if image.mode != "RGB":
                image = image.convert("RGB")

            image = self.enhance_image(image)

            # Распознавание текста
            extracted_text = pytesseract.image_to_string(image, lang="rus+eng")
            logger.info(f"Извлеченный текст: {extracted_text[:100]}...")

            # Извлечение данных с помощью регулярных выражений
            structured_data = self.fallback_extraction(extracted_text)

            return json.dumps(structured_data, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Ошибка OCR: {e}")
            return f'{{"error": "Ошибка обработки: {str(e)}"}}'

    def enhance_image(self, image):
        """Улучшение изображения"""
        image = ImageEnhance.Contrast(image).enhance(1.5)
        image = ImageEnhance.Sharpness(image).enhance(1.5)
        return image

    def fallback_extraction(self, text):
        """Извлечение данных без LLM (бесплатно)"""

        # Суммы с валютой
        amounts = re.findall(r"\d+[.,]?\d*\s?(?:₸|T|KZT)", text)

        # Даты
        dates = re.findall(r"\d{2}[./]\d{2}[./]\d{2,4}", text)

        # Карты (xxxx xxxx xxxx xxxx)
        cards = re.findall(r"\b(?:\d{4}[\s-]?){4}\b", text)

        # Квитанции (12–20 цифр подряд)
        receipts = re.findall(r"\b\d{12,20}\b", text)

        # Дополнительные данные по ключевым словам
        details = {}
        for line in text.splitlines():
            if "Отправитель" in line:
                details["sender"] = line.replace("Отправитель", "").strip(": ").strip()
            if "клиенту" in line or "Получатель" in line:
                details["receiver"] = line.replace("клиенту", "").replace("Получатель", "").strip(": ").strip()
            if "Тип перевода" in line:
                details["transfer_type"] = line.replace("Тип перевода", "").strip(": ").strip()

        return {
            "text": text[:500] + "..." if len(text) > 500 else text,
            "amounts": amounts,
            "dates": dates,
            "card_numbers": cards,
            "receipts": receipts,
            **details,
            "note": "Обработка выполнена оффлайн, без LLM."
        }


ocr_processor = OCRProcessor()