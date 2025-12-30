## Auth + registration rule

This project uses **Firebase Auth** (Google / email+password) for authentication, and a separate **Firestore `users` collection** for “registered users”.

### Key rule

Firebase login **does not auto-register** a user in Firestore.

- **Register flow**: Firebase sign-in → create `users/{uid}` doc
- **Login flow**: Firebase sign-in → verify `users/{uid}` doc exists

If the Firestore user doc is missing, the backend returns:
- **HTTP 403**
- `code: "USER_NOT_FOUND"`
- `error: "User not found, please, register first"`

### API authentication

All HTTP APIs (`users_api`, `accounts_api`, `transactions_api`) expect:

- **External calls**: `Authorization: Bearer <firebase_id_token>`
  - The token must be a Firebase **ID token** (not the Monobank token).
  - The token uid must match the `{user_id}` in the URL.

- **Internal calls (sync services)**: `X-Internal-Api-Key: <INTERNAL_API_KEY>`
  - Used by `sync_worker` / `sync_transactions` when calling other APIs.
  - `GET /users` is **internal-only** (used to iterate active users for sync).

### Local development

`docker-compose.yml` is configured with:
- Firestore + Auth emulators
- `FIREBASE_AUTH_EMULATOR_HOST` for API containers
- a default `INTERNAL_API_KEY=dev-internal-key`

Dev-only escape hatch (useful for `curl` / Postman):
- Set `AUTH_MODE=disabled` (or `AUTH_DISABLED=1`) to bypass token verification.


