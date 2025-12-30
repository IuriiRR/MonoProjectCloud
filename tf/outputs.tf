output "users_api_url" {
  description = "HTTPS URL of the deployed users API."
  value       = google_cloudfunctions2_function.users_api.service_config[0].uri
}

output "accounts_api_url" {
  description = "HTTPS URL of the deployed accounts API."
  value       = google_cloudfunctions2_function.accounts_api.service_config[0].uri
}

output "transactions_api_url" {
  description = "HTTPS URL of the deployed transactions API."
  value       = google_cloudfunctions2_function.transactions_api.service_config[0].uri
}

output "sync_worker_url" {
  description = "HTTPS URL of the deployed sync worker."
  value       = google_cloudfunctions2_function.sync_worker.service_config[0].uri
}

output "sync_transactions_url" {
  description = "HTTPS URL of the deployed sync transactions function."
  value       = google_cloudfunctions2_function.sync_transactions.service_config[0].uri
}

output "firebase_hosting_url" {
  description = "The URL of the Firebase Hosting site."
  value       = "https://${google_firebase_hosting_site.main.site_id}.web.app"
}

output "firebase_config" {
  description = "Firebase configuration for the frontend."
  value = {
    appId             = google_firebase_web_app.frontend.app_id
    projectId         = var.project_id
    storageBucket     = "${var.project_id}.appspot.com"
  }
}

output "firebase_web_config" {
  description = "Firebase Web App config (use for the Vite VITE_FIREBASE_* env vars)."
  value = {
    apiKey            = data.google_firebase_web_app_config.frontend.api_key
    authDomain        = data.google_firebase_web_app_config.frontend.auth_domain
    projectId         = var.project_id
    storageBucket     = data.google_firebase_web_app_config.frontend.storage_bucket
    messagingSenderId = data.google_firebase_web_app_config.frontend.messaging_sender_id
    appId             = google_firebase_web_app.frontend.app_id
  }
}


