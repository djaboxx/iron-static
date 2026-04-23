terraform {
  required_version = ">= 1.5"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # State stored in GCS. Backend values live in gcs.tfbackend (gitignored).
  # Copy gcs.tfbackend.example → gcs.tfbackend and fill in your values.
  #
  # One-time bootstrap (create the state bucket before `terraform init`):
  #   gcloud storage buckets create gs://<state-bucket> \
  #     --project=<gcp-project> --location=US --uniform-bucket-level-access
  #
  # Init:
  #   terraform init -backend-config=gcs.tfbackend
  #
  # Migrate existing local state to GCS (first time only):
  #   terraform init -backend-config=gcs.tfbackend -migrate-state
  #
  # Apply:
  #   GITHUB_TOKEN=$GH_PAT \
  #   TF_VAR_gcp_project=<project> \
  #   TF_VAR_gcs_large_files_bucket=<bucket> \
  #   TF_VAR_gemini_api_key=$GEMINI_API_KEY \
  #   TF_VAR_gh_pat=$GH_PAT \
  #   terraform apply
  backend "gcs" {}
}

# The GitHub provider reads GITHUB_TOKEN from the environment.
# Always set GITHUB_OWNER= (blank) to prevent it from overriding the owner below.
provider "github" {
  owner = local.github_owner
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

locals {
  github_owner = "djaboxx"
  repository   = "iron-static"
}
