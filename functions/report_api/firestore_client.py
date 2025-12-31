import os

try:  # pragma: no cover
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None  # type: ignore[assignment]


def get_project_id() -> str:
    # Prefer explicit env var, then repo's emulator project.
    return os.getenv("FIRESTORE_PROJECT_ID") or "demo-monobank"


def get_db():
    # If local and FIRESTORE_EMULATOR_HOST is set, Client connects to emulator.
    if firestore is None:  # pragma: no cover
        raise RuntimeError("google-cloud-firestore is required to use get_db()")
    if os.getenv("FIRESTORE_EMULATOR_HOST"):
        return firestore.Client(project=get_project_id())

    return firestore.Client()

