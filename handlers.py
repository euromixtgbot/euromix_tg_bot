from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from keyboards import make_keyboard, remove_keyboard, STEPS
from services import (
    create_jira_issue, attach_file_to_jira,
    add_comment_to_jira, get_issue_status
)

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

    text = update.message.text
    step = user_data[uid]["step"]
    key = STEPS[step]

    if text == "Назад":
        user_data[uid]["step"] = max(0, step - 1)
        txt, mkp = make_keyboard(user_data[uid]["step"], user_data[uid].get("description",""))
        await update.message.reply_text(txt, reply_markup=mkp)
        return

    if key in ("division","department","service","full_name"):
        user_data[uid][key] = text
    elif key == "description":
        user_data[uid].setdefault("description","")
        user_data[uid]["description"] += text + "\n"
    elif key == "confirm":
        if text == "Створити задачу":
            await send_to_jira(update, context)
            return
        else:
            user_data[uid].setdefault("description","")
            user_data[uid]["description"] += text + "\n"
            txt, mkp = make_keyboard(step, user_data[uid]["description"])
            await update.message.reply_text(txt, reply_markup=mkp)
            return

    user_data[uid]["step"] = min(len(STEPS)-1, step+1)
    txt, mkp = make_keyboard(user_data[uid]["step"], user_data[uid].get("description",""))
    await update.message.reply_text(txt, reply_markup=mkp)

async def send_to_jira(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    desc = user_data[uid].get("description","").strip()
    summary = desc.split("\n",1)[0]  # перший рядок як заголовок
    result = await create_jira_issue(summary, desc)
    code = result["status_code"]
    if code == 201:
        issue_key = result["json"]["key"]
        user_data[uid]["task_id"] = issue_key
        await update.message.reply_text(f"✅ Задача створена: {issue_key}", reply_markup=remove_keyboard())
        await update.message.reply_text("Перевірити статус задачі")
    else:
        err = result["json"].get("errorMessages") or result["json"]
        await update.message.reply_text(f"❌ Помилка створення задачі: {code}: {err}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, почніть з /start"); return
    tid = user_data[uid].get("task_id")
    if not tid:
        await update.message.reply_text("❗ Спочатку 'Створити задачу', потім надсилайте файли."); return

    doc = update.message.document
    if doc.file_size > 9.9*1024*1024:
        await update.message.reply_text("❗ Файл >9.9MB"); return

    file = await context.bot.get_file(doc.file_id)
    content = await file.download_as_bytearray()
    resp = await attach_file_to_jira(tid, doc.file_name, content)
    if resp.status_code in (200,201):
        await update.message.reply_text(f"✅ '{doc.file_name}' прикріплено")
    else:
        await update.message.reply_text(f"⛔ Помилка при надсиланні файлу: {resp.status_code}")

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    tid = user_data.get(uid,{}).get("task_id")
    if not tid:
        await update.message.reply_text("Немає ID"); return
    try:
        st = await get_issue_status(tid)
        await update.message.reply_text(f"Статус {tid}: {st}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка при отриманні статусу: {e}")

async def add_comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    tid = user_data.get(uid,{}).get("task_id")
    if not tid:
        await update.message.reply_text("Немає ID"); return
    c = update.message.text.strip()
    resp = await add_comment_to_jira(tid, c)
    if resp.status_code == 201:
        await update.message.reply_text("✅ Коментар додано")
    else:
        await update.message.reply_text(f"⛔ Помилка додавання коментаря: {resp.status_code}")

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        await handle_document(update, context)
        return
    txt = update.message.text or ""
    if txt == "/start":
        await start(update, context)
    elif txt == "Перевірити статус задачі":
        await check_status(update, context)
    elif user_data.get(update.effective_user.id,{}).get("task_id"):
        await add_comment_handler(update, context)
    else:
        await handle_message(update, context)
