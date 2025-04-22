import base64
import httpx
from io import BytesIO
from config import MAKE_WEBHOOK_CREATE_TASK, JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN

async def create_task_in_make(payload: dict) -> dict:
    """
    Надсилає дані до Make.com для створення задачі.
    Повертає JSON із відповіді або словник з ключем "error".
    """
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(MAKE_WEBHOOK_CREATE_TASK, json=payload, timeout=10.0)
            r.raise_for_status()
            return r.json()
        except httpx.RequestError as exc:
            return {"error": f"HTTP error occurred: {exc}"}
        except httpx.HTTPStatusError as exc:
            return {"error": f"Unexpected status code: {exc.response.status_code}"}

def _jira_auth_header() -> dict:
    """
    Формує заголовок Authorization для Jira REST API.
    """
    token = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Accept": "application/json"
    }

async def attach_file_to_jira(issue_id: str, filename: str, content: bytes) -> httpx.Response:
    """
    Прикріплює файл до вказаної задачі в Jira.
    Обгортає байти у BytesIO, щоб httpx міг їх передати.
    """
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_id}/attachments"
    headers = {**_jira_auth_header(), "X-Atlassian-Token": "no-check"}
    files = {
        "file": (filename, BytesIO(content))
    }
    async with httpx.AsyncClient() as client:
        return await client.post(url, headers=headers, files=files)

async def add_comment_to_jira(issue_id: str, comment: str) -> httpx.Response:
    """
    Додає коментар до вказаної задачі в Jira.
    Повертає Response для перевірки статусу.
    """
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_id}/comment"
    headers = {**_jira_auth_header(), "Content-Type": "application/json"}
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": comment}
                    ]
                }
            ]
        }
    }
    async with httpx.AsyncClient() as client:
        return await client.post(url, headers=headers, json=payload)

async def get_issue_status(issue_id: str) -> str:
    """
    Повертає назву поточного статусу задачі в Jira.
    """
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_id}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=_jira_auth_header(), timeout=10.0)
        r.raise_for_status()
        data = r.json()
        return data["fields"]["status"]["name"]
