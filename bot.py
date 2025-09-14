import asyncio
import io
from PIL import Image
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import config
from ocr_core import ocr_processor
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = """
🏦 *BCC HUB OCR 2.0 Бот*

Я обрабатываю банковские документы и извлекаю данные в структурированном виде.

*Как использовать:*
1. Сделайте фото чека, выписки или договора
2. Отправьте фото мне в чат
3. Получите результат в формате JSON

*Поддерживаемые форматы:* JPEG, PNG
*Что умею извлекать:* названия банков, номера счетов, суммы, даты, получателей

Для начала просто отправьте мне фото документа!
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фотографий"""
    try:
        user = update.message.from_user
        logger.info(f"Получено фото от пользователя {user.first_name} (ID: {user.id})")

        # Показываем статус "печатает"
        await update.message.reply_chat_action(
            action=telegram.constants.ChatAction.TYPING
        )

        # Скачиваем фото (берем самое высокое качество)
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        # Конвертируем в изображение
        image = Image.open(io.BytesIO(photo_bytes))

        # Конвертируем в RGB если нужно
        if image.mode != 'RGB':
            image = image.convert('RGB')

        logger.info(f"Изображение получено: {image.size}, режим: {image.mode}")

        # Отправляем статус обработки
        processing_msg = await update.message.reply_text(
            "🔄 Обрабатываю изображение... Это может занять несколько секунд."
        )

        # Обрабатываем изображение
        result = ocr_processor.process_image(image)

        # Удаляем сообщение о обработке
        await context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=processing_msg.message_id
        )

        # Форматируем ответ
        if result.startswith('{') and '}' in result:
            response_text = f"✅ *Данные извлечены!*\n\n```json\n{result}\n```"
            parse_mode = 'Markdown'
        else:
            response_text = f"📝 *Результат обработки:*\n\n{result}"
            parse_mode = None

        # Отправляем результат
        await update.message.reply_text(
            response_text,
            parse_mode=parse_mode,
            reply_to_message_id=update.message.message_id
        )

        logger.info(f"Успешно обработано для пользователя {user.first_name}")

    except Exception as e:
        logger.error(f"Ошибка в handle_photo: {e}")
        error_text = "❌ Произошла ошибка при обработке изображения. Попробуйте еще раз или отправьте другое фото."
        await update.message.reply_text(error_text)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик документов"""
    try:
        document = update.message.document
        mime_type = document.mime_type

        if mime_type and mime_type.startswith('image/'):
            await update.message.reply_chat_action(
                action=telegram.constants.ChatAction.TYPING
            )

            # Скачиваем документ
            file = await document.get_file()
            document_bytes = await file.download_as_bytearray()

            # Конвертируем в изображение
            image = Image.open(io.BytesIO(document_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Обрабатываем
            result = ocr_processor.process_image(image)

            await update.message.reply_text(
                f"📄 *Результат обработки документа:*\n\n```json\n{result}\n```",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Пожалуйста, отправьте изображение (JPEG, PNG)."
            )

    except Exception as e:
        logger.error(f"Ошибка в handle_document: {e}")
        await update.message.reply_text("❌ Ошибка при обработке документа.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)

    if update and update.message:
        await update.message.reply_text(
            "⚠️ Произошла непредвиденная ошибка. Попробуйте еще раз."
        )

def main():
    """Основная функция запуска бота"""
    try:
        # Создаем приложение
        application = Application.builder().token(config.BOT_TOKEN).build()

        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
        application.add_error_handler(error_handler)

        # Запускаем бота
        logger.info("Бот запускается...")
        print("✅ Бот успешно запущен!")
        print("📸 Отправьте боту фото документа для тестирования")
        print("⏹️  Для остановки нажмите Ctrl+C")

        application.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        print(f"❌ Ошибка запуска: {e}")

if __name__ == "__main__":
    main()