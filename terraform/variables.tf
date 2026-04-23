variable "gemini_api_key" {
  description = "Google AI Studio API key for Gemini workflows. Set via: export TF_VAR_gemini_api_key=$GEMINI_API_KEY"
  type        = string
  sensitive   = true
}

variable "gh_pat" {
  description = "GitHub Personal Access Token with repo contents:write scope. Set via: export TF_VAR_gh_pat=$GH_PAT"
  type        = string
  sensitive   = true
}

variable "gcp_project" {
  description = "GCP project ID. Set via: export TF_VAR_gcp_project=<project-id>"
  type        = string
}

variable "gcp_region" {
  description = "GCS bucket location (multi-region or region). Default: US multi-region."
  type        = string
  default     = "US"
}

variable "gcs_large_files_bucket" {
  description = "GCS bucket name for large IRON STATIC files (audio, samples, presets). Set via: export TF_VAR_gcs_large_files_bucket=iron-static-files"
  type        = string
}
