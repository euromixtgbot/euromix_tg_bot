import base64
from datetime import datetime
from io import BytesIO

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from config import JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN
from keyboards import make_keyboard, remove_keyboard, STEPS
from services import (
    create_issue_in_jira,
    attach_file_to_jira,
    add_comment_to_jira,
    get_issue_status,
)

user_data = {}

# ——————————————————————————————————————————
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data[uid] = {"step": 0}
    text, markup = make_keyboard(0)
    await update.message.reply_text(text, reply_markup=markup)

# ——————————————————————————————————————————
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return

    text = update.message.text or ""
    step = user_data[uid]["step"]
    key = STEPS[step]

    # ← Назад
    if text == "Назад":
        user_data[uid]["step"] = max(0, step - 1)
        txt, mkp = make_keyboard(
            user_data[uid]["step"],
            description=user_data[uid].get("description", "")
        )
        await update.message.reply_text(txt, reply_markup=mkp)
        return

    # Збір даних
    if key in ("division", "department", "service", "full_name"):
        user_data[uid][key] = text

    # Опис проблеми
    elif key == "description":
        user_data[uid].setdefault("description", "")
        user_data[uid]["description"] += text + "\n"

    # Confirm-крок
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

    # Перехід далі
    user_data[uid]["step"] = min(len(STEPS) - 1, step + 1)
    txt, mkp = make_keyboard(
        user_data[uid]["step"],
        description=user_data[uid].get("description", "")
    )
    await update.message.reply_text(txt, reply_markup=mkp)

# ——————————————————————————————————————————
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return

    issue_key = user_data[uid].get("task_id")
    if not issue_key:
        await update.message.reply_text(
            "❗ Спочатку натисніть 'Створити задачу', а потім надсилайте файли."
        )
        return

    doc = update.message.document
    if doc.file_size > 9.9 * 1024 * 1024:
        await update.message.reply_text("❗ Файл занадто великий (макс 9.9 MB).")
        return

    try:
        f = await context.bot.get_file(doc.file_id)
        content = await f.download_as_bytearray()
        resp = await attach_file_to_jira(issue_key, doc.file_name, content)
        if resp.status_code in (200, 201):
            await update.message.reply_text(f"✅ Файл '{doc.file_name}' прикріплено.")
        else:
            await update.message.reply_text(f"⛔ Не вдалося прикріпити файл. Код: {resp.status_code}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка при надсиланні файлу: {e}")

# ——————————————————————————————————————————
async def send_to_jira(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Створює issue в Jira без Make.com."""
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
        issue_key = result["key"]
        user_data[uid]["task_id"] = issue_key
        await update.message.reply_text(
            f"✅ Задача створена: {issue_key}",
            reply_markup=ReplyKeyboardRemove()
        )
        mkp = ReplyKeyboardMarkup(
            [[KeyboardButton("Перевірити статус задачі")]],
            resize_keyboard=True
        )
        await update.message.reply_text("Тепер ви можете надсилати файли або коментарі.", reply_markup=mkp)
    else:
        await update.message.reply_text(f"❌ Помилка створення задачі: {result.get('error')}")

# ——————————————————————————————————————————
async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    issue_key = user_data.get(uid, {}).get("task_id")
    if not issue_key:
        await update.message.reply_text("Немає активної задачі.")
        return
    try:
        status = await get_issue_status(issue_key)
        await update.message.reply_text(f"Статус задачі {issue_key}: {status}")
        if status.lower() == "готово":
            mkp = ReplyKeyboardMarkup(
                [[KeyboardButton("Старт. Створити нову заявку")]],
                resize_keyboard=True
            )
            await update.message.reply_text("✅ Задача завершена.", reply_markup=mkp)
            user_data.pop(uid, None)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка при отриманні статусу: {e}")

# ——————————————————————————————————————————
async def add_comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    issue_key = user_data.get(uid, {}).get("task_id")
    if not issue_key:
        await update.message.reply_text("Немає активної задачі.")
        return

    comment = update.message.text.strip()
    try:
        resp = await add_comment_to_jira(issue_key, comment)
        if resp.status_code == 201:
            await update.message.reply_text("✅ Коментар додано.")
        elif resp.status_code == 404:
            await update.message.reply_text("⛔ Задачу не знайдено або бракує прав.")
        else:
            await update.message.reply_text(f"⛔ Помилка додавання коментаря: {resp.status_code}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка при додаванні коментаря: {e}")

# ——————————————————————————————————————————
async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        await handle_document(update, context)
        return

    text = update.message.text or ""
    if text == "/start":
        await start(update, context)
    elif text == "Перевірити статус задачі":
        await check_status(update, context)
    elif user_data.get(update.effective_user.id, {}).get("task_id"):
        await add_comment_handler(update, context)
    else:
        await handle_message(update, context)
