import os
from typing import Any

try:  # pragma: no cover
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None  # type: ignore[assignment]


def get_project_id() -> str:
    # Prefer explicit env var, then standard Google env var, then repo's emulator project.
    return (
        os.getenv("FIRESTORE_PROJECT_ID")
        or "demo-monobank"
    )


def get_db() -> Any:
    # Якщо ми в GCP, Client() сам знайде проект.
    # Якщо локально і є FIRESTORE_EMULATOR_HOST, він підключиться до нього.
    if firestore is None:  # pragma: no cover
        raise RuntimeError("google-cloud-firestore is required to use get_db()")
    if os.getenv("FIRESTORE_EMULATOR_HOST"):
        return firestore.Client(project=get_project_id())
    
    return firestore.Client()







