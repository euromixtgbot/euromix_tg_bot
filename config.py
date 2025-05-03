import os
import logging
logger = logging.getLogger(__name__)
from datetime import datetime
from dotenv import load_dotenv

# підвантажити credentials.env
load_dotenv("credentials.env")

# — Telegram —
TOKEN = os.getenv("TOKEN")

# — Jira —
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "TES1")
JIRA_ISSUE_TYPE = os.getenv("JIRA_ISSUE_TYPE", "tgtask")
JIRA_REPORTER_ACCOUNT_ID = os.getenv("JIRA_REPORTER_ACCOUNT_ID")

# SSL для webhook (якщо ви використовуєте webhook)
SSL_CERT_PATH = os.getenv("SSL_CERT_PATH")
SSL_KEY_PATH = os.getenv("SSL_KEY_PATH")
