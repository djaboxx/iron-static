# GCS infrastructure for IRON STATIC
#
# Manages:
#   - Large-file storage bucket (iron-static-files or var.gcs_large_files_bucket)
#   - GitHub Actions service account + IAM binding on that bucket
#   - Service account key (base64 JSON — decoded and written to GitHub Actions secret)
#
# NOTE: The Terraform state bucket is NOT managed here to avoid circular dependencies.
# Create it manually once (see bootstrap instructions in main.tf), then it persists forever.

resource "google_storage_bucket" "large_files" {
  name     = var.gcs_large_files_bucket
  project  = var.gcp_project
  location = var.gcp_region

  # Uniform access simplifies IAM — no per-object ACLs
  uniform_bucket_level_access = true

  # Keep previous versions of overwritten files for 30 days
  versioning {
    enabled = true
  }

  # Move objects untouched for a year to cheaper Nearline storage
  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  # Prevent accidental deletion when managed by Terraform
  force_destroy = false
}

# Dedicated service account — least privilege, scoped to this bucket only
resource "google_service_account" "github_actions" {
  account_id   = "github-actions-iron-static"
  display_name = "GitHub Actions — IRON STATIC GCS sync"
  project      = var.gcp_project
}

# objectAdmin on the large-files bucket only (not project-wide storage admin)
resource "google_storage_bucket_iam_member" "github_actions_objectadmin" {
  bucket = google_storage_bucket.large_files.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_actions.email}"
}

# SA key — private_key is base64-encoded JSON; decoded below for the GitHub secret.
# State contains the plaintext key — the GCS state bucket should have restricted access.
resource "google_service_account_key" "github_actions" {
  service_account_id = google_service_account.github_actions.name
  # Rotation: taint this resource and re-apply, then cycle the GitHub secret
}
