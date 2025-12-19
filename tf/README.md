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
- Firestore

### Configure

Pick a globally-unique bucket name (stores your function source zip), then:

```bash
cd tf
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`.

### Deploy

```bash
cd tf
terraform init
terraform apply
```

Terraform will output `users_api_url` and `accounts_api_url`.

### Update / redeploy

Just re-run:

```bash
cd tf
terraform apply
```

The source archive object name changes when code changes, forcing a rebuild/redeploy.


