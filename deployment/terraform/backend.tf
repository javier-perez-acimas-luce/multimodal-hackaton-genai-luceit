terraform {
  backend "gcs" {
    bucket = "qwiklabs-gcp-03-4db3e0484ac8-terraform-state"
    prefix = "prod"
  }
}
