#!/usr/bin/env python3
# bot.py — Telegram ↔ Jira support bot, конфігурація через credentials.env

import os
import base64
import asyncio
from datetime import datetime
from io import BytesIO

import requests
from dotenv import load_dotenv
from telegram import (
    Bot,
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Завантажуємо змінні з файлу credentials.env
load_dotenv("credentials.env")

# --- Конфігурація через середовище ---
TOKEN                   = os.getenv("TOKEN")
WEBHOOK_URL             = os.getenv("WEBHOOK_URL")
MAKE_WEBHOOK_CREATE_TASK= os.getenv("MAKE_WEBHOOK_CREATE_TASK")
JIRA_DOMAIN             = os.getenv("JIRA_DOMAIN")
JIRA_EMAIL              = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN          = os.getenv("JIRA_API_TOKEN")
SSL_CERT_PATH           = os.getenv("SSL_CERT_PATH")
SSL_KEY_PATH            = os.getenv("SSL_KEY_PATH")

# Ініціалізація Telegram Bot та Application
bot = Bot(token=TOKEN)
application = ApplicationBuilder().token(TOKEN).build()

# Тимчасове зберігання стану користувачів
user_data = {}
steps = ["division", "department", "service", "full_name", "description", "confirm"]

# ------------------ Старт діалогу ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ініціює новий діалог створення Jira-задачі."""
    user_id = update.effective_user.id
    user_data[user_id] = {"step": 0}
    await ask_next_question(update, context)

# ------------------ Формування та відправка питання ------------------
async def ask_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Відправляє користувачу питання по кроках із клавіатурою відповідей."""
    user_id = update.effective_user.id
    step = user_data[user_id]["step"]
    text = ""
    options = []

    if steps[step] == "division":
        text = "Оберіть ваш Підрозділ:"
        options = [
            "Офіс", "Дніпро", "PSC", "Київ", "Біла Церква", "Суми", "Вінниця",
            "Запоріжжя", "Краматорськ", "Кривий Ріг", "Кропивницький", "Львів",
            "Одеса", "Полтава", "Харків", "Черкаси", "Чернігів", "Імпорт"
        ]
    elif steps[step] == "department":
        text = "Оберіть Департамент:"
        options = [
            "Комерційний департамент", "Операційний департамент", "Департамент маркетинга",
            "ІТ департамент", "Юр. департамент", "Департамент безпеки", "Департамент персоналу",
            "Фінансовий департамент", "Бухгалтерія", "Контрольно ревізійний відділ", "Відділ кадрів"
        ]
    elif steps[step] == "service":
        text = "Оберіть Сервіс:"
        options = [
            "E-mix 2.x", "E-mix 3.x", "E-supervisor", "E-mix market-android",
            "E-mix market iOS", "E-drive", "E-inventory", "Пошта",
            "Мобільний зв'язок", "Ремонт техніки", "Портал техпідтримки"
        ]
    elif steps[step] == "full_name":
        text = "Введіть ваше Прізвище та Ім'я:"
    elif steps[step] == "description":
        text = "Опишіть вашу проблему:"
    elif steps[step] == "confirm":
        description = user_data[user_id].get("description", "")
        text = (
            "Натисніть 'Створити задачу', якщо все заповнено.\n\n"
            f"Опис задачі:\n{description}"
        )
        options = ["Створити задачу"]

    # Формуємо клавіатуру
    keyboard = [[KeyboardButton(opt)] for opt in options]
    keyboard.append([KeyboardButton("Назад")])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(text, reply_markup=reply_markup)

# ------------------ Обробка документів ------------------
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Прикріплює документ користувача до створеної Jira-задачі."""
    user_id = update.effective_user.id
    task_id = user_data.get(user_id, {}).get("created_task_id")
    if not task_id:
        await update.message.reply_text("Немає активної задачі. Запустіть /start.")
        return

    doc = update.message.document
    if doc.file_size > 9.9 * 1024 * 1024:
        await update.message.reply_text("❗ Файл завеликий (макс 9.9 MB).")
        return

    # Завантажуємо файл у байти
    file = await context.bot.get_file(doc.file_id)
    content = await file.download_as_bytearray()

    # Формуємо запит до Jira
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{task_id}/attachments"
    auth = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "X-Atlassian-Token": "no-check",
        "Accept": "application/json"
    }
    files = {"file": (doc.file_name, content)}

    resp = requests.post(url, headers=headers, files=files)
    if resp.status_code in (200, 201):
        await update.message.reply_text(f"✅ '{doc.file_name}' прикріплено.")
    else:
        await update.message.reply_text(
            f"❌ Помилка {resp.status_code}: {resp.text}"
        )

