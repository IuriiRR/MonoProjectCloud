# local_server/secrets

This directory is mounted into the local_server containers at `/etc/cloudapi:ro`.

Place credentials here. They are git-ignored.

Required files:

- `sa.json` — GCP service account key JSON for the `rpi-local-server` service account.
  - Source: created by `terraform apply` (or generate via `gcloud iam service-accounts keys create`).
  - The container reads this path because `GOOGLE_APPLICATION_CREDENTIALS=/etc/cloudapi/sa.json`
    is set in `local_server/.env`.

Permissions: keep `sa.json` mode `0600` on the host.
