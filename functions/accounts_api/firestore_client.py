import os

from google.cloud import firestore


def get_project_id() -> str:
    # Prefer explicit env var, then repo's emulator project.
    return os.getenv("FIRESTORE_PROJECT_ID") or "demo-monobank"


def get_db() -> firestore.Client:
    # If local and FIRESTORE_EMULATOR_HOST is set, Client connects to emulator.
    if os.getenv("FIRESTORE_EMULATOR_HOST"):
        return firestore.Client(project=get_project_id())

    return firestore.Client()


