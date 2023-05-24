provider "aws" {
  region = "us-west-2"
  profile = "quant"
}

data "aws_ssoadmin_instances" "sso_instance" {}

resource "aws_identitystore_user" "sso_user" {
  identity_store_id = tolist(data.aws_ssoadmin_instances.sso_instance.identity_store_ids)[0]
  display_name      = "Grafana Admin"
  user_name         = "grafana_admin"

  name {
    family_name = "Grafana"
    given_name  = "Admin"
  }
}

resource "aws_identitystore_group" "grafana_admin_group" {
  identity_store_id = tolist(data.aws_ssoadmin_instances.sso_instance.identity_store_ids)[0]
  display_name      = "grafana_admin_group"
  description       = "Grafana admin group"
}

resource "aws_identitystore_group_membership" "sso_group_user" {
  identity_store_id = tolist(data.aws_ssoadmin_instances.sso_instance.identity_store_ids)[0]
  group_id          = aws_identitystore_group.grafana_admin_group.group_id
  member_id         = aws_identitystore_user.sso_user.user_id
}




resource "aws_grafana_role_association" "role_association" {
  role         = var.grafana_local_role
  group_ids    = [aws_identitystore_group.grafana_admin_group.group_id]
  workspace_id = aws_grafana_workspace.grafana_workspace.id
}

resource "aws_grafana_workspace" "grafana_workspace" {
  name                     = var.grafana_name
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO", "SAML"]
  permission_type          = "SERVICE_MANAGED"
  role_arn                 = var.grafana_role
  data_sources             = ["CLOUDWATCH", "TIMESTREAM"]
}
