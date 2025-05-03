#!/usr/bin/env python3
from datetime import datetime
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from telegram.ext import ContextTypes
from google_sheets_service import get_user_tickets
from keyboards import (
    make_keyboard, remove_keyboard, STEPS,
    main_menu_markup, after_create_menu_markup, mytickets_action_markup,
    comment_mode_markup, BUTTONS
)
from services import (
    create_jira_issue,
    attach_file_to_jira,
    add_comment_to_jira,
    get_issue_status
)
from google_sheets_service import add_ticket

# Сховище стану користувача в пам'яті процесу
user_data: dict[int, dict] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data[uid] = {"step": 0}

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="👋 Вітаємо! Оберіть дію нижче:",
            reply_markup=main_menu_markup
        )
    except Exception as e:
        logger.exception("🚫 Помилка в функції start: %s", e)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Помилка при відображенні кнопок. Спробуйте ще раз або напишіть /start."
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

    buttons = []
    for t in sorted_tickets:
        issue_id = t.get("Ticket_ID", "N/A")
        try:
            status = await get_issue_status(issue_id)
        except Exception:
            status = "❓ помилка"
        label = f"{issue_id} — {status}"
        # callback_data з префіксом comment_task_
        buttons.append([InlineKeyboardButton(label, callback_data=f"comment_task_{issue_id}")])

    await update.message.reply_text(
        "🖋️ Оберіть задачу для коментаря:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def choose_task_for_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    tickets = get_user_tickets(uid)

    if not tickets:
        await update.message.reply_text("❗️ У вас немає заявок для коментаря.", reply_markup=None)
        return

    # Відсортувати за датою і взяти останні 10
    sorted_tickets = sorted(
        tickets,
        key=lambda t: t.get("Created_At", ""),
        reverse=True
    )[:10]

    buttons = []
    for t in sorted_tickets:
        issue_id = t.get("Ticket_ID", "N/A")
        try:
            status = await get_issue_status(issue_id)
        except Exception:
            status = "❓ помилка"
        label = f"{issue_id} — {status}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"comment_task_{issue_id}")])

    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "🖋️ Натисніть на задачу щоб переглянути детальніше і додати коментар:",
        reply_markup=markup
    )

# 1) обробляє клік на інлайн-кнопку «comment_task_<ID>»
async def handle_comment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_reply_markup(reply_markup=None)

    uid = query.from_user.id
    task_id = query.data.replace("comment_task_", "", 1)

    user_data.setdefault(uid, {})
    user_data[uid]["user_comment_mode"] = True
    user_data[uid]["comment_task_id"] = task_id

    # Запит на перший коментар + кнопка ❌
    await query.message.reply_text(
        f"✍️ Ви пишете коментар до {task_id}.\nНадішліть текст або натисніть ❌ для виходу.",
        reply_markup=comment_mode_markup
    )

