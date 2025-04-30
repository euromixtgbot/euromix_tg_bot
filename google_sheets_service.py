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

def connect_to_sheet():
    """
    Підключення до Google Sheets по ID або за назвою.
    Повертає об’єкт Sheet або None у разі помилки.
    """
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
            sheet = client.open_by_key(sheet_id).sheet1
        else:
            sheet = client.open(sheet_name).sheet1
        return sheet

    except SpreadsheetNotFound:
        identifier = sheet_id or sheet_name
        logger.error(
            f"[GoogleSheets] Лист '{identifier}' не знайдено. "
            "Перевірте GOOGLE_SHEET_ID/GOOGLE_SHEET_NAME у .env"
        )
        return None
    except Exception as e:
        logger.error(f"[GoogleSheets] Помилка підключення до Sheets: {e}")
        return None

def add_ticket(ticket_id, telegram_user_id, telegram_chat_id, telegram_username=None, status="Open"):
    """
    Додає новий запис у Google Sheets з полями:
    Ticket_ID, Telegram_User_ID, Telegram_Chat_ID, Created_At, Status, Telegram_Username, ...
    """
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
    """
    Оновлює статус існуючої заявки у Google Sheets.
    """
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
    """
    Повертає список заявок користувача.
    Якщо не вдалося підключитися до Sheets, повертає порожній список.
    """
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
