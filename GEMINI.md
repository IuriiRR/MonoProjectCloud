# GEMINI.md

This file provides guidance and instructions to Gemini (Antigravity) when working with code in this repository.

## ❗️ Core Rules (Global Context)

These rules are critical and must be strictly followed during every interaction:
- **Token Efficiency**: Always try to be token efficient, prioritizing task success first.
- **Confidence Check**: Ask questions if you are not confident in your answer.
- **Summary**: Always provide a bulleted summary of your work at the end of your response, unless the user requests a different format.
- **Structure**: Always structure your responses with distinct topics. Highlight important items with emojis (e.g. ❗️, ✅, ❌, 🚩) without overusing them.
- **Result Verification**: If there is a rule or functionality on how to verify your results, ask the user if needed and get confirmation.
- **Proposals & Permissions**: If a new rule, functionality, or document can be added after your changes/plan, propose it first and ask the user for permission.
- **Best Practices**: Stick with the best practices of software engineering and modern LLM approaches in answers and solutions.

---

## ⚡️ Quick Start & Local Commands

**Run everything locally:**
```bash
make run           # Starts all services + Firestore/Auth emulators + frontend
make test          # Runs Python tests + local_server tests + frontend tests
make frontend-dev  # Frontend dev server with Vite (HMR)
```

**Single tests:**
```bash
# Python backend functions
python -m pytest tests/ -v -k "test_name"
python -m pytest functions/users_api/ -v

# Local server
PYTHONPATH=local_server/src:. python -m pytest local_server/tests/ -v -k "test_name"

# Frontend
cd frontend && npm test -- --run -t "test name"
```

---

## 🏗️ Architecture Overview

**CloudApi** is a personal Monobank aggregator with a React UI and Telegram bot. It runs primarily on a Raspberry Pi with passive failover to GCP Cloud Functions.

### Core Components

**Backend (Python 3.11 + Functions Framework)**
- `functions/` — Microservices deployed to GCP Cloud Functions Gen2
  - `users_api` (port 8081) — User registration, linking, reports trigger
  - `accounts_api` (port 8082) — Monobank account sync and balance queries
  - `transactions_api` (port 8083) — Transaction storage and retrieval
  - `sync_worker` (port 8084) — Orchestrates hourly sync cycles
  - `sync_transactions` (port 8085) — Fetches and caches Monobank transactions
  - `report_api` (port 8086) — Generates daily narrative spending reports
  - `telegram_bot` (port 8087) — Polls/webhooks for Telegram notifications and account linking
- `local_server/` — Runs locally on the Raspberry Pi; mirrors GCP production APIs when cloud is unavailable
- `tests/` — Shared integration and unit tests
- `firebase/` — Firestore emulator + Auth emulator (ports 8080, 9099, 4000)

**Frontend (React 18 + TypeScript + Vite)**
- `frontend/` (port 3000) — React app with Tailwind; connects to all backend APIs

### Data Layer
- **Firestore** — Single source of truth (project `demo-monobank` locally; production GCP)
- **Firebase Auth** — Google/email login via emulator locally; Firebase in production
- **Schema** — Documented in `docs/firestore_schema.md`

### Key Deployment Targets
- **GCP Cloud Functions Gen2** — Production backend
- **Firebase Hosting** — Production frontend (built by `./scripts/deploy_frontend.sh`)
- **Raspberry Pi** — `local_server` runs in systemd; offers graceful degradation if cloud is down
- **Terraform** — Infrastructure-as-code in `tf/` (includes API enablement, Cloud Scheduler jobs, Secret Manager)

---

## 🔐 Auth & Registration Rule

🚩 **Critical:** Firebase Auth **does not auto-register**. The flow is:
1. User signs up via Firebase Auth (emulator locally, Firebase in production)
2. Backend verifies auth token; if no user doc in Firestore ➡️ **403 USER_NOT_FOUND**
3. User must register explicitly (via `/register` endpoint or Telegram `/start`)

See `docs/auth.md` for details.

---

## 📦 Firestore & Emulator

**Locally:**
- Firestore Emulator (port 8080), Auth Emulator (port 9099), UI on port 4000
- Data persists in `.emulator-data/` (checked into repo; reset with `docker compose down -v`)

**In code:**
```python
import os
# Emulator vars set by docker-compose
if os.getenv("FIRESTORE_EMULATOR_HOST"):
    from google.cloud import firestore
    db = firestore.Client(project=os.getenv("FIRESTORE_PROJECT_ID"))
```

---

## 🧪 Testing Strategy

- **Backend unit tests** in `tests/` and function subdirectories (pytest)
- **Local server tests** in `local_server/tests/` (pytest, PYTHONPATH setup required)
- **Frontend tests** in `frontend/` (Vitest + React Testing Library)
- **No mocking of Firestore** — tests hit the emulator
- **Integration focus** — tests exercise real auth, Firestore, and API boundaries

---

## 🔑 Key Files & Patterns

- **Service entry points** — Each function's `main.py` uses `@functions_framework.http` decorator
- **Shared auth** — `functions/shared_auth.py` validates Firebase tokens
- **Shared Firestore ops** — `functions/shared_firestore.py` handles DB access
- **Flask responses** — All APIs return JSON wrapped in `make_response()` with CORS headers
- **Env vars & secrets** — `.env` file (not committed) for local tokens; GCP Secret Manager in production
- **Type hints** — All Python functions should have type annotations
- **Frontend env vars** — Prefixed `VITE_*` in docker-compose and `.env.local` for local React dev

---

## 🤖 Telegram Integration

**Local development (polling mode)**
- Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_BOT_USERNAME` to `.env`
- `make run` automatically starts polling; no webhook tunnel needed
- Emulator auth rejection: local dev uses callback buttons (webhooks can't target localhost)

**Production (webhook mode)**
- Requires public HTTPS URL; configured in Secret Manager
- Cloud Scheduler triggers the bot once per day to push reports

---

## 🛠️ Common Tasks & Workflows

**Add a new backend function**
1. Create `functions/new_service/` with `main.py`, `requirements.txt`, `Dockerfile.new_service`
2. Add service to `docker-compose.yml`
3. Wire up dependencies (Firestore, shared auth) following existing patterns
4. Add tests in `tests/` or `functions/new_service/test_*.py`

**Modify Firestore schema**
1. Update `docs/firestore_schema.md`
2. Update `.emulator-data/` (or reset with `docker compose down -v`)
3. Check `firestore.rules` (security rules in GCP)

**Deploy to GCP**
1. `cd tf && terraform init && terraform apply` (requires `terraform.tfvars` and GCP credentials)
2. Push frontend with `./scripts/deploy_frontend.sh`
3. Monitor via Sentry (configured in function env)

---

## 📚 References & Documentation

- `docs/arc42.md` — Full architecture documentation (goals, constraints, building blocks, deployment, ADRs)
- `docs/firestore_schema.md` — Data model
- `docs/auth.md` — Auth flow and registration
- `README.md` — Local dev quick start and deployment checklist
