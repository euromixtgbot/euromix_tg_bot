import base64
import requests
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from config import MAKE_WEBHOOK_CREATE_TASK, JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN
from keyboards import make_keyboard, remove_keyboard, STEPS
from services import create_task_in_make, attach_file_to_jira, add_comment_to_jira, get_issue_status

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
    text = update.message.text
    step = user_data[uid]["step"]

    if text == "Назад":
        user_data[uid]["step"] = max(0, step - 1)
        text, markup = make_keyboard(user_data[uid]["step"], description=user_data[uid].get("description",""))
        await update.message.reply_text(text, reply_markup=markup)
        return

    key = STEPS[step]
    if key in ("division", "department", "service", "full_name"):
        user_data[uid][key] = text
    elif key == "description":
        user_data[uid].setdefault("description", "")
        user_data[uid]["description"] += text + "\n"
    elif key == "confirm" and text == "Створити задачу":
        await send_to_make(update, context)
        return

    user_data[uid]["step"] = min(len(STEPS) - 1, step + 1)
    text, markup = make_keyboard(user_data[uid]["step"], description=user_data[uid].get("description",""))
    await update.message.reply_text(text, reply_markup=markup)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return
    task_id = user_data.get(uid, {}).get("task_id")
    if not task_id:
        await update.message.reply_text("Немає активної задачі. /start")
        return

    doc = update.message.document
    if doc.file_size > 9.9 * 1024 * 1024:
        await update.message.reply_text("❗ max 9.9MB")
        return

    file = await context.bot.get_file(doc.file_id)
    content = await file.download_as_bytearray()
    resp = await attach_file_to_jira(task_id, doc.file_name, content)
    if resp.status_code in (200,201):
        await update.message.reply_text(f"✅ '{doc.file_name}' прикріплено")
    else:
        await update.message.reply_text(f"❌ Error {resp.status_code}")

async def send_to_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return
    payload = {
        "username": update.effective_user.username,
        "telegram_id": uid,
        **{k: user_data[uid].get(k) for k in ("division","department","service","full_name","description")},
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    result = await create_task_in_make(payload)
    tid = result.get("task_id")
    if not tid:
        await update.message.reply_text("❌ Не отримали ID")
        return
    user_data[uid]["task_id"] = tid
    await update.message.reply_text(f"✅ Задача: {tid}", reply_markup=remove_keyboard())
    await update.message.reply_text("Перевірити статус задачі")

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return
    tid = user_data.get(uid, {}).get("task_id")
    if not tid:
        await update.message.reply_text("Немає ID")
        return
    status = await get_issue_status(tid)
    await update.message.reply_text(f"Статус {tid}: {status}")

async def add_comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return
    tid = user_data.get(uid, {}).get("task_id")
    if not tid:
        await update.message.reply_text("Немає ID")
        return
    comment = update.message.text.strip()
    resp = await add_comment_to_jira(tid, comment)
    if resp.status_code == 201:
        await update.message.reply_text("✅ Коментар додано")
    else:
        await update.message.reply_text(f"❌ Error {resp.status_code}")

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Перевірити статус задачі":
        await check_status(update, context)
    elif text == "/start":
        await start(update, context)
    elif text and user_data.get(update.effective_user.id,{}).get("task_id"):
        await add_comment_handler(update, context)
    else:
        await handle_message(update, context)