variable "project_id" {
  type        = string
  description = "GCP project id to deploy into."
}

variable "region" {
  type        = string
  description = "GCP region for Cloud Functions Gen2."
  default     = "europe-west1"
}

variable "function_name" {
  type        = string
  description = "Cloud Function name (users_api)."
  default     = "users-api"
}

variable "runtime" {
  type        = string
  description = "Python runtime for Cloud Functions."
  default     = "python311"
}

variable "entry_point" {
  type        = string
  description = "Python function entry point (users_api)."
  default     = "users_api"
}

variable "source_dir" {
  type        = string
  description = "Directory containing the function source + requirements.txt (users_api)."
  default     = "../functions/users_api"
}

variable "accounts_function_name" {
  type        = string
  description = "Cloud Function name (accounts_api)."
  default     = "accounts-api"
}

variable "accounts_entry_point" {
  type        = string
  description = "Python function entry point (accounts_api)."
  default     = "accounts_api"
}

variable "accounts_source_dir" {
  type        = string
  description = "Directory containing the function source + requirements.txt (accounts_api)."
  default     = "../functions/accounts_api"
}

variable "transactions_function_name" {
  type        = string
  description = "Cloud Function name (transactions_api)."
  default     = "transactions-api"
}

variable "transactions_entry_point" {
  type        = string
  description = "Python function entry point (transactions_api)."
  default     = "transactions_api"
}

variable "transactions_source_dir" {
  type        = string
  description = "Directory containing the function source + requirements.txt (transactions_api)."
  default     = "../functions/transactions_api"
}

variable "sync_worker_function_name" {
  type        = string
  description = "Cloud Function name (sync_worker)."
  default     = "sync-worker"
}

variable "sync_worker_entry_point" {
  type        = string
  description = "Python function entry point (sync_worker)."
  default     = "sync_worker"
}

variable "sync_worker_source_dir" {
  type        = string
  description = "Directory containing the function source + requirements.txt (sync_worker)."
  default     = "../functions/sync_worker"
}

variable "sync_transactions_function_name" {
  type        = string
  description = "Cloud Function name (sync_transactions)."
  default     = "sync-transactions"
}

variable "sync_transactions_entry_point" {
  type        = string
  description = "Python function entry point (sync_transactions)."
  default     = "sync_transactions"
}

variable "sync_transactions_source_dir" {
  type        = string
  description = "Directory containing the function source + requirements.txt (sync_transactions)."
  default     = "../functions/sync_transactions"
}

variable "report_function_name" {
  type        = string
  description = "Cloud Function name (report_api)."
  default     = "report-api"
}

variable "report_entry_point" {
  type        = string
  description = "Python function entry point (report_api)."
  default     = "report_api"
}

variable "report_source_dir" {
  type        = string
  description = "Directory containing the function source + requirements.txt (report_api)."
  default     = "../functions/report_api"
}

variable "report_timezone" {
  type        = string
  description = "Default timezone for daily reports (used when tz query param is omitted)."
  default     = "Europe/Kyiv"
}

variable "gemini_api_key" {
  type        = string
  description = "Gemini API key (stored in Secret Manager and injected into report_api as GEMINI_API_KEY)."
  sensitive   = true
  default     = ""
}

variable "bucket_name" {
  type        = string
  description = "GCS bucket to store function source archive."
}

variable "google_oauth_client_id" {
  type        = string
  description = "OAuth Client ID used for Google sign-in (Identity Platform / Firebase Auth)."
  default     = ""
}

variable "google_oauth_client_secret" {
  type        = string
  description = "OAuth Client Secret used for Google sign-in (Identity Platform / Firebase Auth)."
  sensitive   = true
  default     = ""
}

variable "internal_api_key" {
  type        = string
  description = "Shared key for internal function-to-function calls (sync_worker/sync_transactions -> APIs)."
  sensitive   = true
  default     = ""
}

variable "auth_mode" {
  type        = string
  description = "Auth mode for HTTP APIs: 'enabled' (default) or 'disabled' (dev-only)."
  default     = "enabled"
}

variable "sync_worker_schedule" {
  type        = string
  description = "Cron schedule for Cloud Scheduler job that triggers sync_worker."
  default     = "0 * * * *"
}

variable "scheduler_time_zone" {
  type        = string
  description = "Time zone used by Cloud Scheduler (e.g. 'Etc/UTC', 'Europe/Kyiv')."
  default     = "Etc/UTC"
}

variable "sentry_dsn" {
  type        = string
  description = "Sentry DSN. Leave empty to disable Sentry."
  sensitive   = true
  default     = ""
}

variable "sentry_disabled" {
  type        = bool
  description = "When true, sets DISABLE_SENTRY=1 for all functions."
  default     = false
}


