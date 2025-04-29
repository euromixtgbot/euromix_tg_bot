# /root/euromix_tg_bot/google_sheets_service.py

import os
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# Завантаження змінних оточення з .env
load_dotenv()

def connect_to_sheet():
    """Підключення до Google Sheets."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    sheet_name = os.getenv("GOOGLE_SHEET_NAME", "euromix_tickets")

    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    return sheet

def add_ticket(ticket_id, telegram_user_id, telegram_chat_id, telegram_username=None, status="Open"):
    """Додає новий запис у Google Sheets з розширеними полями."""
    sheet = connect_to_sheet()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [
        ticket_id,                # A: Ticket_ID
        telegram_user_id,         # B: Telegram_User_ID
        telegram_chat_id,         # C: Telegram_Chat_ID
        created_at,               # D: Created_At
        status,                   # E: Status
        telegram_username or "",  # F: Telegram_Username
        "",                       # G: User_name_Real (пусте)
        ""                        # H: Account_ID (пусте)
    ]

    sheet.append_row(row)

def update_ticket_status(ticket_id, new_status):
    """Оновлює статус існуючої заявки у Google Sheets."""
    sheet = connect_to_sheet()
    try:
        cell = sheet.find(ticket_id)
        if cell:
            row_number = cell.row
            sheet.update_cell(row_number, 5, new_status)  # 5 = стовпець 'Status'
        else:
            print(f"[GoogleSheets] Ticket ID '{ticket_id}' не знайдено.")
    except Exception as e:
        print(f"[GoogleSheets] Помилка при оновленні статусу: {e}")

def get_user_tickets(telegram_user_id):
    """Отримує всі заявки користувача з таблиці."""
    sheet = connect_to_sheet()
    try:
        records = sheet.get_all_records()
        user_tickets = [
            record for record in records
            if str(record.get('Telegram_User_ID')) == str(telegram_user_id)
        ]
        return user_tickets
    except Exception as e:
        print(f"[GoogleSheets] Помилка при отриманні заявок: {e}")
        return []
