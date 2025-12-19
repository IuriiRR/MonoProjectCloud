provider "google" {
  project = var.project_id
  region  = var.region
}

data "archive_file" "users_api_zip" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/.build/users_api.zip"
}

data "archive_file" "accounts_api_zip" {
  type        = "zip"
  source_dir  = var.accounts_source_dir
  output_path = "${path.module}/.build/accounts_api.zip"
}

resource "google_storage_bucket" "functions_src" {
  name                        = var.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}

resource "google_storage_bucket_object" "users_api_src" {
  name   = "users_api/${data.archive_file.users_api_zip.output_sha}.zip"
  bucket = google_storage_bucket.functions_src.name
  source = data.archive_file.users_api_zip.output_path
}

resource "google_storage_bucket_object" "accounts_api_src" {
  name   = "accounts_api/${data.archive_file.accounts_api_zip.output_sha}.zip"
  bucket = google_storage_bucket.functions_src.name
  source = data.archive_file.accounts_api_zip.output_path
}

resource "google_service_account" "users_api" {
  account_id   = "users-api-sa"
  display_name = "users-api Cloud Function service account"
}

resource "google_service_account" "accounts_api" {
  account_id   = "accounts-api-sa"
  display_name = "accounts-api Cloud Function service account"
}

resource "google_project_iam_member" "users_api_firestore_access" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.users_api.email}"
}

resource "google_project_iam_member" "accounts_api_firestore_access" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.accounts_api.email}"
}

resource "google_cloudfunctions2_function" "users_api" {
  name     = var.function_name
  location = var.region

  build_config {
    runtime     = var.runtime
    entry_point = var.entry_point

    source {
      storage_source {
        bucket = google_storage_bucket.functions_src.name
        object = google_storage_bucket_object.users_api_src.name
      }
    }
  }

  service_config {
    available_memory      = "256M"
    timeout_seconds       = 60
    max_instance_count    = 3
    ingress_settings      = "ALLOW_ALL"
    service_account_email = google_service_account.users_api.email

    environment_variables = {
      FIRESTORE_PROJECT_ID = var.project_id
    }
  }
}

resource "google_cloudfunctions2_function" "accounts_api" {
  name     = var.accounts_function_name
  location = var.region

  build_config {
    runtime     = var.runtime
    entry_point = var.accounts_entry_point

    source {
      storage_source {
        bucket = google_storage_bucket.functions_src.name
        object = google_storage_bucket_object.accounts_api_src.name
      }
    }
  }

  service_config {
    available_memory      = "256M"
    timeout_seconds       = 60
    max_instance_count    = 3
    ingress_settings      = "ALLOW_ALL"
    service_account_email = google_service_account.accounts_api.email

    environment_variables = {
      FIRESTORE_PROJECT_ID = var.project_id
    }
  }
}

# Public (unauthenticated) invoke for now. Tighten later with IAM / auth.
resource "google_cloud_run_service_iam_member" "users_api_invoker" {
  location = google_cloudfunctions2_function.users_api.location
  service  = google_cloudfunctions2_function.users_api.service_config[0].service
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "accounts_api_invoker" {
  location = google_cloudfunctions2_function.accounts_api.location
  service  = google_cloudfunctions2_function.accounts_api.service_config[0].service
  role     = "roles/run.invoker"
  member   = "allUsers"
}


