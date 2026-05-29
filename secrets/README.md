# secrets/

GCP service account key for local cloud-function testing.

Required files (gitignored):
- `sa.json` (chmod 600) — GCP service account key

Mounted into `*_cloud` Docker services in docker-compose.yml at `/etc/cloudapi/`.
