import os
import logging
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from gspread.exceptions import SpreadsheetNotFound

# Завантаження .env
load_dotenv()
logger = logging.getLogger(__name__)

# -----------------------
# ПІДКЛЮЧЕННЯ ДО ТАБЛИЦЬ
# -----------------------

def connect_to_users_sheet():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)

        sheet_id = os.getenv("GOOGLE_SHEET_users_ID")
        return client.open_by_key(sheet_id).sheet1  # 🟢 Використати перший аркуш
    except Exception as e:
        logger.error(f"[connect_to_users_sheet] ❌ Error: {e}")
        return None

def connect_to_ticket_sheet():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)

        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        sheet_name = os.getenv("GOOGLE_SHEET_NAME", "euromix_tickets")
        return client.open_by_key(sheet_id).worksheet(sheet_name)
    except SpreadsheetNotFound:
        logger.error("[connect_to_ticket_sheet] ❗️ Sheet not found. Check GOOGLE_SHEET_ID and name.")
        return None
    except Exception as e:
        logger.error(f"[connect_to_ticket_sheet] ❌ {e}")
        return None

# -----------------------
# ІДЕНТИФІКАЦІЯ КОРИСТУВАЧА
# -----------------------

async def identify_user_by_telegram(user_id: int, username: str = "", phone: str = "") -> dict | None:
    """
    Повертає словник з даними користувача, якщо знайдено за:
    - telegram_id
    - telegram_username
    - або номером телефону (з нормалізацією)
    """
    try:
        sheet = connect_to_users_sheet()
        if not sheet:
            return None

        rows = sheet.get_all_values()[1:]  # Пропускаємо заголовки
        headers = ["user_key_1", "full_name", "division", "department", "mobile_number",
                   "telegram_id", "telegram_username", "email", "account_id"]

        # Очистка номера від '+' та пробілів
        phone = phone.lstrip("+").replace(" ", "").strip() if phone else ""

        for idx, row in enumerate(rows):
            record = dict(zip(headers, row + [""] * (len(headers) - len(row))))
            row_index = idx + 2

            row_phone = record.get("mobile_number", "").lstrip("+").replace(" ", "").strip()
            row_uid = record.get("telegram_id", "").strip()
            row_uname = record.get("telegram_username", "").strip().lower()

            # 1) Збіг по Telegram ID
            if str(user_id) == row_uid:
                if not row_uname and username:
                    sheet.update_cell(row_index, 7, username)
                return record

            # 2) Збіг по username
            if username and username.lower() == row_uname:
                if not row_uid:
                    sheet.update_cell(row_index, 6, str(user_id))
                return record

            # 3) Збіг по номеру телефону
            if phone and phone == row_phone:
                if not row_uid:
                    sheet.update_cell(row_index, 6, str(user_id))
                if not row_uname and username:
                    sheet.update_cell(row_index, 7, username)
                return record

        return None

    except Exception as e:
        logger.exception(f"[identify_user_by_telegram] ❌ Error: {e}")
        return None

# -----------------------
# ЗАЯВКИ
# -----------------------

def add_ticket(ticket_id, telegram_user_id, telegram_chat_id, telegram_username=None, status="Open"):
    sheet = connect_to_ticket_sheet()
    if sheet is None:
        return

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [
        ticket_id,
        telegram_user_id,
        telegram_chat_id,
        created_at,
        status,
        telegram_username or "",
        "",  # User_name_Real
        ""   # Account_ID
    ]
    try:
        sheet.append_row(row)
    except Exception as e:
        logger.error(f"[GoogleSheets] ❗ Помилка при записі заявки: {e}")

def update_ticket_status(ticket_id, new_status):
    sheet = connect_to_ticket_sheet()
    if sheet is None:
        return

    try:
        cell = sheet.find(ticket_id)
        if cell:
            sheet.update_cell(cell.row, 5, new_status)
        else:
            logger.warning(f"[GoogleSheets] Ticket ID '{ticket_id}' не знайдено.")
    except Exception as e:
        logger.error(f"[GoogleSheets] Помилка при оновленні статусу: {e}")

def get_user_tickets(telegram_user_id):
    sheet = connect_to_ticket_sheet()
    if sheet is None:
        return []

    try:
        records = sheet.get_all_records()
        return [
            record for record in records
            if str(record.get('Telegram_User_ID')) == str(telegram_user_id)
        ]
    except Exception as e:
        logger.error(f"[GoogleSheets] Помилка при отриманні заявок: {e}")
        return []
