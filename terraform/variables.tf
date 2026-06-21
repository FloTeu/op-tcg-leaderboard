variable "gcp_credentials" {}
variable "project" {}
variable "limitless_api_token" {}
variable "scraper_proxy" {}
variable "region" {
  default = "europe-west1"
}
variable "environment" {
  default = "dev"
}
variable "artifact_registry_repo" {
  default = "op-tcg"
}
