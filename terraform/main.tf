# inspired by: https://cloud.google.com/functions/docs/tutorials/terraform?hl=de
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0.0"
    }
  }
  # bucket is passed via -backend-config in CI so dev/prod use separate state.
  backend "gcs" {
    prefix = "terraform/state"
  }
}

provider "google" {
  credentials = file(var.gcp_credentials)
  project     = var.project
  region      = var.region
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

resource "google_project_iam_member" "storage_object_admin" {
  project = var.project
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cloud_function_sa.email}"
}

resource "google_project_iam_member" "storage_object_creator" {
  project = var.project
  role    = "roles/storage.objectCreator"
  member  = "serviceAccount:${google_service_account.cloud_function_sa.email}"
}

resource "google_project_iam_member" "storage_bucket_viewer" {
  project = var.project
  role    = "roles/storage.insightsCollectorService"
  member  = "serviceAccount:${google_service_account.cloud_function_sa.email}"
}

resource "google_project_iam_member" "run_invoker" {
  project = var.project
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.cloud_function_sa.email}"
}

# pub/sub
resource "google_pubsub_topic" "all_elo_update_pubsub_topic" {
  name = "all-elo-update-pub-sub"
}

resource "google_pubsub_topic" "elo_update_pubsub_topic" {
  name = "elo-update-pub-sub"
}

resource "google_pubsub_topic" "crawl_tournaments_pubsub_topic" {
  name = "crawl-tournaments-pub-sub"
}

resource "google_pubsub_topic" "crawl_prices_pubsub_topic" {
  name = "crawl-prices-pub-sub"
}

resource "google_pubsub_topic" "card_image_update_pubsub_topic" {
  name = "card-image-update-pub-sub"
}

resource "google_pubsub_topic" "crawl_op_top_decks_pubsub_topic" {
  name = "crawl-op-top-decks-pub-sub"
}

# Set IAM binding for the Cloud Function to be invoked by Pub/Sub
resource "google_pubsub_topic_iam_binding" "elo_updatepubsub_invoker" {
  topic = google_pubsub_topic.elo_update_pubsub_topic.name
  role  = "roles/pubsub.publisher"

  members = [
    "serviceAccount:${google_service_account.cloud_function_sa.email}"
  ]
}
resource "google_pubsub_topic_iam_binding" "all_elo_update_pubsub_invoker" {
  topic = google_pubsub_topic.all_elo_update_pubsub_topic.name
  role  = "roles/pubsub.publisher"

  members = [
    "serviceAccount:${google_service_account.cloud_function_sa.email}"
  ]
}

resource "google_pubsub_topic_iam_binding" "crawl_op_top_decks_pubsub_invoker" {
  topic = google_pubsub_topic.crawl_op_top_decks_pubsub_topic.name
  role  = "roles/pubsub.publisher"

  members = [
    "serviceAccount:${google_service_account.cloud_function_sa.email}"
  ]
}

resource "google_storage_bucket" "default" {
  name                        = "${var.project}-gcf-source" # Every bucket name must be globally unique
  location                    = "europe-west3"
  uniform_bucket_level_access = true
}


resource "google_storage_bucket_object" "object" {
  name   = "function-source.zip"
  bucket = google_storage_bucket.default.name
  source = "cloud_functions/function-source.zip" # Add path to the zipped function source code
}

