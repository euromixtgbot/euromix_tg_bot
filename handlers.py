#!/usr/bin/env python3
import logging
logger = logging.getLogger(__name__)
from datetime import datetime
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from telegram.ext import ContextTypes

from google_sheets_service import (
    get_user_tickets,
    add_ticket,
    identify_user_by_telegram
)

from keyboards import (
    make_keyboard, remove_keyboard, STEPS,
    main_menu_markup, after_create_menu_markup, mytickets_action_markup,
    comment_mode_markup, BUTTONS,
    request_contact_keyboard
)

from services import (
    create_jira_issue,
    attach_file_to_jira,
    add_comment_to_jira,
    get_issue_status
)

# Сховище стану користувача в пам'яті процесу
user_data: dict[int, dict] = {}

import logging
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт та головне меню"""
    user = update.effective_user
    uid = user.id
    uname = user.username or ""

    logger.info(f"[START] User {uid} (@{uname}) викликав /start")

    # Ідентифікація користувача
    phone = context.user_data.get("pending_phone_check")
    profile = await identify_user_by_telegram(uid, uname, phone)
    context.user_data["profile"] = profile

    if profile:
        fname = profile.get("full_name", "Користувач")
        logger.info(f"[START] User {uid} авторизований як {fname}")
        await update.message.reply_text(
            f"👋 Вітаю, {fname}! Оберіть дію:",
            reply_markup=main_menu_markup
        )
    else:
        logger.info(f"[START] User {uid} не авторизований")
        await update.message.reply_text(
            "🔐 Ви ще не авторизовані. Надішліть номер телефону для авторизації:",
            reply_markup=request_contact_keyboard()
        )

    context.user_data['started'] = True


async def mytickets_handler(update, context):
    user_id = update.effective_user.id
    # 1) Дістаємо всі записи–заявки з Google Sheets
    records = await get_user_tickets(user_id)

    if not records:
        return await update.message.reply_text(
            "У вас немає відкритих заявок.",
            reply_markup=main_menu_markup
        )

    # 2) Формуємо список Inline-кнопок з ключами і статусами
    buttons = []
    for rec in records:
        issue_key = rec["Ticket_ID"]
        try:
            status = await get_issue_status(issue_key)
        except Exception:
            status = "❓ помилка"
        buttons.append([InlineKeyboardButton(
            f"{issue_key} — {status}",
            callback_data=f"comment_task_{issue_key}"
        )])

    # 3) Відправляємо список
    await update.message.reply_text(
        "✒️ Оберіть задачу для перегляду деталей:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def choose_task_for_comment(update, context):
    uid = update.effective_user.id
    tickets = await get_user_tickets(uid)  # Added await to make it asynchronous

    if not tickets:
        return await update.message.reply_text(
            "❗️ У вас немає заявок для коментаря.",
            reply_markup=main_menu_markup
        )

    # Сортуємо й беремо останні 10
    sorted_tickets = sorted(
        tickets,
        key=lambda t: t.get("Created_At", ""),
        reverse=True
    )[:10]

    keyboard = []
    for t in sorted_tickets:
        issue_id = t.get("Ticket_ID")
        try:
            status = await get_issue_status(issue_id)
        except Exception:
            status = "❓ помилка"
        keyboard.append([InlineKeyboardButton(
            f"{issue_id} — {status}",
            callback_data=f"comment_task_{issue_id}"
        )])

    await update.message.reply_text(
        "🖋️ Натисніть на задачу, щоб переглянути деталі та додати коментар:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# 1) обробляє клік на інлайн-кнопку «comment_task_<ID>»
async def handle_comment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє натиск на кнопку з issue_id:
    1) Дістає статус із Jira
    2) Дістає summary із Jira
    3) Відправляє нове повідомлення з оновленим текстом і клавіатурою comment_mode_markup
    """
    query = update.callback_query
    issue_id = query.data
    await query.answer()

    # 1) Статус
    status = await get_issue_status(issue_id)
    # 2) Summary
    summary = await get_issue_summary(issue_id)

    # 3) Новий текст замість старого
    await query.message.reply_text(
        f"✍️ Задача {issue_id} - статус: {status}\n"
        f"Summary: {summary}\n"
        "____\n"
        "Напишіть коментар до задачі, чи натисніть ❌ для виходу.",
        reply_markup=comment_mode_markup
    )

    # Перевести бота в режим коментування
    context.user_data["in_comment_mode"] = True
    context.user_data["current_issue"] = issue_id

