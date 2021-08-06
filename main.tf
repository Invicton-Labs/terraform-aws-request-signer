resource "random_id" "lambda" {
  byte_length = 14
}

locals {
  // If no role/policy info is given, try using the current caller's role
  lambda_role = var.lambda_role_arn == null && length(var.lambda_role_policies_json) == 0 && length(var.lambda_role_policy_arns) == 0 ? local.caller_role_arn : var.lambda_role_arn
}

// Create the Lambda that will sign the request
module "signer_lambda" {
  depends_on = [
    module.assert_role_present.checked,
    module.assert_single_body.checked
  ]
  source                   = "Invicton-Labs/lambda-set/aws"
  version                  = "0.4.1"
  edge                     = false
  source_directory         = "${path.module}/lambda"
  archive_output_directory = "${path.module}/archives/"
  lambda_config = {
    function_name = "invicton-labs-aws-request-signer-${random_id.lambda.hex}"
    handler       = "main.lambda_handler"
    runtime       = "python3.8"
    timeout       = 10
    memory_size   = 128
    role          = local.lambda_role
    tags = {
      "ModuleAuthor" = "InvictonLabs"
      "ModuleUrl"    = "https://registry.terraform.io/modules/Invicton-Labs/request-signer/aws"
    }
  }
  role_policies                 = var.lambda_role_policies_json
  role_policy_arns              = var.lambda_role_policy_arns
  logs_lambda_subscriptions     = var.lambda_logs_lambda_subscriptions
  logs_non_lambda_subscriptions = var.lambda_logs_non_lambda_subscriptions
}
