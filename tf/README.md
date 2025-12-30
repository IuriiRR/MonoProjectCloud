## Deploy `users_api` + `accounts_api` to GCP (Terraform)

This deploys:
- `functions/users_api` as `users-api`
- `functions/accounts_api` as `accounts-api`

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
- `sync_worker_schedule`: cron schedule for triggering `sync_worker` (default: hourly)
- `scheduler_time_zone`: time zone used by Cloud Scheduler (default: `Etc/UTC`)

### Deploy

```bash
cd tf
terraform init
terraform apply
```

Terraform will output `users_api_url`, `accounts_api_url`, and `sync_worker_scheduler_job_name` (plus other service URLs).

### Update / redeploy

Just re-run:

```bash
cd tf
terraform apply
```

The source archive object name changes when code changes, forcing a rebuild/redeploy.


