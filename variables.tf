variable "lambda_role_arn" {
  description = "The ARN of the role to use for the Lambda that signs requests. If this value is provided, a new role will not be created. Conflicts with `lambda_role_policy_json`. If neither is provided, the module will attempt to use the role that the Terraform caller has assumed (if a role has been assumed)."
  type        = string
  default     = null
}

variable "lambda_role_policies_json" {
  description = "A list of JSON-encoded policies to apply to a new role that will be created for the Lambda that signs requests. Conflicts with `lambda_role_arn`. If neither is provided, the module will attempt to use the role that the Terraform caller has assumed (if a role has been assumed)."
  type        = list(string)
  default     = []
}

variable "lambda_role_policy_arns" {
  description = "A list of IAM policy ARNs to apply to a new role that will be created for the Lambda that signs requests. Conflicts with `lambda_role_arn`. If neither is provided, the module will attempt to use the role that the Terraform caller has assumed (if a role has been assumed)."
  type        = list(string)
  default     = []
}

variable "lambda_logs_lambda_subscriptions" {
  description = "A list of configurations for Lambda subscriptions to the CloudWatch Logs Group for the Lambda function that signs requests. Each element should be a map with `destination_arn` (required), `name` (optional), `filter_pattern` (optional), and `distribution` (optional)."
  type = list(object({
    destination_arn = string
    name            = optional(string)
    filter_pattern  = optional(string)
    distribution    = optional(string)
  }))
  default = []
}

variable "lambda_logs_non_lambda_subscriptions" {
  description = "A list of configurations for non-Lambda subscriptions to the CloudWatch Logs Group for the Lambda function that signs requests. Each element should be a map with `destination_arn` (required), `name` (optional), `filter_pattern` (optional), `role_arn` (optional), and `distribution` (optional)."
  type = list(object({
    destination_arn = string
    name            = optional(string)
    filter_pattern  = optional(string)
    role_arn        = optional(string)
    distribution    = optional(string)
  }))
  default = []
}

data "aws_caller_identity" "current" {}

data "aws_arn" "role" {
  arn = data.aws_caller_identity.current.arn
}

locals {
  caller_role_arn = substr(data.aws_arn.role.resource, 0, 5) == "role/" ? data.aws_caller_identity.current.arn : (substr(data.aws_arn.role.resource, 0, 13) == "assumed-role/" ? "arn:${data.aws_arn.role.partition}:iam::${data.aws_arn.role.account}:role/${split("/", data.aws_arn.role.resource)[1]}" : null)
}

module "assert_role_present" {
  source        = "Invicton-Labs/assertion/null"
  version       = "0.2.1"
  condition     = var.lambda_role_arn != null || length(var.lambda_role_policies_json) > 0 || length(var.lambda_role_policy_arns) > 0 || local.caller_role_arn != null
  error_message = "One of the `lambda_role_arn`, `lambda_role_policies_json`, or `lambda_role_policy_arns` input parameters must be provided, or this module must be called from a Terraform configuration that has assumed a role."
}
module "assert_single_body" {
  source        = "Invicton-Labs/assertion/null"
  version       = "0.2.1"
  condition     = var.lambda_role_arn == null || (length(var.lambda_role_policies_json) == 0 && length(var.lambda_role_policy_arns) == 0)
  error_message = "The `lambda_role_arn` cannot be provided when either the `lambda_role_policies_json` or `lambda_role_policy_arns` input parameter is provided."
}