async def comment_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє текст у режимі коментування.
    Якщо text == BUTTONS['exit_comment'] — виходить в головне меню,
    інакше — відправляє коментар і лишається в режимі.
    """
    uid = update.effective_user.id
    if not user_data.get(uid, {}).get("user_comment_mode"):
        return  # не в режимі — пропускаємо

    text = update.message.text

    # 1) Вихід із режиму
    if text == BUTTONS["exit_comment"]:
        user_data[uid]["user_comment_mode"] = False
        user_data[uid]["comment_task_id"] = None
        await update.message.reply_text(
            "🔙 Ви вийшли з режиму коментаря.",
            reply_markup=main_menu_markup
        )
        return

    # 2) Власне коментар
    task_id = user_data[uid].get("comment_task_id")
    if not task_id:
        # якщо раптом немає прив’язки — просто виходимо
        user_data[uid]["user_comment_mode"] = False
        return

    resp = await add_comment_to_jira(task_id, text)

    if resp.status_code == 201:
        await update.message.reply_text(
            f"✅ Коментар додано до задачі {task_id}\n\n"
            "Можете продовжувати писати нові коментарі або натиснути ❌ для виходу.",
            reply_markup=comment_mode_markup
        )
    else:
        await update.message.reply_text(
            f"⛔ Помилка додавання коментаря: {resp.status_code}\n\n"
            "Спробуйте ще раз або натисніть ❌ для виходу.",
            reply_markup=comment_mode_markup
        )
async def send_to_jira(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    desc = user_data[uid].get("description", "").strip()
    summary = desc.split("\n", 1)[0]
    result = await create_jira_issue(summary, desc)
    code = result["status_code"]

    if code == 201:
        issue_key = result["json"]["key"]
        # Переходимо у режим додавання коментаря після створення
        user_data[uid]["task_id"] = issue_key
        user_data[uid]["user_comment_mode"] = True
        user_data[uid]["comment_task_id"] = issue_key

        try:
            add_ticket(
                ticket_id=issue_key,
                telegram_user_id=uid,
                telegram_chat_id=update.effective_chat.id,
                telegram_username=update.effective_user.username
            )
        except Exception as e:
            print(f"[GoogleSheets] ❗ Помилка при записі в таблицю: {e}")

        await update.message.reply_text(
            f"✅ Задача створена: {issue_key}",
            reply_markup=after_create_menu_markup
        )
    else:
        err = result["json"].get("errorMessages") or result["json"]
        await update.message.reply_text(f"❌ Помилка створення задачі: {code}: {err}")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data or "task_id" not in user_data[uid]:
        await update.message.reply_text(
            "❗ Спочатку натисніть 'Створити задачу', а потім надсилайте файли."
        )
        return

    tid = user_data[uid]["task_id"]
    file_obj = None
    filename = None

    # будь-який тип media/document/photo/video/audio
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

    # завантажити bytes
    f = await context.bot.get_file(file_obj.file_id)
    content = await f.download_as_bytearray()
    resp = await attach_file_to_jira(tid, filename, content)
    if resp.status_code in (200, 201):
        await update.message.reply_text(f"✅ '{filename}' прикріплено")
    else:
        await update.message.reply_text(
            f"⛔ Помилка при надсиланні файлу: {resp.status_code}"
        )

async def add_comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Всередині universal_handler: коли user_comment_mode==True
    ми ловимо будь-який текст (окрім EXIT) тут і додаємо коментар.
    Після цього лишаємо режим увімкненим.
    """
    uid = update.effective_user.id
    tid = user_data[uid].get("comment_task_id")
    text = update.message.text.strip()

    resp = await add_comment_to_jira(tid, text)
    if resp.status_code == 201:
        await update.message.reply_text(
            f"✅ Коментар додано до задачі {tid}.\n"
            "Можете писати ще коментарі або натиснути ❌ для виходу.",
            reply_markup=comment_mode_markup
        )
    else:
        await update.message.reply_text(
            f"⛔ Не вдалося додати коментар: {resp.status_code}\n"
            "Спробуйте ще раз або натисніть ❌ для виходу.",
            reply_markup=comment_mode_markup
        )
    # Не вимикаємо user_comment_mode — чекаємо EXIT

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    if uid not in user_data:
        await update.message.reply_text("Будь ласка, натисніть /start")
        return

    step = user_data[uid].get("step", 0)
    key = STEPS[step]

    if text == BUTTONS["back"]:
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
        if text == BUTTONS["confirm_create"]:
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

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text or ""

    # 1️⃣ Якщо медіа — передаємо в handle_media
    if update.message.document or update.message.photo or update.message.video or update.message.audio:
        await handle_media(update, context)
        return

    # 2️⃣ Режим коментаря
    if user_data.get(uid, {}).get("user_comment_mode"):
        if text == BUTTONS["exit_comment"]:
            # EXIT: вимикаємо режим і повертаємо головне меню
            user_data[uid]["user_comment_mode"] = False
            user_data[uid]["comment_task_id"] = None
            await update.message.reply_text(
                "🔙 Ви вийшли з режиму коментаря.",
                reply_markup=main_menu_markup
            )
        else:
            # будь-який інший текст — додаємо коментар
            await add_comment_handler(update, context)
        return

    # 3️⃣ Стандартна логіка
    if text == BUTTONS["help"]:
        await start(update, context)
    elif text in (BUTTONS["my_tickets"], BUTTONS["my_tasks"]):
        await mytickets_handler(update, context)
    elif text == BUTTONS["create_ticket"]:
        user_data[uid] = {"step": 0}
        txt, markup = make_keyboard(0)
        await update.message.reply_text(txt, reply_markup=markup)
    elif text == BUTTONS["check_status"]:
        await check_status(update, context)
    elif text == BUTTONS["add_comment"]:
        await choose_task_for_comment(update, context)
    elif user_data.get(uid, {}).get("task_id"):
        await add_comment_handler(update, context)
    else:
        await handle_message(update, context)

async def exit_comment_mode(update: Update, uid: int):
    # Вимикаємо режим коментаря
    user_data[uid]["user_comment_mode"] = False
    user_data[uid]["comment_task_id"] = None
    await update.message.reply_text(
        "🔙 Ви вийшли з режиму коментаря.",
        reply_markup=main_menu_markup
    )
