provider "google" {
  project = var.project_id
  region  = var.region

  # Fix for ADC-based auth (user credentials): some APIs (e.g. identitytoolkit)
  # require a quota project. This forces requests to bill/use the target project.
  user_project_override = true
  billing_project       = var.project_id
}

provider "google-beta" {
  project = var.project_id
  region  = var.region

  user_project_override = true
  billing_project       = var.project_id
}

# Enable Firebase services
resource "google_project_service" "firebase" {
  provider           = google-beta
  project            = var.project_id
  service            = "firebase.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "hosting" {
  provider           = google-beta
  project            = var.project_id
  service            = "firebasehosting.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "identitytoolkit" {
  provider           = google-beta
  project            = var.project_id
  service            = "identitytoolkit.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudscheduler" {
  project            = var.project_id
  service            = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager" {
  project            = var.project_id
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_firebase_project" "default" {
  provider   = google-beta
  project    = var.project_id
  depends_on = [google_project_service.firebase]
}

# Firebase Web App for the frontend
resource "google_firebase_web_app" "frontend" {
  provider        = google-beta
  project         = var.project_id
  display_name    = "CloudApi Frontend"
  deletion_policy = "DELETE"
  depends_on      = [google_firebase_project.default]
}

# Fetch the Firebase Web App config (API key, etc.) for the frontend
data "google_firebase_web_app_config" "frontend" {
  provider   = google-beta
  project    = var.project_id
  web_app_id = google_firebase_web_app.frontend.app_id
}

# Hosting site (if not already created with the project)
resource "google_firebase_hosting_site" "main" {
  provider   = google-beta
  project    = var.project_id
  site_id    = var.project_id # Using project_id as site_id is standard
  app_id     = google_firebase_web_app.frontend.app_id
  depends_on = [google_firebase_web_app.frontend]
}

# Identity Platform / Firebase Auth configuration
# This is what makes Google sign-in work on Firebase Hosting domains.
resource "google_identity_platform_config" "default" {
  provider = google-beta
  project  = var.project_id

  authorized_domains = [
    "${var.project_id}.web.app",
    "${var.project_id}.firebaseapp.com",
  ]
}

resource "google_identity_platform_default_supported_idp_config" "google" {
  provider = google-beta
  project  = var.project_id
  idp_id   = "google.com"
  enabled  = true

  client_id     = var.google_oauth_client_id
  client_secret = var.google_oauth_client_secret

  depends_on = [google_identity_platform_config.default]
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

data "archive_file" "transactions_api_zip" {
  type        = "zip"
  source_dir  = var.transactions_source_dir
  output_path = "${path.module}/.build/transactions_api.zip"
}

resource "google_storage_bucket_object" "transactions_api_src" {
  name   = "transactions_api/${data.archive_file.transactions_api_zip.output_sha}.zip"
  bucket = google_storage_bucket.functions_src.name
  source = data.archive_file.transactions_api_zip.output_path
}

data "archive_file" "sync_worker_zip" {
  type        = "zip"
  source_dir  = var.sync_worker_source_dir
  output_path = "${path.module}/.build/sync_worker.zip"
}

resource "google_storage_bucket_object" "sync_worker_src" {
  name   = "sync_worker/${data.archive_file.sync_worker_zip.output_sha}.zip"
  bucket = google_storage_bucket.functions_src.name
  source = data.archive_file.sync_worker_zip.output_path
}

data "archive_file" "sync_transactions_zip" {
  type        = "zip"
  source_dir  = var.sync_transactions_source_dir
  output_path = "${path.module}/.build/sync_transactions.zip"
}

resource "google_storage_bucket_object" "sync_transactions_src" {
  name   = "sync_transactions/${data.archive_file.sync_transactions_zip.output_sha}.zip"
  bucket = google_storage_bucket.functions_src.name
  source = data.archive_file.sync_transactions_zip.output_path
}

data "archive_file" "report_api_zip" {
  type        = "zip"
  source_dir  = var.report_source_dir
  output_path = "${path.module}/.build/report_api.zip"
}

resource "google_storage_bucket_object" "report_api_src" {
  name   = "report_api/${data.archive_file.report_api_zip.output_sha}.zip"
  bucket = google_storage_bucket.functions_src.name
  source = data.archive_file.report_api_zip.output_path
}

resource "google_service_account" "users_api" {
  account_id   = "users-api-sa"
  display_name = "users-api Cloud Function service account"
}

resource "google_service_account" "accounts_api" {
  account_id   = "accounts-api-sa"
  display_name = "accounts-api Cloud Function service account"
}

resource "google_service_account" "transactions_api" {
  account_id   = "transactions-api-sa"
  display_name = "transactions-api Cloud Function service account"
}

resource "google_service_account" "sync_worker" {
  account_id   = "sync-worker-sa"
  display_name = "sync-worker Cloud Function service account"
}

resource "google_service_account" "sync_transactions" {
  account_id   = "sync-transactions-sa"
  display_name = "sync-transactions Cloud Function service account"
}

resource "google_service_account" "report_api" {
  account_id   = "report-api-sa"
  display_name = "report-api Cloud Function service account"
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

resource "google_project_iam_member" "transactions_api_firestore_access" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.transactions_api.email}"
}

resource "google_project_iam_member" "sync_worker_firestore_access" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.sync_worker.email}"
}

