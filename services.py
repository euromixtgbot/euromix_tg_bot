import base64
import io
import httpx
from config import (
    JIRA_DOMAIN,
    JIRA_EMAIL,
    JIRA_API_TOKEN,
    JIRA_PROJECT_KEY,
    JIRA_ISSUE_TYPE,
    JIRA_REPORTER_ACCOUNT_ID,
)

def _jira_auth_header(no_content_type: bool = False) -> dict:
    token = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    h = {"Authorization": f"Basic {token}", "Accept": "application/json"}
    if not no_content_type:
        h["Content-Type"] = "application/json"
    return h

async def create_jira_issue(summary: str, description: str) -> dict:
    """
    Створює задачу в Jira. Повертає словник:
      - status_code
      - json (тіло відповіді, якщо є)
    """
    url = f"{JIRA_DOMAIN}/rest/api/3/issue"
    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description}]
                }]
            },
            "issuetype": {"name": JIRA_ISSUE_TYPE},
            "reporter": {"accountId": JIRA_REPORTER_ACCOUNT_ID}
        }
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            url,
            headers=_jira_auth_header(),
            json=payload,
            timeout=15.0
        )
        try:
            j = r.json()
        except ValueError:
            j = {}
        return {"status_code": r.status_code, "json": j}

async def attach_file_to_jira(issue_id: str, filename: str, content: bytes) -> httpx.Response:
    """
    Прикріплює будь-який файл до Jira-задачі.
    Обгортає content в io.BytesIO, щоб httpx міг .read().
    """
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_id}/attachments"
    headers = _jira_auth_header(no_content_type=True)
    headers["X-Atlassian-Token"] = "no-check"

    file_obj = io.BytesIO(content)
    files = {
        "file": (
            filename,
            file_obj,
            "application/octet-stream"
        )
    }
    async with httpx.AsyncClient() as client:
        return await client.post(url, headers=headers, files=files)

async def add_comment_to_jira(issue_id: str, comment: str) -> httpx.Response:
    """
    Додає текстовий коментар до Jira-задачі.
    """
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_id}/comment"
    body = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [{
                "type": "paragraph",
                "content": [{"type": "text", "text": comment}]
            }]
        }
    }
    async with httpx.AsyncClient() as client:
        return await client.post(
            url,
            headers=_jira_auth_header(),
            json=body
        )

async def get_issue_status(issue_id: str) -> str:
    """
    Повертає назву статусу Jira-задачі.
    """
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_id}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=_jira_auth_header(), timeout=10.0)
        r.raise_for_status()
        return r.json()["fields"]["status"]["name"]
