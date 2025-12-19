## Users API (local cloud function)

This repo includes a local Cloud Function-style HTTP API (Python Functions Framework) to CRUD the Firestore `users` collection described in `docs/firestore_schema.md`.

### Prereqs
- Firestore emulator running (via Docker)
- Python 3.11+ recommended

### 1) Start Firestore emulator (Docker)

From repo root:

```bash
docker compose up --build
```

Emulator UI: `http://localhost:4000`  
Firestore emulator: `localhost:8080`

### 2) Install Python deps

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Configure env vars (connect to emulator)

```bash
export FIRESTORE_EMULATOR_HOST=localhost:8080
export FIRESTORE_PROJECT_ID=demo-monobank
```

### 4) Seed users (idempotent)

If `users` collection is empty, this will create 2 sample users:

```bash
python scripts/seed_users.py
```

### 5) Run the cloud function locally

```bash
functions-framework \
  --source functions/users_api \
  --target users_api \
  --port 8081 \
  --debug
```

Base URL: `http://localhost:8081`

### Endpoints

#### List users
- `GET /users`

```bash
curl -s http://localhost:8081/users | jq
```

#### Create user
- `POST /users`

```bash
curl -s -X POST http://localhost:8081/users \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"user_123","username":"Jane","mono_token":null,"active":true}' | jq
```

#### Get user
- `GET /users/{user_id}`

```bash
curl -s http://localhost:8081/users/user_123 | jq
```

#### Update user (partial)
- `PATCH /users/{user_id}` (also supports `PUT`)

```bash
curl -s -X PATCH http://localhost:8081/users/user_123 \
  -H 'Content-Type: application/json' \
  -d '{"active":false}' | jq
```

#### Delete user
- `DELETE /users/{user_id}`

```bash
curl -s -X DELETE http://localhost:8081/users/user_123 | jq
```


