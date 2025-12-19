output "users_api_url" {
  description = "HTTPS URL of the deployed users API."
  value       = google_cloudfunctions2_function.users_api.service_config[0].uri
}

output "accounts_api_url" {
  description = "HTTPS URL of the deployed accounts API."
  value       = google_cloudfunctions2_function.accounts_api.service_config[0].uri
}


