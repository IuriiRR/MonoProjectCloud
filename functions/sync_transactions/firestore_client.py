import os
from google.cloud import firestore

_db = None

def get_db():
    global _db
    if _db is None:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        _db = firestore.Client(project=project_id)
    return _db


