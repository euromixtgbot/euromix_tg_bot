# services.py
import base64
import httpx
from io import BytesIO
from config import (
    JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN,
    JIRA_PROJECT_KEY, JIRA_ISSUE_TYPE,
)

def _jira_headers(json=True):
    token = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    h = {
        "Authorization": f"Basic {token}",
        "Accept": "application/json"
    }
    if json:
        h["Content-Type"] = "application/json"
    return h

async def create_issue_in_jira(data: dict) -> dict:
    """
    Створює issue і повертає { "key": "<ISSUE-KEY>" } або { "error": ... }.
    data має містити:
      - division, department, service, full_name, description
    """
    url = f"{JIRA_DOMAIN}/rest/api/3/issue"
    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "issuetype": {"name": JIRA_ISSUE_TYPE},
            "summary": f"{data['division']} / {data['department']} / {data['service']} — {data['full_name']}",
            "description": data["description"]
        }
    }
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, headers=_jira_headers(), json=payload, timeout=15.0)
            r.raise_for_status()
            return {"key": r.json()["key"]}
        except httpx.HTTPStatusError as e:
            return {"error": f"Jira create failed {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"error": str(e)}

async def attach_file_to_jira(issue_key: str, filename: str, content: bytes) -> httpx.Response:
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_key}/attachments"
    headers = {**_jira_headers(json=False), "X-Atlassian-Token": "no-check"}
    files = {"file": (filename, BytesIO(content))}
    async with httpx.AsyncClient() as client:
        return await client.post(url, headers=headers, files=files)

async def add_comment_to_jira(issue_key: str, comment: str) -> httpx.Response:
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_key}/comment"
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}]
        }
    }
    async with httpx.AsyncClient() as client:
        return await client.post(url, headers=_jira_headers(), json=payload)

async def get_issue_status(issue_key: str) -> str:
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_key}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=_jira_headers(), timeout=10.0)
        r.raise_for_status()
        return r.json()["fields"]["status"]["name"]
