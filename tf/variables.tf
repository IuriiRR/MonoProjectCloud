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

variable "bucket_name" {
  type        = string
  description = "GCS bucket to store function source archive."
}


