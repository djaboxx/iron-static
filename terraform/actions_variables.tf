# GitHub Actions variables for the iron-static repo.
# Variables are non-secret config values readable by any workflow.
# Bump model names here when new Gemini versions release — no workflow edits needed.

resource "github_actions_variable" "gemini_model_fast" {
  repository    = local.repository
  variable_name = "GEMINI_MODEL_FAST"
  value         = "gemini-2.0-flash-lite"
}

resource "github_actions_variable" "gemini_model_pro" {
  repository    = local.repository
  variable_name = "GEMINI_MODEL_PRO"
  value         = "gemini-2.5-pro"
}

# GCS bucket name for large-file sync — not sensitive, so a variable (not secret)
resource "github_actions_variable" "gcs_bucket" {
  repository    = local.repository
  variable_name = "GCS_BUCKET"
  value         = var.gcs_large_files_bucket
}
