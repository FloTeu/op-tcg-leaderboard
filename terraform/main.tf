# inspired by: https://cloud.google.com/functions/docs/tutorials/terraform?hl=de
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.34.0"
    }
  }
}


provider "google" {
  project = var.project
}

resource "google_storage_bucket" "default" {
  name                        = "${var.project}-terraform" # Every bucket name must be globally unique
  location                    = var.region
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "object" {
  name   = "function-source.zip"
  bucket = google_storage_bucket.default.name
  source = "/tmp/function-source.zip" # Add path to the zipped function source code
}

resource "google_cloudfunctions2_function" "default" {
  name        = "elo-update"
  location    = var.region
  description = "Updates the elo of all leaders for given meta formats"

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
    max_instance_count = 5
    available_memory   = "512M"
    timeout_seconds    = 60
    service_account_email = "streamlit-service-acc@${var.project}.iam.gserviceaccount.com"
  }
}

resource "google_cloud_run_service_iam_member" "member" {
  location = google_cloudfunctions2_function.default.location
  service  = google_cloudfunctions2_function.default.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:streamlit-service-acc@${var.project}.iam.gserviceaccount.com"
}

output "function_uri" {
  value = google_cloudfunctions2_function.default.service_config[0].uri
}