# ------------------ Обробка текстових повідомлень ------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Збирає відповіді по кроках; при підтвердженні — створює задачу."""
    user_id = update.effective_user.id
    text = update.message.text
    step = user_data[user_id]["step"]

    # Повернутись на попередній крок
    if text == "Назад":
        user_data[user_id]["step"] = max(0, step - 1)
        await ask_next_question(update, context)
        return

    # Зберігаємо відповідь
    key = steps[step]
    if key in ("division", "department", "service", "full_name"):
        user_data[user_id][key] = text
    elif key == "description":
        user_data[user_id].setdefault("description", "")
        user_data[user_id]["description"] += text + "\n"
    elif key == "confirm" and text == "Створити задачу":
        await send_to_make(update, context)
        return

    # Переходимо далі
    user_data[user_id]["step"] = min(len(steps) - 1, step + 1)
    await ask_next_question(update, context)

# ------------------ Відправка даних у Make.com ------------------
async def send_to_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Надсилає зібрані дані на Make.com, щоб створити Jira-задачу."""
    user_id = update.effective_user.id
    payload = {
        "username": update.effective_user.username,
        "telegram_id": user_id,
        "division": user_data[user_id].get("division"),
        "department": user_data[user_id].get("department"),
        "service": user_data[user_id].get("service"),
        "full_name": user_data[user_id].get("full_name"),
        "description": user_data[user_id].get("description"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    resp = requests.post(MAKE_WEBHOOK_CREATE_TASK, json=payload)
    if resp.status_code == 200 and (result := resp.json()).get("task_id"):
        task_id = result["task_id"]
        user_data[user_id]["created_task_id"] = task_id
        await update.message.reply_text(
            f"✅ Задача сформована: {task_id}",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Перевірити статус задачі",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("Перевірити статус задачі")]],
                resize_keyboard=True
            )
        )
    else:
        await update.message.reply_text("❌ Не вдалося створити задачу.")

# ------------------ Додавання коментаря до Jira ------------------
async def add_comment_to_jira(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Додає коментар користувача до Jira-задачі."""
    user_id = update.effective_user.id
    comment = update.message.text.strip()
    task_id = user_data.get(user_id, {}).get("created_task_id")
    if not task_id:
        await update.message.reply_text("Немає ID задачі. Запустіть /start.")
        return

    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{task_id}/comment"
    auth = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    body = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": comment}]}
            ]
        }
    }

    resp = requests.post(url, headers=headers, json=body)
    if resp.status_code == 201:
        await update.message.reply_text(f"✅ Коментар додано до {task_id}.")
    else:
        await update.message.reply_text(f"❌ Помилка: {resp.status_code}.")

# ------------------ Перевірка статусу задачі ------------------
async def check_task_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отримує статус Jira-задачі та повідомляє користувача."""
    user_id = update.effective_user.id
    task_id = user_data.get(user_id, {}).get("created_task_id")
    if not task_id:
        await update.message.reply_text("Немає ID задачі.")
        return

    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{task_id}"
    resp = requests.get(url, auth=(JIRA_EMAIL, JIRA_API_TOKEN), headers={"Accept":"application/json"})
    if resp.status_code == 200:
        status = resp.json()["fields"]["status"]["name"]
        await update.message.reply_text(f"Статус {task_id}: {status}")
        if status.lower() == "готово":
            await update.message.reply_text(
                "✅ Задача завершена.",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("Старт. Створити нову заявку")]],
                    resize_keyboard=True
                )
            )
            user_data.pop(user_id, None)
    else:
        await update.message.reply_text(f"❌ Не вдалося отримати статус: {resp.status_code}")

# ------------------ Універсальний обробник ------------------
async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Розподіляє вхідні повідомлення між відповідними обробниками."""
    text = update.message.text if update.message else ""
    user_id = update.effective_user.id if update.effective_user else None

    if text == "Перевірити статус задачі":
        await check_task_status(update, context)
    elif text == "Старт. Створити нову заявку":
        await start(update, context)
    elif user_data.get(user_id, {}).get("created_task_id"):
        # Після створення задачі — дозволяємо додати коментар
        await add_comment_to_jira(update, context)
    else:
        await handle_message(update, context)

# ------------------ Запуск ------------------
if __name__ == "__main__":
    # Реєструємо хендлери
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))

    # Запускаємо webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8443)),
        url_path="webhook",
        webhook_url=WEBHOOK_URL,
        cert=SSL_CERT_PATH,
        key=SSL_KEY_PATH,
    )

