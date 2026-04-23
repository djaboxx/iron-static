# GitHub Actions secrets for the iron-static repo.
# Values are never stored in this file — they flow from environment variables:
#
#   export TF_VAR_gemini_api_key=$GEMINI_API_KEY
#   export TF_VAR_gh_pat=$GH_PAT
#
# The sensitive = true flag in variables.tf prevents values from appearing
# in plan/apply output. State files are gitignored.

resource "github_actions_secret" "gemini_api_key" {
  repository      = local.repository
  secret_name     = "GEMINI_API_KEY"
  plaintext_value = var.gemini_api_key
}

resource "github_actions_secret" "gh_pat" {
  repository      = local.repository
  secret_name     = "GH_PAT"
  plaintext_value = var.gh_pat
}
