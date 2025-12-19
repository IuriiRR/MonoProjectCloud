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
  description = "Cloud Function name."
  default     = "users-api"
}

variable "runtime" {
  type        = string
  description = "Python runtime for Cloud Functions."
  default     = "python311"
}

variable "entry_point" {
  type        = string
  description = "Python function entry point."
  default     = "users_api"
}

variable "source_dir" {
  type        = string
  description = "Directory containing the function source + requirements.txt."
  default     = "../functions/users_api"
}

variable "bucket_name" {
  type        = string
  description = "GCS bucket to store function source archive."
}


