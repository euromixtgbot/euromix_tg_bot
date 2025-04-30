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
            await update.message.reply_text("⚠️ Сталася помилка. Спробуйте знову.")
        except Exception:
            pass

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # старт
    app.add_handler(CommandHandler("start", handlers.start))

    # 1) callback на inline-кнопки «comment_task_...»
    app.add_handler(
        CallbackQueryHandler(
            handlers.handle_comment_callback,
            pattern=r"^comment_task_"
        )
    )

    # 2) текст в режимі коментаря
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handlers.comment_text_handler
        ),
        group=0
    )

    # 3) універсальні хендлери після comment_text_handler
    app.add_handler(
        MessageHandler(
            filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO,
            handlers.universal_handler
        ),
        group=1
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handlers.universal_handler
        ),
        group=1
    )

    # помилки
    app.add_error_handler(error_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
