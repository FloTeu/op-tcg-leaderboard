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
  region = var.region
}

# iam
resource "google_service_account" "cloud_function_caller" {
  account_id   = "cloud-function-caller"
  display_name = "Cloud Function Caller"
}


resource "google_storage_bucket" "default" {
  name     = "${var.project}-gcf-source"  # Every bucket name must be globally unique
  location = var.region
  uniform_bucket_level_access = true
}


resource "google_storage_bucket_object" "object" {
  name   = "function-source.zip"
  bucket = google_storage_bucket.default.name
  source = "cloud_functions/function-source.zip" # Add path to the zipped function source code
}


# cloud function
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
    # triggers redeploy
    environment_variables = {
    DEPLOYED_AT = timestamp()
    }
  }



  service_config {
    max_instance_count = 1
    available_memory   = "512M"
    timeout_seconds    = 60
    service_account_email = "streamlit-service-acc@${var.project}.iam.gserviceaccount.com"
  }
}

resource "google_cloud_run_service_iam_member" "member" {
  location = google_cloudfunctions2_function.default.location
  service  = google_cloudfunctions2_function.default.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.cloud_function_caller.email}"
}

output "function_uri" {
  value = google_cloudfunctions2_function.default.service_config[0].uri
}

# cloud function iam binding
resource "google_cloudfunctions2_function_iam_binding" "invoke_cloud_function" {
  cloud_function = google_cloudfunctions2_function.default.name
  role        = "roles/cloudfunctions.invoker"

  members = [
    "serviceAccount:${google_service_account.cloud_function_caller.email}"
  ]
}

resource "google_cloudfunctions2_function_iam_member" "invoker_permission" {
  cloud_function = google_cloudfunctions2_function.default.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.cloud_function_caller.email}"
}

# cloud scheduler
resource "google_cloud_scheduler_job" "job" {
  name             = "elo-update-job"
  region           = var.region
  description      = "run cloud function http job"
  schedule         = "0 0 */1 * *"
  time_zone        = "Europe/Berlin"
  attempt_deadline = "320s"

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.default.service_config[0].uri
    headers = {
      "Content-Type" = "application/json"
    }
    body    = base64encode("{\"meta_formats\":[]}")


    oidc_token {
      service_account_email = google_service_account.cloud_function_caller.email
    }
  }
}