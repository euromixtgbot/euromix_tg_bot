# handlers.py
import base64
from datetime import datetime
from io import BytesIO
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from config import JIRA_PROJECT_KEY, JIRA_ISSUE_TYPE, JIRA_REPORTER_ACCOUNT_ID
from keyboards import make_keyboard, remove_keyboard, STEPS
from services import create_issue_in_jira, attach_file_to_jira, add_comment_to_jira, get_issue_status
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Бот запущено")

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data[uid] = {"step": 0}
    text, markup = make_keyboard(0)
    await update.message.reply_text(text, reply_markup=markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return
    text = update.message.text or ""
    step = user_data[uid]["step"]
    key = STEPS[step]
    if text == "Назад":
        user_data[uid]["step"] = max(0, step - 1)
        txt, mkp = make_keyboard(user_data[uid]["step"], description=user_data[uid].get("description", ""))
        await update.message.reply_text(txt, reply_markup=mkp)
        return
    if key in ("division", "department", "service", "full_name"):
        user_data[uid][key] = text
    elif key == "description":
        user_data[uid].setdefault("description", "")
        user_data[uid]["description"] += text + "\n"
    elif key == "confirm":
        if text == "Створити задачу":
            await send_to_jira(update, context)
            return
        else:
            user_data[uid].setdefault("description", "")
            user_data[uid]["description"] += text + "\n"
            txt, mkp = make_keyboard(step, description=user_data[uid]["description"]) 
            await update.message.reply_text(txt, reply_markup=mkp)
            return
    user_data[uid]["step"] = min(len(STEPS) - 1, step + 1)
    txt, mkp = make_keyboard(user_data[uid]["step"], description=user_data[uid].get("description", ""))
    await update.message.reply_text(txt, reply_markup=mkp)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return
    issue = user_data[uid].get("task_id")
    if not issue:
        await update.message.reply_text("❗ Спочатку натисніть 'Створити задачу', а потім надсилайте файли.")
        return
    doc = update.message.document
    if doc.file_size > 9.9 * 1024 * 1024:
        await update.message.reply_text("❗ Файл занадто великий (макс 9.9MB)")
        return
    f = await context.bot.get_file(doc.file_id)
    content = await f.download_as_bytearray()
    resp = await attach_file_to_jira(issue, doc.file_name, content)
    if resp.status_code in (200, 201):
        await update.message.reply_text(f"✅ Файл '{doc.file_name}' прикріплено.")
    else:
        await update.message.reply_text(f"⛔ Помилка прикріплення: {resp.status_code}")

async def send_to_jira(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    data = {
        "division": user_data[uid].get("division"),
        "department": user_data[uid].get("department"),
        "service": user_data[uid].get("service"),
        "full_name": user_data[uid].get("full_name"),
        "description": user_data[uid].get("description", ""),
    }
    result = await create_issue_in_jira(data)
    if "key" in result:
        issue = result["key"]
        user_data[uid]["task_id"] = issue
        await update.message.reply_text(f"✅ Задача створена: {issue}", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text("Тепер можете надсилати файли або коментарі.")
    else:
        await update.message.reply_text(f"❌ Помилка створення задачі: {result.get('error')}")

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        await handle_document(update, context)
    else:
        text = update.message.text or ""
        if text == "/start":
            await start(update, context)
        elif text == "Перевірити статус задачі":
            await check_status(update, context)
        elif user_data.get(update.effective_user.id, {}).get("task_id"):
            await add_comment_handler(update, context)
        else:
            await handle_message(update, context)