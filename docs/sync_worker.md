## Sync Worker (local cloud function)

This service provides an endpoint to trigger account synchronization from Monobank for all active users.

In GCP, `tf/` deploys this as a **Cloud Functions Gen2** HTTP service, and a **Cloud Scheduler** job triggers it hourly.

### Logic
1.  Fetches all active users from `users_api`.
2.  For each user with a `mono_token`, fetches accounts (cards and jars) from Monobank API.
3.  Maps Monobank account data to the internal format.
4.  Pushes accounts to `accounts_api` via batch `PUT` request.

### Endpoints

#### Sync all accounts
- `POST /sync/accounts`

Triggers sync for all active users.

```bash
curl -s -X POST http://localhost:8084/sync/accounts | jq
```

### Auth (required in prod)

`sync_worker` requires an internal API key when `INTERNAL_API_KEY` is set (production default).

- Header: `X-Internal-Api-Key: <INTERNAL_API_KEY>`

Example (local / curl):

```bash
curl -s -X POST \
  -H 'X-Internal-Api-Key: dev-internal-key' \
  http://localhost:8084/sync/accounts | jq
```

Cloud Scheduler uses the same header; see `tf/main.tf` (`google_cloud_scheduler_job.sync_worker_hourly`).

### Environment Variables
- `USERS_API_URL`: URL for `users_api` (default: `http://localhost:8081`)
- `ACCOUNTS_API_URL`: URL for `accounts_api` (default: `http://localhost:8082`)
- `INTERNAL_API_KEY`: shared internal key used when calling `users_api` / `accounts_api`

### Running Locally

```bash
functions-framework \
  --source functions/sync_worker \
  --target sync_worker \
  --port 8084 \
  --debug
```

