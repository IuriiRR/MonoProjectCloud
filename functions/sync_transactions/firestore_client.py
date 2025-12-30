import os
try:  # pragma: no cover
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None  # type: ignore[assignment]

_db = None

def get_db():
    global _db
    if _db is None:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if firestore is None:  # pragma: no cover
            raise RuntimeError("google-cloud-firestore is required to use get_db()")
        _db = firestore.Client(project=project_id)
    return _db


