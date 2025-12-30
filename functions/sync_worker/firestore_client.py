import os
try:  # pragma: no cover
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None  # type: ignore[assignment]

_db = None

def get_db():
    global _db
    if _db is None:
        if firestore is None:  # pragma: no cover
            raise RuntimeError("google-cloud-firestore is required to use get_db()")
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        # In local development with emulator, we often don't need project_id 
        # but it's good practice.
        _db = firestore.Client(project=project_id)
    return _db

