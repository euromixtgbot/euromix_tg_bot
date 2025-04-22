import base64
import requests
from datetime import datetime
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import ContextTypes

from config import (
    MAKE_WEBHOOK_CREATE_TASK,
    JIRA_DOMAIN,
    JIRA_EMAIL,
    JIRA_API_TOKEN,
)
from keyboards import make_keyboard, remove_keyboard, STEPS
from services import (
    create_task_in_make,
    attach_file_to_jira,
    add_comment_to_jira,
    get_issue_status,
)

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
        text, markup = make_keyboard(
            user_data[uid]["step"],
            description=user_data[uid].get("description", "")
        )
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
    text, markup = make_keyboard(
        user_data[uid]["step"],
        description=user_data[uid].get("description", "")
    )
    await update.message.reply_text(text, reply_markup=markup)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # Якщо користувач ще не стартував діалог
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return

    # Якщо задача ще не створена
    task_id = user_data[uid].get("task_id")
    if not task_id:
        await update.message.reply_text(
            "❗ Спочатку натисніть 'Створити задачу', а потім надсилайте файли."
        )
        return

    document = update.message.document

    # Перевірка ліміту розміру
    if document.file_size > 9.9 * 1024 * 1024:
        await update.message.reply_text("❗ Ваш файл занадто великий (макс 9.9 MB).")
        return

    # Завантажуємо вміст та надсилаємо в Jira
    try:
        file = await context.bot.get_file(document.file_id)
        content = await file.download_as_bytearray()
        resp = await attach_file_to_jira(task_id, document.file_name, content)

        if resp.status_code in (200, 201):
            await update.message.reply_text(f"✅ Файл '{document.file_name}' прикріплено.")
        else:
            await update.message.reply_text(
                f"⛔ Не вдалося прикріпити файл. Статус: {resp.status_code}"
            )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка при завантаженні файлу: {e}")

async def send_to_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return

    payload = {
        "username": update.effective_user.username,
        "telegram_id": uid,
        "division": user_data[uid].get("division"),
        "department": user_data[uid].get("department"),
        "service": user_data[uid].get("service"),
        "full_name": user_data[uid].get("full_name"),
        "description": user_data[uid].get("description"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        result = await create_task_in_make(payload)
        task_id = result.get("task_id")
        if not task_id:
            raise ValueError("Не повернувся task_id")
        user_data[uid]["task_id"] = task_id

        await update.message.reply_text(
            f"✅ Задача створена: {task_id}", reply_markup=remove_keyboard()
        )
        # Додаємо кнопку для перевірки статусу
        markup = ReplyKeyboardMarkup(
            [[KeyboardButton("Перевірити статус задачі")]],
            resize_keyboard=True
        )
        await update.message.reply_text("Перевірити статус задачі", reply_markup=markup)

    except Exception as e:
        await update.message.reply_text(f"❌ Помилка при створенні задачі: {e}")

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return

    task_id = user_data[uid].get("task_id")
    if not task_id:
        await update.message.reply_text("Немає активної задачі.")
        return

    try:
        status = await get_issue_status(task_id)
        await update.message.reply_text(f"Статус задачі {task_id}: {status}")
        if status.lower() == "готово":
            markup = ReplyKeyboardMarkup(
                [[KeyboardButton("Старт. Створити нову заявку")]],
                resize_keyboard=True
            )
            await update.message.reply_text("✅ Задача завершена.", reply_markup=markup)
            user_data.pop(uid, None)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Не вдалося отримати статус: {e}")

async def add_comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return

    task_id = user_data[uid].get("task_id")
    if not task_id:
        await update.message.reply_text("Немає активної задачі.")
        return

    comment = update.message.text.strip()
    try:
        resp = await add_comment_to_jira(task_id, comment)
        if resp.status_code == 201:
            await update.message.reply_text("✅ Коментар додано.")
        else:
            await update.message.reply_text(
                f"⛔ Помилка додавання коментаря: {resp.status_code}"
            )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Сталася помилка: {e}")

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Спочатку обробляємо документи
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