resource "google_project_iam_member" "sync_transactions_firestore_access" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.sync_transactions.email}"
}

resource "google_project_iam_member" "report_api_firestore_access" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.report_api.email}"
}

resource "google_secret_manager_secret" "gemini_api_key" {
  project   = var.project_id
  secret_id = "gemini-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "gemini_api_key" {
  # Only create a secret version when a non-empty key is provided.
  # Otherwise the API errors with: "Field [payload] is required."
  count       = length(trimspace(var.gemini_api_key)) > 0 ? 1 : 0
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = var.gemini_api_key
}

resource "google_secret_manager_secret_iam_member" "report_api_secret_access" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.report_api.email}"
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
      AUTH_MODE            = var.auth_mode
      INTERNAL_API_KEY     = var.internal_api_key
      SENTRY_DSN           = var.sentry_dsn
      DISABLE_SENTRY       = var.sentry_disabled ? "1" : "0"
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
      AUTH_MODE            = var.auth_mode
      INTERNAL_API_KEY     = var.internal_api_key
      SENTRY_DSN           = var.sentry_dsn
      DISABLE_SENTRY       = var.sentry_disabled ? "1" : "0"
    }
  }
}

resource "google_cloudfunctions2_function" "transactions_api" {
  name     = var.transactions_function_name
  location = var.region

  build_config {
    runtime     = var.runtime
    entry_point = var.transactions_entry_point

    source {
      storage_source {
        bucket = google_storage_bucket.functions_src.name
        object = google_storage_bucket_object.transactions_api_src.name
      }
    }
  }

  service_config {
    available_memory      = "256M"
    timeout_seconds       = 300
    max_instance_count    = 3
    ingress_settings      = "ALLOW_ALL"
    service_account_email = google_service_account.transactions_api.email

    environment_variables = {
      FIRESTORE_PROJECT_ID = var.project_id
      AUTH_MODE            = var.auth_mode
      INTERNAL_API_KEY     = var.internal_api_key
      SENTRY_DSN           = var.sentry_dsn
      DISABLE_SENTRY       = var.sentry_disabled ? "1" : "0"
    }
  }
}

resource "google_cloudfunctions2_function" "report_api" {
  name     = var.report_function_name
  location = var.region

  build_config {
    runtime     = var.runtime
    entry_point = var.report_entry_point

    source {
      storage_source {
        bucket = google_storage_bucket.functions_src.name
        object = google_storage_bucket_object.report_api_src.name
      }
    }
  }

  service_config {
    available_memory      = "256M"
    timeout_seconds       = 120
    max_instance_count    = 3
    ingress_settings      = "ALLOW_ALL"
    service_account_email = google_service_account.report_api.email

    environment_variables = {
      FIRESTORE_PROJECT_ID = var.project_id
      AUTH_MODE            = var.auth_mode
      INTERNAL_API_KEY     = var.internal_api_key
      REPORT_TIMEZONE      = var.report_timezone
      SENTRY_DSN           = var.sentry_dsn
      DISABLE_SENTRY       = var.sentry_disabled ? "1" : "0"
    }

    dynamic "secret_environment_variables" {
      for_each = length(trimspace(var.gemini_api_key)) > 0 ? [1] : []
      content {
        key        = "GEMINI_API_KEY"
        project_id = var.project_id
        secret     = google_secret_manager_secret.gemini_api_key.secret_id
        version    = "latest"
      }
    }
  }

  depends_on = [
    google_storage_bucket_object.report_api_src,
    google_project_iam_member.report_api_firestore_access,
    google_secret_manager_secret_iam_member.report_api_secret_access,
  ]
}

resource "google_cloudfunctions2_function" "sync_worker" {
  name     = var.sync_worker_function_name
  location = var.region

  build_config {
    runtime     = var.runtime
    entry_point = var.sync_worker_entry_point

    source {
      storage_source {
        bucket = google_storage_bucket.functions_src.name
        object = google_storage_bucket_object.sync_worker_src.name
      }
    }
  }

  service_config {
    available_memory      = "256M"
    timeout_seconds       = 60
    max_instance_count    = 3
    ingress_settings      = "ALLOW_ALL"
    service_account_email = google_service_account.sync_worker.email

    environment_variables = {
      FIRESTORE_PROJECT_ID  = var.project_id
      USERS_API_URL         = google_cloudfunctions2_function.users_api.service_config[0].uri
      ACCOUNTS_API_URL      = google_cloudfunctions2_function.accounts_api.service_config[0].uri
      SYNC_TRANSACTIONS_URL = google_cloudfunctions2_function.sync_transactions.service_config[0].uri
      INTERNAL_API_KEY      = var.internal_api_key
      SENTRY_DSN            = var.sentry_dsn
      DISABLE_SENTRY        = var.sentry_disabled ? "1" : "0"
    }
  }

  depends_on = [
    google_cloudfunctions2_function.users_api,
    google_cloudfunctions2_function.accounts_api,
    google_cloudfunctions2_function.sync_transactions
  ]
}

