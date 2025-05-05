# services.py
import logging
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

logger = logging.getLogger(__name__)


def _jira_auth_header() -> dict:
    """
    Повертає заголовки для Basic Auth у Jira API.
    """
    token = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


async def create_jira_issue(payload: dict) -> str:
    """
    Створює задачу в Jira.
    Вхідний payload має містити ключі:
      - summary: str
      - description: str
    Повертає рядок-ключ створеної задачі (наприклад "TES1-123").
    """
    url = f"{JIRA_DOMAIN}/rest/api/3/issue"
    jira_body = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": payload["summary"],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": payload["description"]}]
                }]
            },
            "issuetype": {"name": JIRA_ISSUE_TYPE},
            "reporter": {"accountId": JIRA_REPORTER_ACCOUNT_ID},
        }
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(
            url,
            headers=_jira_auth_header(),
            json=jira_body,
            timeout=15.0
        )
        r.raise_for_status()
        data = r.json()
        issue_key = data.get("key")
        if not issue_key:
            raise RuntimeError(f"Jira did not return issue key: {data!r}")
        return issue_key


async def attach_file_to_jira(issue_id: str, filename: str, content: bytes) -> httpx.Response:
    """
    Прикріплює файл до задачі в Jira.
    """
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_id}/attachments"
    headers = _jira_auth_header().copy()
    headers.pop("Content-Type", None)
    headers["X-Atlassian-Token"] = "no-check"

    file_obj = io.BytesIO(content)
    files = {
        "file": (filename, file_obj, "application/octet-stream")
    }

    async with httpx.AsyncClient() as client:
        return await client.post(url, headers=headers, files=files)


async def add_comment_to_jira(issue_id: str, comment: str) -> httpx.Response:
    """
    Додає текстовий коментар до задачі в Jira.
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
    Повертає поточний статус задачі в Jira.
    """
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_id}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=_jira_auth_header(), timeout=10.0)
        r.raise_for_status()
        data = r.json()
        return data["fields"]["status"]["name"]


async def get_issue_summary(issue_id: str) -> str:
    """
    Повертає поле summary із Jira.
    """
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_id}?fields=summary"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=_jira_auth_header(), timeout=10.0)
        r.raise_for_status()
        return r.json()["fields"]["summary"]