async def add_comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє текст у режимі коментування.
    Якщо text == BUTTONS['exit_comment'] — виходить в головне меню,
    інакше — відправляє коментар і лишається в режимі.
    """
    user = update.effective_user
    uid = user.id
    logger.info(f"[COMMENT] User {uid} (@{user.username or '-'}, {user.first_name}) додає коментар")

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
    """Створює задачу в Jira і показує меню after_create"""
    user = update.effective_user
    uid = user.id
    logger.info(f"[JIRA] User {uid} створює задачу")

    # Формуємо payload для Jira
    payload = {
        "summary": context.user_data.get("summary"),
        "description": context.user_data.get("description"),
        # інші поля…
    }
    issue_key = await create_jira_issue(payload)

    # Додаємо задачу в Google Sheets
    await add_ticket({
        "issue_key": issue_key,
        "telegram_user_id": uid,
        "telegram_chat_id": update.effective_chat.id,
        "telegram_username": user.username
    })

    await update.message.reply_text(
        f"✅ Задача створена: {issue_key}",
        reply_markup=after_create_menu_markup
    )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    logger.info(f"[MEDIA] User {uid} (@{user.username or '-'}, {user.first_name}) надсилає медіа")
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
    user = update.effective_user
    uid = user.id
    logger.info(f"[COMMENT] User {uid} (@{user.username or '-'}, {user.first_name}) додає коментар")

    if not user_data.get(uid, {}).get("user_comment_mode"):
        return  # не в режимі — пропускаємо

    text = update.message.text.strip()

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
            "Можете продовжувати писати нові коментарі або натиснути 🔙 для виходу.",
            reply_markup=comment_mode_markup
        )
    else:
        await update.message.reply_text(
            f"⛔ Помилка додавання коментаря: {resp.status_code}\n\n"
            "Спробуйте ще раз або натисніть 🔙 для виходу.",
            reply_markup=comment_mode_markup
        )

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    tid = user_data.get(uid, {}).get("task_id")
    if not tid:
        await update.message.reply_text("Немає активної задачі.")
        logger.info(f"[STATUS] User {uid} (@{user.username or '-'}, {user.first_name}) — немає задачі")
        return
    try:
        st = await get_issue_status(tid)
        await update.message.reply_text(f"Статус {tid}: {st}")
        logger.info(f"[STATUS] User {uid} (@{user.username or '-'}, {user.first_name}) — статус: {st}")
    except Exception as e:
        logger.exception(f"[STATUS] User {uid} (@{user.username or '-'}, {user.first_name}) — помилка: {e}")
        await update.message.reply_text(f"⚠️ Помилка при отриманні статусу: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє текстові повідомлення"""
    text = update.message.text

    # Вихід у головне меню
    if text == BUTTONS["exit"]:
        return await start(update, context)

    # Мої заявки
    if text == BUTTONS["my_tickets"]:
        return await mytickets_handler(update, context)

    # Перевірка статусу
    if text == BUTTONS["check_status"]:
        issue_id = context.user_data.get("last_created_issue")
        status = await get_issue_status(issue_id)
        return await update.message.reply_text(
            f"Статус {issue_id}: {status}",
            reply_markup=after_create_menu_markup
        )

    # Режим коментарів
    if context.user_data.get("in_comment_mode"):
        # … обробка коментаря …
        return

    # Створення нової заявки
    if text == BUTTONS["create_ticket"]:
        context.user_data["step"] = 0
        prompt, markup = make_keyboard(0)
        return await update.message.reply_text(prompt, reply_markup=markup)

    # Інша логіка: обробка STEPS, confirm тощо…
    step = context.user_data.get("step")
    if step is not None:
        prompt, markup = make_keyboard(step, context.user_data.get("description", ""))
        # … оновлюємо step, зберігаємо дані …
        return await update.message.reply_text(prompt, reply_markup=markup)

    # За замовчуванням — невідома команда/текст
    await update.message.reply_text(
        "Невідома команда. Оберіть дію з меню:",
        reply_markup=main_menu_markup
    )

async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    text = update.message.text or ""
    logger.info(f"[UNIVERSAL] User {uid} (@{user.username or '-'}, {user.first_name}) надіслав: {text}")

    # 0️⃣ Спочатку перевіряємо кнопки, які мають пріоритет
    if text == BUTTONS["check_status"]:
        await check_status(update, context)
        return  # Важливо повернутися, щоб уникнути подальшої обробки

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
    elif text == BUTTONS["my_tickets"]:
        await mytickets_handler(update, context)
    elif text == BUTTONS["create_ticket"]:
        user_data[uid] = {"step": 0}
        txt, markup = make_keyboard(0)
        await update.message.reply_text(txt, reply_markup=markup)
    elif text == BUTTONS["add_comment"]:
        await choose_task_for_comment(update, context)
    elif text == BUTTONS["continue_unauthorized"]:
        user_data[uid] = {"step": 0}
        await update.message.reply_text(
            "📋 Ви продовжили без авторизації. Меню дій:",
            reply_markup=mytickets_action_markup
        )
        return
    elif text == BUTTONS["restart"]:
        await start(update, context)
        return
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
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    uname = user.username or ""
    phone = update.message.contact.phone_number

    logger.info(f"[CONTACT] Отримано номер {phone} від UID={uid}, @{uname}")

    try:
        profile = await identify_user_by_telegram(uid, uname, phone)
        if profile:
            context.user_data["started"] = True
            context.user_data["profile"] = profile
            context.user_data.pop("pending_phone_check", None)  # Видаляємо pending_phone_check
            fname = profile.get("full_name", "Користувач")
            await update.message.reply_text(
                f"✅ Вітаємо, {fname}! Ви авторизовані.",
                reply_markup=main_menu_markup
            )
        else:
            await update.message.reply_text(
                "⛔ Номер не знайдено в базі. Зверніться до адміністратора.",
                reply_markup=ReplyKeyboardMarkup(
                    [
                        [KeyboardButton(BUTTONS["continue_unauthorized"])],
                        [KeyboardButton(BUTTONS["restart"])]
                    ],
                    resize_keyboard=True
                )
            )
    except Exception as e:
        logger.exception(f"[CONTACT] Помилка обробки: {e}")
        await update.message.reply_text("⚠️ Помилка. Спробуйте пізніше.")
