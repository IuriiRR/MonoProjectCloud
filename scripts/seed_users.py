import os
from datetime import datetime, timezone

from functions.users_api.firestore_client import get_db, get_project_id


def main() -> int:
    emulator = os.getenv("FIRESTORE_EMULATOR_HOST")
    if not emulator:
        print("ERROR: FIRESTORE_EMULATOR_HOST is not set (expected e.g. localhost:8080).")
        return 2

    db = get_db()
    users_ref = db.collection("users")

    existing = list(users_ref.limit(1).stream())
    if existing:
        print("Seed skipped: `users` collection already has documents.")
        return 0

    now = datetime.now(timezone.utc)
    sample = [
        {
            "user_id": "user_001",
            "username": "Alice",
            "mono_token": "replace_me_token_1",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "user_id": "user_002",
            "username": "Bob",
            "mono_token": "replace_me_token_2",
            "active": False,
            "created_at": now,
            "updated_at": now,
        },
    ]

    for u in sample:
        users_ref.document(u["user_id"]).set(u)

    print(
        f"Seeded {len(sample)} users into project={get_project_id()} via emulator={emulator}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


