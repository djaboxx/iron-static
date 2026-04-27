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
  default     = "happypathway-1522441039906"
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

variable "instagram_access_token" {
  description = "Long-lived Instagram User Access Token with instagram_content_publish scope. Valid ~60 days; refresh before expiry. Generate via https://developers.facebook.com/tools/explorer/"
  type        = string
  sensitive   = true
  default     = ""
}

variable "instagram_user_id" {
  description = "Numeric Instagram user ID (not username). Find via: GET /me?fields=id&access_token=<token>"
  type        = string
  sensitive   = true
  default     = ""
}

variable "youtube_client_id" {
  description = "YouTube OAuth 2.0 client ID. From Google Cloud Console OAuth 2.0 Desktop client. Generate token with: python scripts/generate_youtube_token.py"
  type        = string
  sensitive   = true
  default     = ""
}

variable "youtube_client_secret" {
  description = "YouTube OAuth 2.0 client secret. Paired with youtube_client_id."
  type        = string
  sensitive   = true
  default     = ""
}

variable "youtube_refresh_token" {
  description = "YouTube OAuth 2.0 refresh token. Does not expire unless revoked. Obtained by running python scripts/generate_youtube_token.py."
  type        = string
  sensitive   = true
  default     = ""
}
