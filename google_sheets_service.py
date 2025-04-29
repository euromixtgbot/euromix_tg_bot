# /root/euromix_tg_bot/google_sheets_service.py

import os
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# Завантаження змінних оточення
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

def add_ticket(ticket_id, telegram_user_id, telegram_chat_id, status="Open"):
    """Додає новий запис у Google Sheets."""
    sheet = connect_to_sheet()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([ticket_id, telegram_user_id, telegram_chat_id, created_at, status])

def update_ticket_status(ticket_id, new_status):
    """Оновлює статус існуючої заявки у Google Sheets."""
    sheet = connect_to_sheet()
    cell = sheet.find(ticket_id)
    if cell:
        row_number = cell.row
        sheet.update_cell(row_number, 5, new_status)  # 5-й стовпець — статус
    else:
        print(f"Ticket ID {ticket_id} not found.")

def get_user_tickets(telegram_user_id):
    """Отримує всі заявки користувача."""
    sheet = connect_to_sheet()
    records = sheet.get_all_records()
    user_tickets = []
    for record in records:
        if str(record['Telegram_User_ID']) == str(telegram_user_id):
            user_tickets.append(record)
    return user_tickets
