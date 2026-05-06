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

output "report_api_url" {
  description = "HTTPS URL of the deployed report API."
  value       = google_cloudfunctions2_function.report_api.service_config[0].uri
}

output "telegram_bot_url" {
  description = "HTTPS URL of the deployed Telegram bot webhook function."
  value       = google_cloudfunctions2_function.telegram_bot.service_config[0].uri
}

output "sync_worker_url" {
  description = "HTTPS URL of the deployed sync worker."
  value       = google_cloudfunctions2_function.sync_worker.service_config[0].uri
}

output "sync_transactions_url" {
  description = "HTTPS URL of the deployed sync transactions function."
  value       = google_cloudfunctions2_function.sync_transactions.service_config[0].uri
}

output "sync_worker_scheduler_job_name" {
  description = "Name of the Cloud Scheduler job that triggers sync_worker."
  value       = google_cloud_scheduler_job.sync_worker_hourly.name
}

output "daily_reports_scheduler_job_name" {
  description = "Name of the Cloud Scheduler job that sends daily Telegram reports."
  value       = google_cloud_scheduler_job.daily_reports_daily.name
}

output "rpi_unblocker_scheduler_job_name" {
  description = "Name of the Cloud Scheduler unblocker job used by the Raspberry Pi heartbeat."
  value       = google_cloud_scheduler_job.rpi_unblocker.name
}

output "rpi_local_server_service_account_email" {
  description = "Service account email used by the Raspberry Pi local server."
  value       = google_service_account.rpi_local_server.email
}

output "local_server_env" {
  description = "Bootstrap values for local_server/.env on Raspberry Pi."
  value = {
    project_id              = var.project_id
    scheduler_region        = var.region
    unblocker_job           = google_cloud_scheduler_job.rpi_unblocker.name
    sync_worker_job         = google_cloud_scheduler_job.sync_worker_hourly.name
    daily_reports_job       = google_cloud_scheduler_job.daily_reports_daily.name
    users_api_url           = google_cloudfunctions2_function.users_api.service_config[0].uri
    accounts_api_url        = google_cloudfunctions2_function.accounts_api.service_config[0].uri
    transactions_api_url    = google_cloudfunctions2_function.transactions_api.service_config[0].uri
    sync_transactions_url   = google_cloudfunctions2_function.sync_transactions.service_config[0].uri
    telegram_webhook_url    = google_cloudfunctions2_function.telegram_bot.service_config[0].uri
    scheduler_time_zone     = var.scheduler_time_zone
    sync_worker_schedule    = var.sync_worker_schedule
    daily_reports_schedule  = var.daily_reports_schedule
  }
}

output "firebase_hosting_url" {
  description = "The URL of the Firebase Hosting site."
  value       = "https://${google_firebase_hosting_site.main.site_id}.web.app"
}

output "firebase_config" {
  description = "Firebase configuration for the frontend."
  value = {
    appId         = google_firebase_web_app.frontend.app_id
    projectId     = var.project_id
    storageBucket = "${var.project_id}.appspot.com"
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