# storage
resource "google_storage_bucket" "public" {
  name                        = "${var.project}-public"
  location                    = "europe-west3"
  uniform_bucket_level_access = true

  website {
    main_page_suffix = "index.html"
    not_found_page   = "404.html"
  }
  cors {
    origin          = ["http://image-store.com"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}

## make bucket public accessible
data "google_iam_policy" "storage_viewer" {
  binding {
    role = "roles/storage.objectViewer"
    members = [
      "allUsers",
    ]
  }
}

resource "google_storage_bucket_iam_policy" "policy" {
  bucket      = google_storage_bucket.public.name
  policy_data = data.google_iam_policy.storage_viewer.policy_data
}

# cloud function
resource "google_cloudfunctions2_function" "all_elo" {
  name        = "all-elo-update"
  location    = var.region
  description = "Updates the elo of all leaders for all meta formats"

  build_config {
    runtime     = "python312"
    entry_point = "run_all_etl_elo_update" # Set the entry point
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
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.all_elo_update_pubsub_topic.id
    retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
  }

  service_config {
    max_instance_count    = 1
    available_memory      = "512M"
    timeout_seconds       = 60
    service_account_email = google_service_account.cloud_function_sa.email
    # triggers redeploy
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project
    }
  }
}

resource "google_cloudfunctions2_function" "single-elo" {
  name        = "single-elo-update"
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
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.elo_update_pubsub_topic.id
    retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
  }

  service_config {
    max_instance_count    = 10
    available_memory      = "1024M"
    timeout_seconds       = 540
    service_account_email = google_service_account.cloud_function_sa.email
  }
}


resource "google_cloudfunctions2_function" "crawl-tournaments" {
  name        = "crawl-tournaments"
  location    = var.region
  description = "Inserts latest tournament data to BQ"

  build_config {
    runtime     = "python312"
    entry_point = "run_crawl_tournament" # Set the entry point
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
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.crawl_tournaments_pubsub_topic.id
    retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
  }

  service_config {
    max_instance_count    = 10
    available_memory      = "768M"
    timeout_seconds       = 540
    service_account_email = google_service_account.cloud_function_sa.email
    environment_variables = {
      LIMITLESS_API_TOKEN  = var.limitless_api_token
      GOOGLE_CLOUD_PROJECT = var.project
    }
  }
}

resource "google_cloudfunctions2_function" "crawl-op-top-decks" {
  name        = "crawl-op-top-decks"
  location    = var.region
  description = "Crawls op top decks decklists, triggered after limitless tournament crawl"

  build_config {
    runtime     = "python312"
    entry_point = "run_crawl_op_top_decks"
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
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.crawl_op_top_decks_pubsub_topic.id
    retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
  }

  service_config {
    max_instance_count    = 1
    available_memory      = "768M"
    timeout_seconds       = 540
    service_account_email = google_service_account.cloud_function_sa.email
    environment_variables = {
      SCRAPER_PROXY        = var.scraper_proxy
      GOOGLE_CLOUD_PROJECT = var.project
    }
  }
}

resource "google_cloudfunctions2_function" "crawl-prices" {
  name        = "crawl-prices"
  location    = var.region
  description = "Inserts latest prices to BQ"

  build_config {
    runtime     = "python312"
    entry_point = "run_crawl_prices" # Set the entry point
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
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.crawl_prices_pubsub_topic.id
    retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
  }

  service_config {
    max_instance_count    = 10
    available_memory      = "512M"
    timeout_seconds       = 540
    service_account_email = google_service_account.cloud_function_sa.email
  }
}


resource "google_cloudfunctions2_function" "card_image_update" {
  name        = "card-image-update"
  location    = var.region
  description = "Downloads card images to GCP and updates BQ"

  build_config {
    runtime     = "python312"
    entry_point = "run_etl_card_image_update" # Set the entry point
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
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.card_image_update_pubsub_topic.id
    retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
  }

  service_config {
    max_instance_count    = 10
    available_memory      = "512M"
    timeout_seconds       = 540
    service_account_email = google_service_account.cloud_function_sa.email
  }
}

# ---- sealed products crawler (Cloud Run Job) ----

resource "google_cloud_run_v2_job" "crawl_sealed_products" {
  name     = "crawl-sealed-products"
  location = var.region

  # Required in provider v6+ to allow destroy/recreate without manual intervention.
  deletion_protection = false

  # CI updates the container image on each deploy via `gcloud run jobs update`.
  # Terraform only manages the initial definition and env vars; the image is ignored
  # after the first apply so CI-managed image updates are not reverted.
  lifecycle {
    ignore_changes = [template]
  }

  template {
    task_count = 1

    template {
      max_retries     = 1
      timeout         = "1800s"
      service_account = google_service_account.cloud_function_sa.email

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project}/${var.artifact_registry_repo}/op-tcg-crawler:latest"

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project
        }
        env {
          name  = "SCRAPER_PROXY"
          value = var.scraper_proxy
        }
        env {
          name  = "CAMOUFOX_HEADLESS"
          value = "true"
        }

        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }
      }
    }
  }
}

