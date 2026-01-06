## Deploy `users_api` + `accounts_api` to GCP (Terraform)

This deploys:
- `functions/users_api` as `users-api`
- `functions/accounts_api` as `accounts-api`
- `functions/telegram_bot` as `telegram-bot` (Telegram webhook handler)

Both are **Cloud Functions Gen2** (HTTP) and have Firestore access.

### Prereqs
- Terraform installed (`terraform -v`)
- GCP project created
- You are authenticated locally:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

Also ensure these APIs are enabled in the project:
- Cloud Functions
- Cloud Build
- Artifact Registry
- Cloud Run
- Cloud Scheduler
- Firestore

### Configure

Pick a globally-unique bucket name (stores your function source zip), then:

```bash
cd tf
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`.

Auth-related vars:
- `internal_api_key`: required for `sync_worker` / `sync_transactions` to call `users_api` / `accounts_api` / `transactions_api` (sent as `X-Internal-Api-Key`)
- `auth_mode`: keep as `"enabled"` for production. `"disabled"` is dev-only.

Scheduler-related vars:
- `sync_worker_schedule`: cron schedule for triggering `sync_worker` (default: 10:00, 14:00, 18:00, 22:00)
- `daily_reports_schedule`: cron schedule for triggering daily Telegram reports send (default: 22:45 daily)
- `scheduler_time_zone`: time zone used by Cloud Scheduler (default: `Europe/Kyiv`)

### Deploy

```bash
cd tf
terraform init
terraform apply
```

Terraform will output `users_api_url`, `accounts_api_url`, `sync_worker_scheduler_job_name`, and `daily_reports_scheduler_job_name` (plus other service URLs).

### Telegram bot webhook setup

After `terraform apply`, use the output `telegram_bot_url` to configure your bot webhook:

```bash
curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=${TELEGRAM_BOT_URL}" \
  -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}"
```

Notes:
- `TELEGRAM_BOT_URL` should be the Terraform output `telegram_bot_url`
- `TELEGRAM_WEBHOOK_SECRET` is optional (must match `telegram_webhook_secret` in `terraform.tfvars` if set)

### Update / redeploy

Just re-run:

```bash
cd tf
terraform apply
```

The source archive object name changes when code changes, forcing a rebuild/redeploy.


