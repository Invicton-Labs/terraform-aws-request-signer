# Terraform AWS Request Signer

This module creates a Lambda function that can be used to sign requests for use against the AWS API. It is intended to be used in conjunction with the [Invicton-Labs/signed-request/aws](https://registry.terraform.io/modules/Invicton-Labs/signed-request/aws/latest) module.

Usage:

```
module "request_signer" {
  source = "Invicton-Labs/request-signer/aws"

  // Create a role with admin permissions so the Lambda can sign any request
  lambda_role_policy_arns = [
    "arn:aws:iam::aws:policy/AdministratorAccess"
  ]
}

module "signed_request" {
  source                = "Invicton-Labs/signed-request/aws"

  // Pass in the module we just created
  request_signer_module = module.request_signer

  // Parameters for the request. See the documentation for this module for details.
  method                = "GET"
  service               = "ec2"
  headers               = {}
  query_parameters = {
    Action  = "DescribeRegions",
    Version = "2013-10-15",
  }
}

output "signed_request_url" {
    value = module.signed_request.request_url
}
output "signed_request_headers" {
    value = module.signed_request.request_headers
}
```

```
Apply complete! Resources: 0 added, 0 changed, 0 destroyed.

Outputs:

signed_request_headers = {
  "Authorization" = "AWS4-HMAC-SHA256 Credential=.../20210809/us-east-1/ec2/aws4_request, SignedHeaders=content-length;host;x-amz-date;x-amz-security-token, Signature=..."
  "Content-Length" = "0"
  "X-Amz-Date" = "20210809T193725Z"
  "X-Amz-Security-Token" = "..."
}
signed_request_url = "https://ec2.us-east-1.amazonaws.com?Action=DescribeRegions&Version=2013-10-15"
```