#!/usr/bin/env python3
import logging
import os
from datetime import datetime

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from dotenv import load_dotenv

# Завантаження змінних оточення перед імпортом конфігурації
load_dotenv()

from config import TOKEN
from handlers import (
    start,
    handle_comment_callback,
    universal_handler,
    handle_contact
)

# Створити каталог logs/ якщо ще не існує
os.makedirs("logs", exist_ok=True)

# Конфігурація логування у файл і консоль
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def error_handler(update, context):
    logger.error("Exception while handling an update:", exc_info=context.error)
    if update and getattr(update, 'message', None):
        try:
            await update.message.reply_text("⚠️ Сталася помилка. Спробуйте знову.")
        except Exception:
            pass


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # 0) Стартова команда
    app.add_handler(CommandHandler("start", start))

    # 1) Обробка кліку на інлайн-кнопки comment_task_<ID>
    app.add_handler(CallbackQueryHandler(handle_comment_callback, pattern=r"^comment_task_"))

    # 2) Хендлер лише для медіа
    app.add_handler(MessageHandler(
        filters.Document.ALL |
        filters.PHOTO |
        filters.VIDEO |
        filters.AUDIO,
        universal_handler
    ))

    # 3) Хендлер лише для тексту без команд
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))

    # 4) Контакт (номер телефону)
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))

    # 5) Обробник помилок
    app.add_error_handler(error_handler)

    logger.info("⚙️ BOT STARTED AT: %s", datetime.now())
    app.run_polling()


if __name__ == "__main__":
    main()
