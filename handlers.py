# handlers.py
import base64
import logging
from datetime import datetime
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import ContextTypes

from keyboards import make_keyboard, remove_keyboard, STEPS
from services import (
    create_jira_issue,
    attach_file_to_jira,
    add_comment_to_jira,
    get_issue_status,
)

logger = logging.getLogger(__name__)

# Зберігаємо стан користувачів
user_data: dict[int, dict] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data[uid] = {"step": 0}
    text, mkp = make_keyboard(0)
    await update.message.reply_text(text, reply_markup=mkp)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return

    text = update.message.text or ""
    step = user_data[uid]["step"]
    key = STEPS[step]

    # Кнопка «Назад»
    if text == "Назад":
        user_data[uid]["step"] = max(0, step - 1)
        txt, mkp = make_keyboard(user_data[uid]["step"], user_data[uid].get("description", ""))
        await update.message.reply_text(txt, reply_markup=mkp)
        return

    # Запис відповіді
    if key in ("division", "department", "service", "full_name"):
        user_data[uid][key] = text
    elif key == "description":
        user_data[uid].setdefault("description", "")
        user_data[uid]["description"] += text + "\n"
    elif key == "confirm":
        # якщо натиснули Створити
        if text == "Створити задачу":
            await send_to_jira(update, context)
            return
        # або додали ще рядок до опису
        user_data[uid].setdefault("description", "")
        user_data[uid]["description"] += text + "\n"
        txt, mkp = make_keyboard(step, user_data[uid]["description"])
        await update.message.reply_text(txt, reply_markup=mkp)
        return

    # Перехід до наступного кроку
    user_data[uid]["step"] = min(len(STEPS) - 1, step + 1)
    txt, mkp = make_keyboard(user_data[uid]["step"], user_data[uid].get("description", ""))
    await update.message.reply_text(txt, reply_markup=mkp)


async def send_to_jira(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    desc = user_data[uid].get("description", "").strip()
    # перший рядок опису беремо як summary
    summary = desc.split("\n", 1)[0] if desc else "Нова задача"
    result = await create_jira_issue(summary, desc)
    status = result.get("status_code") or result.get("code", 0)
    if status in (200, 201):
        issue = result["json"]["key"]
        user_data[uid]["task_id"] = issue

        # прибираємо клавіатуру збору даних
        await update.message.reply_text(
            f"✅ Задача створена: {issue}",
            reply_markup=ReplyKeyboardRemove()
        )

        # надсилаємо кнопку для перевірки статусу
        markup = ReplyKeyboardMarkup(
            [[KeyboardButton("Перевірити статус задачі")]],
            resize_keyboard=True
        )
        await update.message.reply_text(
            "Щоб перевірити статус задачі, натисніть кнопку нижче",
            reply_markup=markup
        )
    else:
        err = result.get("json", {}).get("errorMessages", result.get("error"))
        await update.message.reply_text(f"❌ Помилка створення задачі: {status}: {err}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start")
        return
    tid = user_data[uid].get("task_id")
    if not tid:
        await update.message.reply_text("❗ Спочатку натисніть 'Створити задачу', а потім надсилайте файли.")
        return

    doc = update.message.document
    if doc.file_size > 9.9 * 1024 * 1024:
        await update.message.reply_text("❗ Файл занадто великий (макс 9.9 MB).")
        return

    file = await context.bot.get_file(doc.file_id)
    content = await file.download_as_bytearray()
    resp = await attach_file_to_jira(tid, doc.file_name, content)
    if resp.status_code in (200, 201):
        await update.message.reply_text(f"✅ '{doc.file_name}' прикріплено")
    else:
        await update.message.reply_text(f"⛔ Помилка при надсиланні файлу: {resp.status_code}")


async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    tid = user_data.get(uid, {}).get("task_id")
    if not tid:
        await update.message.reply_text("Немає ID задачі.")
        return
    try:
        st = await get_issue_status(tid)
        await update.message.reply_text(f"Статус {tid}: {st}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка при отриманні статусу: {e}")


async def add_comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    tid = user_data.get(uid, {}).get("task_id")
    if not tid:
        await update.message.reply_text("Немає ID задачі.")
        return
    c = update.message.text.strip()
    resp = await add_comment_to_jira(tid, c)
    if resp.status_code == 201:
        await update.message.reply_text("✅ Коментар додано")
    else:
        await update.message.reply_text(f"⛔ Помилка додавання коментаря: {resp.status_code}")


async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # документи насамперед
    if update.message.document:
        await handle_document(update, context)
        return

    txt = update.message.text or ""
    if txt == "/start":
        await start(update, context)
    elif txt == "Перевірити статус задачі":
        await check_status(update, context)
    elif user_data.get(update.effective_user.id, {}).get("task_id"):
        await add_comment_handler(update, context)
    else:
        await handle_message(update, context)
