import requests

from local_server.config import Settings


def run(settings: Settings) -> dict:
    headers = {"X-Internal-Api-Key": settings.internal_api_key}
    resp = requests.post(
        f"{settings.sync_worker_cloud_url}/sync/accounts",
        json={},
        headers=headers,
        timeout=600,
    )
    if not resp.ok:
        raise ValueError(f"Cloud backup sync worker call failed: HTTP {resp.status_code} {resp.text}")
    return resp.json()
