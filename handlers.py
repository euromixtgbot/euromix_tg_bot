from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.ext import ContextTypes, CallbackQueryHandler
from google_sheets_service import get_user_tickets
from keyboards import make_keyboard, remove_keyboard, STEPS, main_menu_markup, after_create_menu_markup, mytickets_action_markup
from services import (
    create_jira_issue,
    attach_file_to_jira,
    add_comment_to_jira,
    get_issue_status
)
from google_sheets_service import add_ticket

user_data: dict[int, dict] = {}

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 Допомога:\n"
        "Цей бот дозволяє створювати задачі в Jira та перевіряти їх статус.\n"
        "Ви можете надсилати файли, які будуть прикріплені до задачі.\n"
        "Для початку натисніть /start."
    )

async def mytickets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    tickets = get_user_tickets(uid)

    if not tickets:
        await update.message.reply_text("❗️ У вас немає створених заявок.")
        return

    sorted_tickets = sorted(
        tickets,
        key=lambda t: t.get("Created_At", ""),
        reverse=True
    )[:10]

    lines = []
    for t in sorted_tickets:
        ticket_id = t.get("Ticket_ID", "N/A")
        status = t.get("Status", "Невідомо")
        created_at = t.get("Created_At", "")
        lines.append(f"📌 {ticket_id} — {status} ({created_at})")
    msg = "🧾 Ваші останні заявки:\n\n" + "\n".join(lines)
    await update.message.reply_text(msg, reply_markup=mytickets_action_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data[uid] = {"step": 0}
    await update.message.reply_text("👋 Вітаємо! Оберіть дію нижче:", reply_markup=main_menu_markup)

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
        key_to_clear = STEPS[user_data[uid]["step"]]
        user_data[uid][key_to_clear] = ""
        txt, mkp = make_keyboard(user_data[uid]["step"], user_data[uid].get("description", ""))
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
            txt, mkp = make_keyboard(step, user_data[uid]["description"])
            await update.message.reply_text(txt, reply_markup=mkp)
            return

    user_data[uid]["step"] = min(len(STEPS) - 1, step + 1)
    txt, mkp = make_keyboard(user_data[uid]["step"], user_data[uid].get("description", ""))
    await update.message.reply_text(txt, reply_markup=mkp)

async def send_to_jira(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    desc = user_data[uid].get("description", "").strip()
    summary = desc.split("\n", 1)[0]
    result = await create_jira_issue(summary, desc)
    code = result["status_code"]
    if code == 201:
        issue_key = result["json"]["key"]
        user_data[uid]["task_id"] = issue_key
        try:
            add_ticket(
                ticket_id=issue_key,
                telegram_user_id=update.effective_user.id,
                telegram_chat_id=update.effective_chat.id,
                telegram_username=update.effective_user.username
            )
        except Exception as e:
            print(f"[GoogleSheets] ❗ Помилка при записі в таблицю: {e}")

        await update.message.reply_text(f"✅ Задача створена: {issue_key}", reply_markup=after_create_menu_markup)
    else:
        err = result["json"].get("errorMessages") or result["json"]
        await update.message.reply_text(f"❌ Помилка створення задачі: {code}: {err}")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data or "task_id" not in user_data[uid]:
        await update.message.reply_text("❗ Спочатку натисніть 'Створити задачу', а потім надсилайте файли.")
        return

    tid = user_data[uid]["task_id"]
    file_obj = None
    filename = None

    if update.message.document:
        file_obj = update.message.document
        filename = file_obj.file_name
    elif update.message.photo:
        file_obj = update.message.photo[-1]
        filename = f"photo_{datetime.now().strftime('%H%M%S')}.jpg"
    elif update.message.video:
        file_obj = update.message.video
        filename = file_obj.file_name or f"video_{file_obj.file_id}.mp4"
    elif update.message.audio:
        file_obj = update.message.audio
        filename = file_obj.file_name or f"audio_{file_obj.file_id}.mp3"
    else:
        await update.message.reply_text("⚠️ Непідтримуваний тип файлу.")
        return

    f = await context.bot.get_file(file_obj.file_id)
    content = await f.download_as_bytearray()
    resp = await attach_file_to_jira(tid, filename, content)
    if resp.status_code in (200, 201):
        await update.message.reply_text(f"✅ '{filename}' прикріплено")
    else:
        await update.message.reply_text(f"⛔ Помилка при надсиланні файлу: {resp.status_code}")

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    tid = user_data.get(uid, {}).get("task_id")
    if not tid:
        await update.message.reply_text("Немає активної задачі.")
        return
    try:
        st = await get_issue_status(tid)
        await update.message.reply_text(f"Статус {tid}: {st}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка при отриманні статусу: {e}")

async def choose_task_for_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    tickets = get_user_tickets(uid)
    if not tickets:
        await update.message.reply_text("У вас немає активних задач.")
        return

    buttons = []
    for t in tickets[:10]:
        task_id = t.get("Ticket_ID")
        status = t.get("Status", "Невідомо")
        btn = InlineKeyboardButton(text=f"{task_id} ({status})", callback_data=f"comment_task_{task_id}")
        buttons.append([btn])

    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Оберіть задачу для коментаря:", reply_markup=markup)

async def handle_comment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query: CallbackQuery = update.callback_query
    await query.answer()

    uid = query.from_user.id
    data = query.data

    if data.startswith("comment_task_"):
        task_id = data.replace("comment_task_", "")
        user_data[uid]["user_comment_mode"] = True
        user_data[uid]["comment_task_id"] = task_id
        await query.message.reply_text(f"✍️ Напишіть коментар до задачі {task_id}")

async def add_comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if user_data.get(uid, {}).get("user_comment_mode"):
        tid = user_data[uid].get("comment_task_id")
        comment = update.message.text.strip()
        resp = await add_comment_to_jira(tid, comment)
        if resp.status_code == 201:
            await update.message.reply_text(f"✅ Коментар додано до задачі {tid}")
        else:
            await update.message.reply_text(f"⛔ Помилка додавання коментаря: {resp.status_code}")
        user_data[uid]["user_comment_mode"] = False
        user_data[uid]["comment_task_id"] = None
        return

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if update.message.document or update.message.photo or update.message.video or update.message.audio:
        await handle_media(update, context)
    else:
        txt = update.message.text or ""
        if txt in ("/start", "ℹ️ Допомога"):
            await start(update, context)
        elif txt == "🧾 Мої заявки":
            await mytickets_handler(update, context)
        elif txt == "🆕 Створити заявку":
            user_data[uid] = {"step": 0}
            text, markup = make_keyboard(0)
            await update.message.reply_text(text, reply_markup=markup)
        elif txt == "Перевірити статус задачі":
            await check_status(update, context)
        elif txt == "📝 Додати коментар до задачі":
            await choose_task_for_comment(update, context)
        elif user_data.get(uid, {}).get("user_comment_mode"):
            await add_comment_handler(update, context)
        elif user_data.get(uid, {}).get("task_id"):
            await add_comment_handler(update, context)
        else:
            await handle_message(update, context)
