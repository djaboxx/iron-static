# GitHub Actions variables for the iron-static repo.
# Variables are non-secret config values readable by any workflow.
# Bump model names here when new Gemini versions release — no workflow edits needed.

resource "github_actions_variable" "gemini_model_fast" {
  repository    = local.repository
  variable_name = "GEMINI_MODEL_FAST"
  value         = "gemini-2.0-flash"
}

resource "github_actions_variable" "gemini_model_pro" {
  repository    = local.repository
  variable_name = "GEMINI_MODEL_PRO"
  value         = "gemini-2.5-pro"
}
