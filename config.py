import os
from dotenv import load_dotenv

# підвантажити .env
load_dotenv('credentials.env')

# Telegram
TOKEN = os.getenv('TOKEN')

# Jira
JIRA_DOMAIN = os.getenv('JIRA_DOMAIN')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY')
JIRA_ISSUE_TYPE = os.getenv('JIRA_ISSUE_TYPE')
JIRA_REPORTER_ACCOUNT_ID = os.getenv('JIRA_REPORTER_ACCOUNT_ID')

# SSL для webhook (якщо використовуєте webhook)
SSL_CERT_PATH = os.getenv('SSL_CERT_PATH')
SSL_KEY_PATH = os.getenv('SSL_KEY_PATH')
