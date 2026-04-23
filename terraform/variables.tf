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