resource "google_cloudfunctions2_function" "sync_transactions" {
  name     = var.sync_transactions_function_name
  location = var.region

  build_config {
    runtime     = var.runtime
    entry_point = var.sync_transactions_entry_point

    source {
      storage_source {
        bucket = google_storage_bucket.functions_src.name
        object = google_storage_bucket_object.sync_transactions_src.name
      }
    }
  }

  service_config {
    available_memory      = "256M"
    timeout_seconds       = 300 # Transactions can take longer
    max_instance_count    = 3
    ingress_settings      = "ALLOW_ALL"
    service_account_email = google_service_account.sync_transactions.email

    environment_variables = {
      FIRESTORE_PROJECT_ID = var.project_id
      ACCOUNTS_API_URL     = google_cloudfunctions2_function.accounts_api.service_config[0].uri
      TRANSACTIONS_API_URL = google_cloudfunctions2_function.transactions_api.service_config[0].uri
      INTERNAL_API_KEY     = var.internal_api_key
      SENTRY_DSN           = var.sentry_dsn
      DISABLE_SENTRY       = var.sentry_disabled ? "1" : "0"
    }
  }

  depends_on = [
    google_cloudfunctions2_function.accounts_api,
    google_cloudfunctions2_function.transactions_api
  ]
}

# Hourly trigger for sync_worker (HTTP)
resource "google_cloud_scheduler_job" "sync_worker_hourly" {
  name        = "sync-worker-hourly"
  description = "Hourly sync of Monobank accounts/transactions for all active users."
  region      = var.region

  schedule  = var.sync_worker_schedule
  time_zone = var.scheduler_time_zone

  attempt_deadline = "300s"

  http_target {
    uri         = "${google_cloudfunctions2_function.sync_worker.service_config[0].uri}/sync/accounts"
    http_method = "POST"

    headers = {
      Content-Type       = "application/json"
      X-Internal-Api-Key = var.internal_api_key
    }

    body = base64encode("{}")
  }

  depends_on = [
    google_project_service.cloudscheduler,
    google_cloudfunctions2_function.sync_worker,
  ]
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

resource "google_cloud_run_service_iam_member" "transactions_api_invoker" {
  location = google_cloudfunctions2_function.transactions_api.location
  service  = google_cloudfunctions2_function.transactions_api.service_config[0].service
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "report_api_invoker" {
  location = google_cloudfunctions2_function.report_api.location
  service  = google_cloudfunctions2_function.report_api.service_config[0].service
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "sync_worker_invoker" {
  location = google_cloudfunctions2_function.sync_worker.location
  service  = google_cloudfunctions2_function.sync_worker.service_config[0].service
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "sync_transactions_invoker" {
  location = google_cloudfunctions2_function.sync_transactions.location
  service  = google_cloudfunctions2_function.sync_transactions.service_config[0].service
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_firestore_field" "transactions_time" {
  project    = var.project_id
  database   = "(default)"
  collection = "transactions"
  field      = "time"

  index_config {
    indexes {
      order       = "ASCENDING"
      query_scope = "COLLECTION_GROUP"
    }
    indexes {
      order       = "DESCENDING"
      query_scope = "COLLECTION_GROUP"
    }
    # Some projects end up with a "single-field index exemption" at COLLECTION scope.
    # Explicitly enable COLLECTION scope indexes too, since the API uses:
    #   /users/{user_id}/accounts/{account_id}/transactions  -> order_by(time desc)
    indexes {
      order       = "ASCENDING"
      query_scope = "COLLECTION"
    }
    indexes {
      order       = "DESCENDING"
      query_scope = "COLLECTION"
    }
  }
}

# Composite indexes needed for transactions queries:
# - /users/{user_id}/transactions  (where user_id == X, order by time desc)
# - /users/{user_id}/charts/balance (where user_id == X, order by time asc)
resource "google_firestore_index" "transactions_user_time_asc" {
  project     = var.project_id
  database    = "(default)"
  collection  = "transactions"
  query_scope = "COLLECTION_GROUP"

  fields {
    field_path = "user_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "time"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "transactions_user_time_desc" {
  project     = var.project_id
  database    = "(default)"
  collection  = "transactions"
  query_scope = "COLLECTION_GROUP"

  fields {
    field_path = "user_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "time"
    order      = "DESCENDING"
  }
}


