import requests
from local_server.config import Settings


def run(settings: Settings) -> dict:
    headers = {"X-Internal-Api-Key": settings.internal_api_key}
    resp = requests.post(
        f"{settings.users_api_url}/telegram/reports/daily/send_enabled",
        json={},
        headers=headers,
        timeout=120,
    )
    if not resp.ok:
        raise ValueError(f"Daily reports call failed: HTTP {resp.status_code} {resp.text}")
    return resp.json()
