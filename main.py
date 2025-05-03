#!/usr/bin/env python3
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from dotenv import load_dotenv
from config import TOKEN
import handlers

# Завантаження змінних оточення
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update, context):
    logger.error("Exception while handling an update:", exc_info=context.error)
    if update and getattr(update, 'message', None):
        try:
            await update.message.reply_text("\u26a0\ufe0f Сталася помилка. Спробуйте знову.")
        except Exception:
            pass

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # 0) Стартова команда
    app.add_handler(
        CommandHandler("start", handlers.start)
    )

    # 1) Обробка кліку на інлайн-кнопки comment_task_<ID>
    app.add_handler(
        CallbackQueryHandler(
            handlers.handle_comment_callback,
            pattern=r"^comment_task_"
        )
    )

    # 2) Хендлер лише для медіа
    app.add_handler(
        MessageHandler(
            filters.Document.ALL |
            filters.PHOTO |
            filters.VIDEO |
            filters.AUDIO,
            handlers.universal_handler
        )
    )

    # 3) Хендлер лише для тексту без команд
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handlers.universal_handler
        )
    )

    # 4) Обробник помилок
    app.add_error_handler(error_handler)

    # Запускаємо polling
    app.run_polling()

if __name__ == "__main__":
    main()
