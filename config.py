import os
from dotenv import load_dotenv
import logging

# Налаштування логування для config
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Завантажуємо .env із тим самим каталогом, де лежить config.py
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, 'credentials.env'))

# DEBUG: покажемо, що зчиталося
log.info("CONFIG: TOKEN      = %s…", os.getenv("TOKEN")[:10])
log.info("CONFIG: JIRA_EMAIL = %s", os.getenv("JIRA_EMAIL"))
# НЕ виводимо весь токен у лог, лише перевіримо, що він не None/порожній
log.info("CONFIG: JIRA_API_TOKEN exists? %s", bool(os.getenv("JIRA_API_TOKEN")))

# Тепер змінні
TOKEN           = os.getenv('TOKEN')
JIRA_DOMAIN     = os.getenv('JIRA_DOMAIN')
JIRA_EMAIL      = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN  = os.getenv('JIRA_API_TOKEN')
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY') or "TES1"
JIRA_ISSUE_TYPE  = os.getenv('JIRA_ISSUE_TYPE') or "tgtask"
SSL_CERT_PATH   = os.getenv('SSL_CERT_PATH')
SSL_KEY_PATH    = os.getenv('SSL_KEY_PATH')
