import base64
import httpx
from config import (
    JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN,
    JIRA_PROJECT_KEY, JIRA_ISSUE_TYPE, JIRA_REPORTER_ACCOUNT_ID
)

def _jira_auth_header() -> dict:
    token = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

async def create_jira_issue(summary: str, description: str) -> dict:
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
            "reporter": {"id": JIRA_REPORTER_ACCOUNT_ID}
        }
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=_jira_auth_header(), json=payload, timeout=15.0)
        return {"status_code": r.status_code, "json": r.json()}

async def attach_file_to_jira(issue_id: str, filename: str, content: bytes) -> httpx.Response:
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_id}/attachments"
    headers = {**_jira_auth_header(), "X-Atlassian-Token": "no-check"}
    files = {"file": (filename, content)}
    async with httpx.AsyncClient() as client:
        return await client.post(url, headers=headers, files=files)

async def add_comment_to_jira(issue_id: str, comment: str) -> httpx.Response:
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
        return await client.post(url, headers=_jira_auth_header(), json=body)

async def get_issue_status(issue_id: str) -> str:
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_id}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=_jira_auth_header(), timeout=10.0)
        r.raise_for_status()
        return r.json()["fields"]["status"]["name"]
