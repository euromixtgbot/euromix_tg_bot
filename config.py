# 1) Створюємо config.py, який зчитує змінні з credentials.env
import os
from dotenv import load_dotenv

# Підвантажуємо змінні оточення з файлу credentials.env
load_dotenv('credentials.env')

# Telegram
TOKEN                = os.getenv('TOKEN')
WEBHOOK_URL          = os.getenv('WEBHOOK_URL')

# Make.com
MAKE_WEBHOOK_CREATE_TASK = os.getenv('MAKE_WEBHOOK_CREATE_TASK')

# Jira
JIRA_DOMAIN          = os.getenv('JIRA_DOMAIN')
JIRA_EMAIL           = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN       = os.getenv('JIRA_API_TOKEN')

# SSL для webhook
SSL_CERT_PATH        = os.getenv('SSL_CERT_PATH')
SSL_KEY_PATH         = os.getenv('SSL_KEY_PATH')
