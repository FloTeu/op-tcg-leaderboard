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
resource "google_service_account" "cloud_function_sa" {
  account_id   = "cloud-function-sa"
  display_name = "Cloud Function Service Account"
}

resource "google_project_iam_member" "bigquery_data_editor" {
  project = var.project
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.cloud_function_sa.email}"
}

resource "google_project_iam_member" "bigquery_user" {
  project = var.project
  role    = "roles/bigquery.user"
  member  = "serviceAccount:${google_service_account.cloud_function_sa.email}"
}

resource "google_project_iam_member" "run_invoker" {
  project = var.project
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.cloud_function_sa.email}"
}

# pub /sub
resource "google_pubsub_topic" "elo_update_pubsub_topic" {
  name = "elo-update-pub-sub"
}


# Set IAM binding for the Cloud Function to be invoked by Pub/Sub
resource "google_pubsub_topic_iam_binding" "pubsub_invoker" {
  topic = google_pubsub_topic.elo_update_pubsub_topic.name
  role  = "roles/pubsub.publisher"

  members = [
    "serviceAccount:${google_service_account.cloud_function_sa.email}"
  ]
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

  event_trigger {
    trigger_region = var.region
    event_type = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic = google_pubsub_topic.elo_update_pubsub_topic.id
    retry_policy = "RETRY_POLICY_RETRY"
  }

  service_config {
    max_instance_count = 1
    available_memory   = "1024M"
    timeout_seconds    = 540
    service_account_email = google_service_account.cloud_function_sa.email
  }
}

resource "google_cloud_run_service_iam_member" "member" {
  location = google_cloudfunctions2_function.default.location
  service  = google_cloudfunctions2_function.default.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.cloud_function_sa.email}"
}

# cloud function iam binding
resource "google_cloudfunctions2_function_iam_binding" "invoke_cloud_function" {
  cloud_function = google_cloudfunctions2_function.default.name
  role        = "roles/cloudfunctions.invoker"

  members = [
    "serviceAccount:${google_service_account.cloud_function_sa.email}"
  ]
}

resource "google_cloudfunctions2_function_iam_member" "invoker_permission" {
  cloud_function = google_cloudfunctions2_function.default.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.cloud_function_sa.email}"
}


output "function_uri" {
  value = google_cloudfunctions2_function.default.service_config[0].uri
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


  pubsub_target {
    topic_name = google_pubsub_topic.elo_update_pubsub_topic.id
    data       = base64encode("{\"meta_formats\":[]}")
  }

}