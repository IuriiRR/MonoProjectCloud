# Local Server — DB Schema & API Routes

The local server is a FastAPI monolith running on the Raspberry Pi with a SQLite database at `local_server/secrets/cloudapi_local.db`.

## SQLite Schema

Models defined in `local_server/src/local_server/models.py`.

### User
| Column | Type | Notes |
|--------|------|-------|
| `user_id` | str PK | Matches Firestore document ID |
| `username` | str? | Display name |
| `mono_token` | str | Monobank API token |
| `active` | bool | Default true |
| `created_at` | datetime | UTC |
| `updated_at` | datetime | UTC |

### Account
| Column | Type | Notes |
|--------|------|-------|
| `id` | str PK | Monobank account ID |
| `user_id` | str FK→User | |
| `type` | str | `"card"` or `"jar"` |
| `send_id` | str? | Monobank sendId |
| `currency_code` | int | ISO 4217 (980=UAH) |
| `balance` | int | Smallest currency unit |
| `is_active` | bool | Default true |
| `title` | str? | Jar name |
| `goal` | int? | Jar savings goal |
| `is_budget` | bool | App-managed, default false |
| `invested` | int | App-managed, default 0 |
| `created_at` | datetime | UTC |
| `updated_at` | datetime | UTC |

### Transaction
| Column | Type | Notes |
|--------|------|-------|
| `id` | str PK | Monobank statement item ID |
| `account_id` | str FK→Account | |
| `user_id` | str (indexed) | Denormalized for fast queries |
| `time` | int (indexed) | Unix timestamp |
| `description` | str? | |
| `amount` | int | |
| `operation_amount` | int? | Original currency amount |
| `commission_rate` | int? | |
| `cashback_amount` | int? | |
| `balance` | int | Balance after transaction |
| `hold` | bool | Pending transaction |
| `comment` | str? | User annotation |
| `mcc_code` | int? | Merchant Category Code |
| `original_mcc` | int? | Pre-corrected MCC |
| `created_at` | datetime | UTC |
| `updated_at` | datetime | UTC |

## API Routes

Base URL: `http://localhost:8000` (or Pi IP in production).

### Users
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/users/` | List all users |
| `POST` | `/users/` | Create user — body: `{user_id, mono_token, username?}` |

### Accounts
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/accounts/` | List accounts; optional `?user_id=` filter |

### Transactions
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/transactions/` | List transactions; optional `?user_id=&account_id=&limit=` |

### Sync
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/sync/accounts` | Fetch accounts from Monobank for all active users → upsert SQLite |
| `POST` | `/sync/transactions` | Fetch transactions from Monobank; body: `{user_id?, days?}` (default 30 days) |
| `POST` | `/sync/firestore` | Pull all data from Cloud Firestore into SQLite |

### Other
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Health check with `last_heartbeat_at` |
| `GET` | `/reports/` | Not yet implemented |
| `*` | `/admin` | SQLAdmin web UI for User/Account/Transaction tables |

## Typical Bootstrap Flow (empty local DB)

```bash
# 1. Add your user
curl -X POST http://localhost:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{"user_id":"uid123","mono_token":"your_token_here"}'

# 2. Sync accounts from Monobank
curl -X POST http://localhost:8000/sync/accounts

# 3. Sync last 30 days of transactions
curl -X POST http://localhost:8000/sync/transactions \
  -H "Content-Type: application/json" \
  -d '{"days": 30}'
```
