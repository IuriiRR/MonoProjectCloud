import os

from google.cloud import firestore


def get_project_id() -> str:
    # Prefer explicit env var, then standard Google env var, then repo's emulator project.
    return (
        os.getenv("FIRESTORE_PROJECT_ID")
        or "demo-monobank"
    )


def get_db() -> firestore.Client:
    # Якщо ми в GCP, Client() сам знайде проект.
    # Якщо локально і є FIRESTORE_EMULATOR_HOST, він підключиться до нього.
    if os.getenv("FIRESTORE_EMULATOR_HOST"):
        return firestore.Client(project=get_project_id())
    
    return firestore.Client()