resource "google_cloud_scheduler_job" "crawl_sealed_products_job" {
  name             = "crawl-sealed-products-job"
  region           = var.region
  description      = "Triggers the sealed products Cloud Run Job to crawl Cardmarket prices"
  schedule         = "0 21 * * 1"
  time_zone        = "Europe/Berlin"
  attempt_deadline = "320s"
  paused           = true

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project}/locations/${var.region}/jobs/crawl-sealed-products:run"
    body        = base64encode("{}")

    oauth_token {
      service_account_email = google_service_account.cloud_function_sa.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }
}

resource "google_cloud_run_service_iam_member" "member" {
  location = google_cloudfunctions2_function.all_elo.location
  service  = google_cloudfunctions2_function.all_elo.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.cloud_function_sa.email}"
}

# cloud function iam binding
resource "google_cloudfunctions2_function_iam_binding" "invoke_cloud_function" {
  cloud_function = google_cloudfunctions2_function.all_elo.name
  role           = "roles/cloudfunctions.invoker"

  members = [
    "serviceAccount:${google_service_account.cloud_function_sa.email}"
  ]
}

resource "google_cloudfunctions2_function_iam_member" "invoker_permission" {
  cloud_function = google_cloudfunctions2_function.all_elo.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.cloud_function_sa.email}"
}


output "function_uri" {
  value = google_cloudfunctions2_function.all_elo.service_config[0].uri
}

# cloud scheduler
resource "google_cloud_scheduler_job" "elo-update-job" {
  name             = "elo-update-job"
  region           = var.region
  description      = "run cloud function pub/sub job to start elo update"
  schedule         = "0 0 */1 * *"
  time_zone        = "Europe/Berlin"
  attempt_deadline = "320s"
  paused           = var.environment == "dev"

  retry_config {
    retry_count = 1
  }

  pubsub_target {
    topic_name = google_pubsub_topic.all_elo_update_pubsub_topic.id
    data       = base64encode("{\"meta_formats\":[]}")
  }
}


resource "google_cloud_scheduler_job" "crawl-tournament-job" {
  name             = "crawl-tournament-job"
  region           = var.region
  description      = "run cloud function pub/sub job to start tournament update"
  schedule         = "0 22 */1 * *"
  time_zone        = "Europe/Berlin"
  attempt_deadline = "320s"
  paused           = var.environment == "dev"

  retry_config {
    retry_count = 1
  }

  pubsub_target {
    topic_name = google_pubsub_topic.crawl_tournaments_pubsub_topic.id
    data       = base64encode("{\"num_tournament_limit\":30}")
  }
}

resource "google_cloud_scheduler_job" "crawl-prices-job" {
  name             = "crawl-prices-job"
  region           = var.region
  description      = "run cloud function pub/sub job to start price update"
  schedule         = "0 23 * * 1"
  time_zone        = "Europe/Berlin"
  attempt_deadline = "320s"
  paused           = var.environment == "dev"

  retry_config {
    retry_count = 1
  }

  pubsub_target {
    topic_name = google_pubsub_topic.crawl_prices_pubsub_topic.id
    data       = base64encode("{}")
  }
}


resource "google_cloud_scheduler_job" "card_image_update_job" {
  name             = "card-image-update-job"
  region           = var.region
  description      = "run cloud function pub/sub job to start card image update"
  schedule         = "0 22 */7 * *"
  time_zone        = "Europe/Berlin"
  attempt_deadline = "320s"
  paused           = var.environment == "dev"

  retry_config {
    retry_count = 1
  }

  pubsub_target {
    topic_name = google_pubsub_topic.card_image_update_pubsub_topic.id
    data       = base64encode("{}")
  }
}
