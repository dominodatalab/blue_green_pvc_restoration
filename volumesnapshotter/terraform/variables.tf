
variable "eks-cluster-name" {
  type = string
  default = "greendom44351"
}


variable "custom-kms-key-policy" {
  type = string
  default = "green-upgrade-kms-key-policy"
}

variable "eks-oidc-provider-role" {
  type = string
  default = "https://oidc.eks.us-west-2.amazonaws.com/id/3AD37290979B30D1216535EFC1804FCC"
}

variable "kms_keys" {
  description = "List of KMS key ARNs"
  type        = list(string)
  default = ['arn:aws:kms:us-west-2:946429944765:key/5ace226c-20cd-4853-9480-0079da44f0ae',
             'arn:aws:kms:us-west-2:946429944765:key/29a8779c-785a-4f5d-9a7d-ee2d7f8d7dba']
}