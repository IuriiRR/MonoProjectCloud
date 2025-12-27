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
    }
  }
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
    }
  }

  depends_on = [
    google_cloudfunctions2_function.accounts_api,
    google_cloudfunctions2_function.transactions_api
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
  }
}


