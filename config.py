# config.py
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, 'credentials.env'))

# Debug loaded values
token = os.getenv('JIRA_API_TOKEN') or ''
log.info("CONFIG: TOKEN repr=%r length=%d", os.getenv('TOKEN'), len(os.getenv('TOKEN') or ""))
log.info("CONFIG: JIRA_EMAIL repr=%r length=%d", os.getenv('JIRA_EMAIL'), len(os.getenv('JIRA_EMAIL') or ""))
log.info("CONFIG: JIRA_API_TOKEN repr=%r length=%d", token, len(token))

TOKEN = os.getenv('TOKEN')
JIRA_DOMAIN = os.getenv('JIRA_DOMAIN')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = token
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY')
JIRA_ISSUE_TYPE = os.getenv('JIRA_ISSUE_TYPE')
JIRA_REPORTER_ACCOUNT_ID = os.getenv('JIRA_REPORTER_ACCOUNT_ID')
SSL_CERT_PATH = os.getenv('SSL_CERT_PATH')
SSL_KEY_PATH = os.getenv('SSL_KEY_PATH')