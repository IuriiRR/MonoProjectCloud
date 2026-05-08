# CloudApi — arc42 Architecture Documentation

> Single-document arc42 description of CloudApi: a personal Monobank
> aggregator with a React web UI and a Telegram bot, running primarily on a
> Raspberry Pi with passive failover to GCP Cloud Functions. Cloud Firestore
> is the shared data plane.

## Table of contents

1. [Introduction and Goals](#1-introduction-and-goals)
2. [Architecture Constraints](#2-architecture-constraints)
3. [System Scope and Context](#3-system-scope-and-context)
4. [Solution Strategy](#4-solution-strategy)
5. [Building Block View](#5-building-block-view)
6. [Runtime View](#6-runtime-view)
7. [Deployment View](#7-deployment-view)
8. [Cross-cutting Concepts](#8-cross-cutting-concepts)
9. [Architecture Decisions](#9-architecture-decisions)
10. [Quality Requirements](#10-quality-requirements)
11. [Risks and Technical Debt](#11-risks-and-technical-debt)
12. [Glossary](#12-glossary)

---

## 1. Introduction and Goals

### 1.1 Purpose

CloudApi aggregates a single household's [Monobank](https://api.monobank.ua/)
accounts (cards and jars) and transactions, enriches them with a daily
narrative report, and delivers everything through two channels:

- a **React + Firebase web UI** for browsing balances, charts and reports;
- a **Telegram bot** for daily push reports and account linking.

### 1.2 Top quality goals (priority order)

| # | Quality       | Motivation                                                                                          |
|---|---------------|-----------------------------------------------------------------------------------------------------|
| 1 | Low cost      | Personal project; must fit GCP / Firebase free tiers when the Pi is offline.                        |
| 2 | Durability    | Financial data; loss is unacceptable. Firestore is the single source of truth.                     |
| 3 | Availability  | Hourly sync and daily report must continue even if the Raspberry Pi dies (cloud failover).         |
| 4 | Operability   | Single operator; deploy via Terraform + one shell script; observable via Sentry.                   |

### 1.3 Stakeholders

| Stakeholder           | Interest                                                                       |
|-----------------------|--------------------------------------------------------------------------------|
| Owner / operator      | Daily insight into spending; cheap operation; minimal manual maintenance.      |
| Family member         | Read-only access to a relative's accounts and transactions.                    |
| Monobank API          | External provider of accounts and statements; rate-limited, third-party.       |
| Telegram users        | Recipients of the daily report; trigger account linking via deep link.         |

---

## 2. Architecture Constraints

### 2.1 Technical constraints

- **Language / runtime:** Python 3.11, [Functions Framework](https://github.com/GoogleCloudPlatform/functions-framework-python) for every backend service; React 18 + TypeScript + Vite + Tailwind for the frontend.
- **Cloud platform:** Google Cloud + Firebase. Cloud Functions Gen2, Cloud Firestore, Firebase Auth, Firebase Hosting, Cloud Scheduler, Secret Manager.
- **Data store:** Cloud Firestore only. No relational database.
- **Edge runtime:** Raspberry Pi (single-board ARM64), Linux, Docker or systemd.
- **IaC:** Terraform for everything in GCP (`tf/main.tf`, `tf/variables.tf`).

### 2.2 Organisational constraints

- Single-developer project; no SLA, no on-call rota.
- Deploy via `terraform apply` for backend, `scripts/deploy_frontend.sh` for the SPA.
- Cost target: stay inside the GCP / Firebase free tier under normal household load.

### 2.3 Conventions

- Each backend service is a self-contained folder under `functions/<service>/` with its own `main.py`, `auth.py`, `firestore_client.py`, `requirements.txt`. Code duplication is accepted as the price for deploy isolation.
- Service-to-service calls use header `X-Internal-Api-Key` (env `INTERNAL_API_KEY`).
- User-facing calls use `Authorization: Bearer <Firebase ID token>`.
- HTTP routing is done by manual `request.path` matching inside each function (no Flask blueprints).
- All schedulable HTTP entrypoints accept `POST` with empty `{}` body.

---

## 3. System Scope and Context

### 3.1 Business context

```mermaid
flowchart LR
  WebUser[Owner / family<br/>Web browser]
  TgUser[Telegram user]
  Monobank[Monobank API]
  Telegram[Telegram Bot API]
  Gemini[Google Gemini API]
  FirebaseAuth[Firebase Auth]
  Firestore[Cloud Firestore]
  Scheduler[Cloud Scheduler]
  Sentry[Sentry]

  WebUser -->|HTTPS, ID token| CloudApi
  TgUser -->|messages| Telegram
  Telegram -->|polling or webhook| CloudApi
  CloudApi -->|sendMessage| Telegram
  CloudApi -->|client-info, statement| Monobank
  CloudApi -->|generateContent| Gemini
  CloudApi -->|verify ID token| FirebaseAuth
  CloudApi -->|read/write| Firestore
  Scheduler -->|HTTP cron| CloudApi
  CloudApi -->|errors| Sentry
```

### 3.2 External interfaces

| Partner            | Direction | Protocol / endpoint                                                                  | Purpose                                          |
|--------------------|-----------|--------------------------------------------------------------------------------------|--------------------------------------------------|
| Monobank           | out       | `GET https://api.monobank.ua/personal/client-info`, `.../statement/{acc}/{from}/{to}` | Fetch accounts and transactions (`X-Token`).     |
| Telegram Bot API   | both      | `getUpdates`, `setWebhook`, `deleteWebhook`, `sendMessage`, `answerCallbackQuery`     | Bot polling (Pi) or webhook (cloud) and replies. |
| Firebase Auth      | out       | OIDC / JWKs                                                                          | Verify user ID tokens.                            |
| Cloud Firestore    | both      | gRPC / REST                                                                          | Persist users, accounts, transactions, cache.    |
| Cloud Scheduler    | in        | HTTP cron with `X-Internal-Api-Key`                                                  | Hourly sync, daily report, Pi failover trigger.  |
| Google Gemini      | out       | `google-genai` SDK, model `gemini-2.5-flash-lite`                                    | Optional LLM-enhanced daily report narrative.    |
| Sentry             | out       | DSN                                                                                  | Error reporting (optional).                      |

---

## 4. Solution Strategy

| Concern                       | Decision                                                                                                                                |
|-------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| Decomposition                 | One service per bounded context: `users`, `accounts`, `transactions`, `report`, `sync_worker`, `sync_transactions`, `telegram_bot`.     |
| Same code, two runtimes       | Each service ships as a Cloud Function Gen2 **and** as a `functions-framework` process on the Pi. Source under `functions/<svc>/` is shared. |
| Primary placement             | Pi runs all services on `127.0.0.1:8081-8086` plus an APScheduler-driven scheduler. Cloud Functions are kept as passive failover.        |
| Failover                      | Dead-man's-switch: `rpi_unblocker` Cloud Scheduler job is continually pushed forward by the Pi heartbeat. If heartbeat stops, the job fires and re-enables cloud schedulers + Telegram webhook. |
| Persistence                   | Cloud Firestore as the only durable store. Hierarchical, per-user data model. Same DB for Pi and cloud paths.                            |
| Identity                      | Firebase Auth for end users (Google + email/password). Internal API key for service-to-service.                                          |
| Frontend                      | React SPA on Firebase Hosting; Firebase JS SDK for auth; direct `fetch` to four backend base URLs configured at build time.              |
| LLM                           | Optional: `report_api` calls Gemini when `GEMINI_API_KEY` is set; otherwise renders a deterministic markdown report.                     |

---

## 5. Building Block View

### 5.1 Whitebox — Level 1

```mermaid
flowchart LR
  subgraph clients [Clients]
    Browser[Browser SPA]
    TgClient[Telegram client]
  end

  subgraph backend [Backend services]
    UsersApi[users_api]
    AccountsApi[accounts_api]
    TransactionsApi[transactions_api]
    ReportApi[report_api]
    SyncWorker[sync_worker]
    SyncTx[sync_transactions]
    TelegramBot[telegram_bot]
  end

  subgraph edge [Raspberry Pi edge]
    PiScheduler[local_server.scheduler]
    Polling[telegram polling]
  end

  Firestore[(Cloud Firestore)]
  Monobank[Monobank API]
  Gemini[Gemini API]
  Telegram[Telegram Bot API]
  CloudSched[Cloud Scheduler]

  Browser --> UsersApi
  Browser --> AccountsApi
  Browser --> TransactionsApi
  Browser --> ReportApi

  TgClient --> Telegram
  Telegram --> TelegramBot
  Telegram --> Polling
  Polling --> UsersApi
  TelegramBot --> UsersApi

  PiScheduler --> SyncWorker
  PiScheduler --> UsersApi
  CloudSched --> UsersApi
  CloudSched --> SyncWorker

  SyncWorker --> UsersApi
  SyncWorker --> AccountsApi
  SyncWorker --> SyncTx
  SyncWorker --> Monobank

  SyncTx --> AccountsApi
  SyncTx --> TransactionsApi
  SyncTx --> Monobank

  UsersApi --> ReportApi
  UsersApi --> Telegram
  UsersApi --> CloudSched
  ReportApi --> Gemini

  UsersApi --> Firestore
  AccountsApi --> Firestore
  TransactionsApi --> Firestore
  ReportApi --> Firestore
```

### 5.2 Building blocks — Level 2

| Block               | Responsibility                                                                                          | Interface (in)                                                                                    | Collaborators (out)                                  |
|---------------------|---------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|------------------------------------------------------|
| `users_api`         | User CRUD; family graph; Telegram link state; daily-report orchestration; cloud-scheduler control loop. | `GET/POST/PUT/PATCH/DELETE /users[/...]`, `/users/{id}/telegram/...`, `/users/{id}/family/...`, `/internal/scheduler/{unblock,cede}`, `/telegram/connect`, `/telegram/reports/daily/send_enabled` | Firestore, Firebase Auth, `report_api`, Telegram API, Cloud Scheduler |
| `accounts_api`      | CRUD for accounts under `users/{uid}/accounts`. Family read-only.                                       | `GET/POST/PUT /users/{uid}/accounts[/{id}]`                                                       | Firestore, Firebase Auth                              |
| `transactions_api`  | CRUD plus aggregations: balance chart, monthly summary; collection-group queries.                       | `GET/POST/PUT /users/{uid}/accounts/{aid}/transactions[/{tid}]`, `/users/{uid}/transactions`, `/users/{uid}/charts/...`, internal `/transactions` | Firestore, Firebase Auth                              |
| `report_api`        | Compose daily report; deterministic markdown plus optional LLM rewrite; cache in Firestore.             | `GET /users/{uid}/reports/daily?date=&tz=&llm=`                                                   | Firestore, Gemini (optional)                          |
| `sync_worker`       | Hourly fan-out: list users, fetch Monobank `client-info`, push accounts, kick `sync_transactions`.       | `POST /sync/accounts`                                                                             | `users_api`, `accounts_api`, `sync_transactions`, Monobank |
| `sync_transactions` | Pull Monobank statements per account, batch-write transactions.                                          | `POST /sync/transactions`                                                                         | `accounts_api`, `transactions_api`, Monobank          |
| `telegram_bot`      | Webhook handler in cloud; routes `/start <token>` connects through `users_api`.                          | `GET/POST /` (Telegram update payload)                                                            | `users_api`, Telegram API                             |
| `frontend`          | React SPA: login/register, dashboard, charts, settings, report.                                          | Firebase Hosting + browser fetch                                                                  | Firebase Auth, four backend services                  |
| `local_server.scheduler` | APScheduler-driven cron on Pi; runs heartbeat + control loop; serves `/healthz`.                    | `GET /healthz` on `127.0.0.1:9090`                                                                | All local services, Cloud Scheduler                   |

References:
[functions/users_api/main.py](../functions/users_api/main.py),
[functions/accounts_api/main.py](../functions/accounts_api/main.py),
[functions/transactions_api/main.py](../functions/transactions_api/main.py),
[functions/report_api/main.py](../functions/report_api/main.py),
[functions/sync_worker/main.py](../functions/sync_worker/main.py),
[functions/sync_transactions/main.py](../functions/sync_transactions/main.py),
[functions/telegram_bot/main.py](../functions/telegram_bot/main.py),
[frontend/src/App.tsx](../frontend/src/App.tsx),
[local_server/src/local_server/scheduler.py](../local_server/src/local_server/scheduler.py).

---

## 6. Runtime View

### 6.1 User login + registration gate

```mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant SPA as Frontend SPA
  participant FB as Firebase Auth
  participant UA as users_api
  participant FS as Firestore

  U->>SPA: Open /login
  SPA->>FB: signInWithPopup(Google)
  FB-->>SPA: Firebase user + ID token
  SPA->>UA: GET /users/{uid} (Bearer token)
  UA->>FB: Verify ID token (JWKs)
  UA->>FS: Get users/{uid}
  alt user document exists
    UA-->>SPA: 200 user
    SPA->>U: Redirect to dashboard
  else missing
    UA-->>SPA: 403 USER_NOT_FOUND
    SPA->>U: Redirect to /register
    U->>SPA: Submit registration
    SPA->>UA: POST /users
    UA->>FS: Create users/{uid}
    UA-->>SPA: 201
  end
```

### 6.2 Hourly Monobank sync (Pi primary)

```mermaid
sequenceDiagram
  autonumber
  participant Cron as APScheduler (Pi)
  participant SW as sync_worker
  participant UA as users_api
  participant Mono as Monobank
  participant AA as accounts_api
  participant ST as sync_transactions
  participant TA as transactions_api

  Cron->>SW: POST /sync/accounts (X-Internal-Api-Key)
  SW->>UA: GET /users (internal)
  UA-->>SW: [users with mono_token]
  loop for each active user
    SW->>Mono: GET /personal/client-info (X-Token)
    Mono-->>SW: accounts
    SW->>AA: PUT /users/{uid}/accounts (batch)
    SW-)ST: POST /sync/transactions (async thread)
    ST->>Mono: GET /personal/statement/{acc}/{from}/{to}
    Mono-->>ST: transactions
    ST->>TA: PUT /users/{uid}/accounts/{acc}/transactions (batch)
  end
```

### 6.3 Daily Telegram report

```mermaid
sequenceDiagram
  autonumber
  participant Cron as APScheduler (Pi)
  participant UA as users_api
  participant RA as report_api
  participant FS as Firestore
  participant Gem as Gemini
  participant TG as Telegram

  Cron->>UA: POST /telegram/reports/daily/send_enabled
  UA->>FS: Query users where daily_report=true
  loop for each user
    UA->>RA: GET /users/{uid}/reports/daily?tz=...
    RA->>FS: Read accounts + transactions + cache
    opt GEMINI_API_KEY set
      RA->>Gem: generateContent(prompt)
      Gem-->>RA: narrative
    end
    RA-->>UA: markdown report
    UA->>TG: sendMessage(chat_id, markdown)
  end
```

### 6.4 Telegram account connect

```mermaid
sequenceDiagram
  autonumber
  participant U as Telegram user
  participant TG as Telegram
  participant Bot as telegram_bot (or polling)
  participant UA as users_api
  participant FS as Firestore

  U->>TG: /start <connect_token>
  TG->>Bot: update payload
  Bot->>UA: GET /telegram/connect?token=...&telegram_id=...
  UA->>FS: Validate token, set users/{uid}.telegram_id
  UA-->>Bot: HTML success
  Bot->>TG: sendMessage("Connected.")
```

### 6.5 Pi failover (dead-man's-switch)

```mermaid
sequenceDiagram
  autonumber
  participant Pi as local_server.control_loop
  participant CS as Cloud Scheduler
  participant UA as users_api (cloud)
  participant TG as Telegram

  Note over Pi,CS: Normal operation
  loop every HEARTBEAT_INTERVAL_SEC
    Pi->>CS: update_job(rpi_unblocker, schedule_time = now + UNBLOCKER_LEAD_SEC)
  end

  Note over Pi: Pi dies / loses connectivity
  CS->>UA: POST /internal/scheduler/unblock (X-Internal-Api-Key)
  UA->>CS: Resume sync_worker_hourly + daily_reports_daily
  UA->>CS: Run them now
  UA->>TG: setWebhook(cloud telegram_bot URL)
  UA->>CS: Pause rpi_unblocker (until Pi cedes again)
```

References:
[local_server/src/local_server/control_loop.py](../local_server/src/local_server/control_loop.py),
[local_server/src/local_server/cloud_scheduler.py](../local_server/src/local_server/cloud_scheduler.py),
[functions/users_api/main.py](../functions/users_api/main.py).

---

## 7. Deployment View

```mermaid
flowchart TB
  subgraph pi [Raspberry Pi - PRIMARY]
    direction TB
    subgraph piServices [functions-framework processes 127.0.0.1]
      pUA[users_api :8081]
      pAA[accounts_api :8082]
      pTA[transactions_api :8083]
      pSW[sync_worker :8084]
      pST[sync_transactions :8085]
      pRA[report_api :8086]
    end
    pSched[cloudapi-local<br/>scheduler + heartbeat<br/>:9090]
    pTel[cloudapi-telegram<br/>polling]
  end

  subgraph gcp [GCP - FAILOVER and DATA PLANE]
    direction TB
    subgraph cf [Cloud Functions Gen2]
      cUA[users_api]
      cAA[accounts_api]
      cTA[transactions_api]
      cRA[report_api]
      cSW[sync_worker]
      cST[sync_transactions]
      cTB[telegram_bot]
    end
    fs[(Cloud Firestore)]
    fa[Firebase Auth]
    cSchedHourly[sync_worker_hourly<br/>PAUSED]
    cSchedDaily[daily_reports_daily<br/>PAUSED]
    cSchedUnblock[rpi_unblocker<br/>ACTIVE]
    sm[Secret Manager<br/>gemini-api-key]
    gcs[GCS bucket<br/>function sources]
  end

  subgraph host [Firebase Hosting]
    spa[frontend/dist SPA]
  end

  Browser[User browser] --> spa
  spa --> fa
  spa -->|cloud or pi URL| cUA
  spa --> cAA
  spa --> cTA
  spa --> cRA

  pSched --> piServices
  pSched -->|push_job_forward| cSchedUnblock
  pTel --> pUA

  cSchedUnblock --> cUA
  cSchedHourly -.failover.-> cSW
  cSchedDaily -.failover.-> cUA

  piServices --> fs
  piServices --> fa
  cf --> fs
  cf --> fa
  cRA --> sm
```

### 7.1 Nodes

| Node               | Provisioned by                                        | Contents                                                                                                                                  |
|--------------------|-------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| Raspberry Pi       | Manual + `local_server/docker-compose.yml` or systemd | Six functions-framework HTTP services (8081-8086), `cloudapi-local` scheduler (9090), `cloudapi-telegram` polling worker.                 |
| GCP project        | Terraform (`tf/main.tf`)                              | 7 Cloud Functions Gen2, Firestore, Firebase Auth, 3 Cloud Scheduler jobs, Secret Manager secret, GCS source bucket, IAM, composite indexes. |
| Firebase Hosting   | `scripts/deploy_frontend.sh`                          | `frontend/dist` SPA at `${project_id}.web.app` with SPA rewrite to `/index.html`.                                                         |

### 7.2 Network and security

- **End users → backend:** HTTPS with `Authorization: Bearer <Firebase ID token>`. Backend verifies via Firebase JWKs.
- **Service ↔ service:** HTTP with header `X-Internal-Api-Key: ${INTERNAL_API_KEY}`.
- **Cloud Scheduler → Cloud Functions:** same internal API key in HTTP headers.
- **Pi internal:** services bind to `127.0.0.1` only; only the SPA (and curl on the host) can reach them. The Pi's outbound traffic reaches Firestore, Telegram, Monobank, Gemini and Cloud Scheduler.
- **Cloud Functions invoker:** currently `roles/run.invoker` is granted to `allUsers`; protection is at the application layer (Firebase token / internal key). See risk in §11.
- **Secrets:**
  - Cloud: Secret Manager (`gemini-api-key`); other secrets injected as Terraform variables / env.
  - Pi: `local_server/secrets/` mounted at `/etc/cloudapi/local_server.env`; `GOOGLE_APPLICATION_CREDENTIALS` for Firestore.

References:
[tf/main.tf](../tf/main.tf),
[local_server/docker-compose.yml](../local_server/docker-compose.yml),
[local_server/systemd/cloudapi-telegram.service](../local_server/systemd/cloudapi-telegram.service),
[firebase.json](../firebase.json),
[scripts/deploy_frontend.sh](../scripts/deploy_frontend.sh).

---

## 8. Cross-cutting Concepts

### 8.1 Authentication and authorization

- **Identity**: Firebase Auth (Google or email/password). The frontend uses the Firebase JS SDK; in dev it points at the Auth Emulator.
- **Registration gate**: a Firebase user is considered "registered" only when `users/{uid}` exists in Firestore. Backend returns `403 USER_NOT_FOUND` otherwise (`docs/auth.md`).
- **End-user authorization**: each `/users/{uid}/...` route requires the token's `uid` to match the path. Family members get **read-only** access to a relative's accounts and transactions (`accounts_api`, `transactions_api`).
- **Service-to-service**: header `X-Internal-Api-Key`. `users_api` exposes `/users` listing only to internal callers, used by `sync_worker`.
- **Local dev escape hatches**: `AUTH_DISABLED=1` / `AUTH_MODE=disabled` for curl/Postman.

### 8.2 Data model

- **Firestore hierarchy** (`docs/firestore_schema.md`):
  - `users/{uid}` — profile, `mono_token`, `active`, `daily_report`, `telegram_id`, family graph.
  - `users/{uid}/accounts/{account_id}` — Monobank cards and jars; flags `is_budget`, `invested`.
  - `users/{uid}/accounts/{account_id}/transactions/{transaction_id}` — Monobank statement entries; document ID = Monobank ID (idempotency).
  - `users/{uid}/family_requests/{requester_id}`, `users/{uid}/reports_cache/...`.
  - `invitations/{code}` — invite codes, with **TTL** on `expires_at` (`google_firestore_field.invitations_expires_at_ttl`).
- **Indexes** (`tf/main.tf`): collection-group composite indexes on `transactions(user_id, time)` ASC and DESC, plus single-field indexes on `transactions.time`. Required by collection-group queries in `transactions_api` and `report_api`.

### 8.3 Synchronisation and idempotency

- Monobank IDs become Firestore document IDs for accounts and transactions, so re-runs of `sync_transactions` are idempotent.
- `sync_worker` triggers `sync_transactions` per user in a fire-and-forget thread to keep the worker call short.
- Monobank rate-limit (~once per minute per token) is the practical upper bound on sync frequency.

### 8.4 Observability

- **Sentry**: every backend service has an optional `_init_sentry()` reading `SENTRY_DSN` and `DISABLE_SENTRY`.
- **Health**: Pi scheduler exposes `GET /healthz` (`local_server/src/local_server/health.py`) reporting last heartbeat and last error.
- **Logs**: `loguru` in sync services; Cloud Logging in GCP via Functions runtime.

### 8.5 Configuration

| Surface           | Mechanism                                                                                          |
|-------------------|----------------------------------------------------------------------------------------------------|
| Cloud Functions   | `environment_variables` block in `tf/main.tf` per function. Secrets via `secret_environment_variables`. |
| Pi services       | `/etc/cloudapi/local_server.env` (systemd) or `local_server/secrets/` mount (compose).               |
| Frontend          | `VITE_*` build-time env, baked into `frontend/dist`.                                                |

### 8.6 CORS

Each backend service handles `OPTIONS *` manually, returning permissive CORS headers. There is no shared middleware.

### 8.7 Scheduling model

Three Cloud Scheduler jobs are defined; only one is normally active:

| Job                         | Default state | Target                                                        | Owner of trigger when active           |
|-----------------------------|--------------:|---------------------------------------------------------------|----------------------------------------|
| `sync_worker_hourly`        | paused        | cloud `sync_worker /sync/accounts`                            | Resumed only on Pi failure.            |
| `daily_reports_daily`       | paused        | cloud `users_api /telegram/reports/daily/send_enabled`        | Resumed only on Pi failure.            |
| `rpi_unblocker`             | **active**    | cloud `users_api /internal/scheduler/unblock`                 | Cron itself (after heartbeat stops).   |

When the Pi is healthy, **APScheduler on the Pi** drives the same two HTTP routes against `127.0.0.1` services, while `local_server.control_loop` keeps pushing `rpi_unblocker.schedule_time` into the future.

### 8.8 AI / LLM

`report_api/llm_team.py` uses the `google-genai` SDK with `gemini-2.5-flash-lite` when `GEMINI_API_KEY` is provided through Secret Manager. Without a key, `report_api` falls back to deterministic markdown generated by `matching.py` + `render.py`.

---

## 9. Architecture Decisions

### ADR-1 — Cloud Functions Gen2 over Cloud Run

**Context:** need cheap, idle-zero, per-service deploys.
**Decision:** use Cloud Functions Gen2 for every backend service.
**Consequences:** simple Terraform via `google_cloudfunctions2_function`; per-function source upload through GCS bucket; trade-off is colder starts than always-on Cloud Run.

### ADR-2 — Firestore over relational DB

**Context:** hierarchical per-user data; want free tier.
**Decision:** Firestore as the only data store; documents shaped around the `users/{uid}/accounts/{aid}/transactions/{tid}` tree.
**Consequences:** cheap reads, easy security model along the hierarchy, but reporting needs explicit composite indexes and collection-group queries.

### ADR-3 — Pi-primary, cloud-failover

**Context:** running everything in GCP would either incur cost or require always-warm instances; the operator already has a Pi.
**Decision:** make the Pi the active runtime; deploy the same code to Cloud Functions and keep their schedulers paused, governed by a dead-man's-switch.
**Consequences:** zero ongoing cloud cost for compute when the Pi is up; hands-off failover; trade-off: the failover path is a separate code path (Telegram polling vs webhook) that must be tested.

### ADR-4 — `X-Internal-Api-Key` over IAM-authenticated invoker

**Context:** simplest cross-service auth.
**Decision:** ship a static internal API key as a Terraform variable, allow `allUsers` invoker on Cloud Functions, and gate at app layer.
**Consequences:** no need to manage GCP service-account audiences; one secret to rotate; trade-off: a leaked key bypasses all internal endpoints. Tightening to IAM is a follow-up.

### ADR-5 — Telegram polling on Pi, webhook in cloud

**Context:** Telegram requires a public HTTPS URL for webhooks; the Pi has none by default; localhost rejected for inline-keyboard URLs.
**Decision:** run a polling worker on the Pi; deploy `telegram_bot` Cloud Function as the webhook target, switched on only by failover.
**Consequences:** two Telegram code paths; failover must call `setWebhook` (and recovery must `deleteWebhook`) — encoded in `users_api/scheduler_ops.py` and `local_server/control_loop.py`.

### ADR-6 — No shared Python package across services

**Context:** functions-framework deploys ship a single source dir; sharing via `pip install` would require publishing.
**Decision:** duplicate `auth.py`, `firestore_client.py`, `models.py` per service.
**Consequences:** clean deploy artifacts; risk of drift between services. Convention compensates: same filenames, same patterns.

---

## 10. Quality Requirements

### 10.1 Quality tree

```mermaid
flowchart TD
  Q[CloudApi quality]
  Q --> Cost[Cost]
  Q --> Avail[Availability]
  Q --> Dur[Durability]
  Q --> Sec[Security]
  Q --> Op[Operability]

  Cost --> C1[Stay in GCP free tier]
  Avail --> A1[Hourly sync survives Pi outage]
  Avail --> A2[Daily report delivered before 09:00 local]
  Dur --> D1[No transaction loss across reruns]
  Sec --> S1[Per-user data isolation in API layer]
  Op --> O1[Single-command deploy]
  Op --> O2[Sentry alerts on errors]
```

### 10.2 Quality scenarios

| ID  | Scenario                                                                                   | Response                                                                                  |
|-----|--------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| Q1  | Pi loses power for 2 hours.                                                                | Within `UNBLOCKER_LEAD_SEC` (≈ 30 min) the cloud takes over hourly sync and daily report. |
| Q2  | Monobank temporarily returns 429 for one user.                                              | That user's sync skips this run; others proceed; next run retries.                        |
| Q3  | Operator runs `make run` on a fresh laptop.                                                | Full stack (frontend, six APIs, Telegram polling, emulators) is up via `docker compose`.  |
| Q4  | A new transaction is fetched twice from Monobank.                                          | Idempotent write because the Monobank ID is the Firestore doc ID.                         |
| Q5  | A web user is signed in to Firebase but not registered.                                    | All API calls return `403 USER_NOT_FOUND`; the SPA redirects to `/register`.              |
| Q6  | Daily report user has 0 transactions.                                                      | `report_api` still returns a non-empty markdown summary using account snapshots.          |

---

## 11. Risks and Technical Debt

| # | Item                                                                                       | Impact                                                                       | Mitigation / next step                                       |
|---|--------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|--------------------------------------------------------------|
| 1 | `firestore.rules` is `allow read, write: if true`.                                         | Anyone with project ID could read/write Firestore from a client SDK.         | Replace with per-user rules using `request.auth.uid`.        |
| 2 | `users/{uid}.mono_token` stored plaintext in Firestore.                                    | Token compromise allows reading the user's Monobank statements.              | Move to Secret Manager / encrypt at rest with KMS.           |
| 3 | All Cloud Functions have `roles/run.invoker = allUsers`.                                   | Endpoints are world-reachable; only app-layer auth protects them.            | Switch internal endpoints to IAM-authenticated invokers.     |
| 4 | Code duplication across 7 services (`auth.py`, `firestore_client.py`).                     | Drift, inconsistent fixes.                                                   | Extract a shared package and vendor it during build.         |
| 5 | Manual `request.path` routing in each function.                                            | Easy to miss methods / paths; harder to test.                                | Adopt Flask blueprints or a thin router util.                |
| 6 | `migrate_transactions.py` is a one-off script not in CI.                                   | Hard to reproduce migrations.                                                | Move under `scripts/` with explicit doc and dry-run default. |
| 7 | Two Telegram code paths (polling on Pi, webhook in cloud).                                 | Failover regressions are easy to miss.                                       | Add an integration smoke test that exercises both paths.     |
| 8 | `INTERNAL_API_KEY` is a single static secret.                                              | Leak = full internal access.                                                 | Per-caller keys or short-lived tokens.                       |
| 9 | Frontend stores no global auth state library; relies on `onAuthStateChanged` in `App.tsx`. | Risk of subtle re-render / token-refresh bugs.                               | Introduce `react-query`/`zustand` if complexity grows.       |

---

## 12. Glossary

| Term                          | Definition                                                                                                              |
|-------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| Monobank                      | Ukrainian neobank exposing a personal API for accounts and statements.                                                  |
| Jar                           | A Monobank savings account, modelled the same way as a card account in Firestore.                                       |
| Mono token                    | Per-user Monobank API token (`X-Token`), stored on `users/{uid}.mono_token`.                                            |
| Firebase ID token             | JWT issued by Firebase Auth; presented by the SPA as `Authorization: Bearer ...`.                                       |
| Internal API key              | Shared secret in `INTERNAL_API_KEY`, sent as `X-Internal-Api-Key` for service-to-service calls.                          |
| `users_api`                   | Backend service for user CRUD, family graph, Telegram link, scheduler control.                                          |
| `accounts_api`                | Backend service for account CRUD.                                                                                       |
| `transactions_api`            | Backend service for transaction CRUD plus chart aggregations.                                                            |
| `report_api`                  | Backend service that builds the daily markdown report, optionally via Gemini.                                            |
| `sync_worker`                 | Backend service that fan-outs hourly Monobank sync per user.                                                            |
| `sync_transactions`           | Backend service that pulls Monobank statements and writes transactions in batches.                                       |
| `telegram_bot`                | Cloud Function handling Telegram webhook updates.                                                                        |
| Pi / local_server             | Raspberry Pi deployment running all backend services on `127.0.0.1` plus an APScheduler-driven scheduler.               |
| `rpi_unblocker`               | Cloud Scheduler job acting as a dead-man's-switch; fires only when the Pi heartbeat stops postponing it.                 |
| Heartbeat                     | Periodic call from `local_server.control_loop` that pushes `rpi_unblocker.schedule_time` further into the future.       |
| Family request                | Pending sharing relationship in `users/{uid}/family_requests/{requester_id}`; on accept both users gain read-only links. |
| Daily report                  | Per-user markdown summary of yesterday's transactions, optionally enriched with an LLM narrative.                       |
| Auth Emulator / Firestore Emulator | Firebase local emulators used during `make run`/dev for offline auth and DB.                                       |

---

*Source-of-truth references used while writing this document:
[README.md](../README.md),
[docker-compose.yml](../docker-compose.yml),
[firebase.json](../firebase.json),
[firestore.rules](../firestore.rules),
[Makefile](../Makefile),
[functions/](../functions/),
[frontend/](../frontend/),
[local_server/](../local_server/),
[tf/main.tf](../tf/main.tf),
[docs/auth.md](auth.md),
[docs/firestore_schema.md](firestore_schema.md),
[docs/sync_worker.md](sync_worker.md),
[docs/users_api.md](users_api.md).*
