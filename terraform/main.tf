# inspired by: https://cloud.google.com/functions/docs/tutorials/terraform?hl=de
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.34.0"
    }
  }
}

resource "random_id" "default" {
  byte_length = 8
}

resource "google_storage_bucket" "default" {
  project = "op-tcg-leaderboard-prod"
  name                        = "op-tcg-leaderboard-prod-terraform" # Every bucket name must be globally unique
  location                    = "europe-west3"
  uniform_bucket_level_access = true
}

data "archive_file" "default" {
  type        = "zip"
  output_path = "/tmp/function-source.zip"
  source_dir  = "cloud_functions/"
}
resource "google_storage_bucket_object" "object" {
  name   = "function-source.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.default.output_path # Add path to the zipped function source code
}

resource "google_cloudfunctions2_function" "default" {
  project = "op-tcg-leaderboard-prod"
  name        = "function-v2"
  location    = "europe-west3"
  description = "a new function"

  build_config {
    runtime     = "python312"
    entry_point = "run_etl_elo_update" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    available_memory   = "512M"
    timeout_seconds    = 60
    service_account_email = "streamlit-service-acc@op-tcg-leaderboard-prod.iam.gserviceaccount.com"
  }
}

resource "google_cloud_run_service_iam_member" "member" {
  location = google_cloudfunctions2_function.default.location
  service  = google_cloudfunctions2_function.default.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "function_uri" {
  value = google_cloudfunctions2_function.default.service_config[0].uri
}