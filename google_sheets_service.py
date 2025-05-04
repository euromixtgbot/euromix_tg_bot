# google_sheets_service.py

import os
import logging
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from gspread.exceptions import SpreadsheetNotFound

# Завантаження змінних оточення з .env
load_dotenv()

logger = logging.getLogger(__name__)

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
        sheet = client.open_by_key(sheet_id).worksheet("users")
        return sheet
    except Exception as e:
        logger.error(f"[connect_to_users_sheet] ❌ Error: {e}")
        return None

async def identify_user_by_telegram(user_id: int, username: str = "", phone: str = "") -> dict | None:
    """
    Повертає словник з даними користувача, якщо знайдено за:
    1) Telegram ID
    2) Telegram username
    3) Номер телефону (формат +380...)
    
    Якщо знайдено лише за username або телефоном — оновлює telegram_id / telegram_username в таблиці.
    """
    try:
        sheet = service.spreadsheets().values().get(
            spreadsheetId=os.getenv("GOOGLE_SHEET_users_ID"),
            range="users!A2:F1000"
        ).execute()

        rows = sheet.get("values", [])
        headers = ["full_name", "mobile_number", "telegram_id", "telegram_username", "email", "account_id"]

        for idx, row in enumerate(rows):
            record = dict(zip(headers, row + [""] * (6 - len(row))))
            row_index = idx + 2  # бо A2:F1000

            # 1) Прямий збіг по Telegram ID
            if str(user_id) == record.get("telegram_id"):
                return record

            # 2) Якщо збіг по username — оновлюємо telegram_id
            if username and username.lower() == record.get("telegram_username", "").lower():
                service.spreadsheets().values().update(
                    spreadsheetId=os.getenv("GOOGLE_SHEET_users_ID"),
                    range=f"users!C{row_index}",
                    valueInputOption="RAW",
                    body={"values": [[str(user_id)]]}
                ).execute()
                return record

            # 3) Якщо збіг по телефону — оновлюємо ID та username
            if phone and phone == record.get("mobile_number"):
                updates = []
                if not record.get("telegram_id"):
                    updates.append(("C", str(user_id)))
                if not record.get("telegram_username") and username:
                    updates.append(("D", username))

                for col, val in updates:
                    service.spreadsheets().values().update(
                        spreadsheetId=os.getenv("GOOGLE_SHEET_users_ID"),
                        range=f"users!{col}{row_index}",
                        valueInputOption="RAW",
                        body={"values": [[val]]}
                    ).execute()
                return record

        return None

    except Exception as e:
        logger.exception(f"[identify_user_by_telegram] ❌ Error: {e}")
        return None


def connect_to_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    sheet_name = os.getenv("GOOGLE_SHEET_NAME", "euromix_tickets")

    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)

    try:
        if sheet_id:
            return client.open_by_key(sheet_id).sheet1
        else:
            return client.open(sheet_name).sheet1
    except SpreadsheetNotFound:
        identifier = sheet_id or sheet_name
        logger.error(f"[GoogleSheets] Лист '{identifier}' не знайдено. Перевірте GOOGLE_SHEET_ID/GOOGLE_SHEET_NAME у .env")
        return None
    except Exception as e:
        logger.error(f"[GoogleSheets] Помилка підключення до Sheets: {e}")
        return None

def add_ticket(ticket_id, telegram_user_id, telegram_chat_id, telegram_username=None, status="Open"):
    sheet = connect_to_sheet()
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
        logger.error(f"[GoogleSheets] ❗ Помилка при записі в таблицю: {e}")

def update_ticket_status(ticket_id, new_status):
    sheet = connect_to_sheet()
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
    sheet = connect_to_sheet()
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
