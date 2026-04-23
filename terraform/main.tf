terraform {
  required_version = ">= 1.5"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

# The GitHub provider reads GITHUB_TOKEN and GITHUB_OWNER from the environment.
# GITHUB_OWNER overrides the owner field below if set — always blank it out:
#   GITHUB_OWNER= GITHUB_TOKEN=$GH_PAT TF_VAR_gemini_api_key=$GEMINI_API_KEY TF_VAR_gh_pat=$GH_PAT terraform apply -auto-approve
provider "github" {
  owner = local.github_owner
}

locals {
  github_owner = "djaboxx"
  repository   = "iron-static"
}
