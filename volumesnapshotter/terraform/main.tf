locals {
  ebs_csi_service_account_namespace = "kube-system"
  ebs_csi_service_account_name = "ebs-csi-controller-sa"
}

module "ebs_csi_controller_role" {
  source                        = "terraform-aws-modules/iam/aws//modules/iam-assumable-role-with-oidc"
  version                       = "5.11.1"
  create_role                   = true
  role_name                     = "${var.eks-cluster-name}-ebs-csi-controller"
  provider_url                  = replace(data.aws_iam_openid_connect_provider.eks-oidc-provider.url, "https://", "")
  role_policy_arns              = ["arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy",
                                   aws_iam_policy.custom_kms_policy.arn]
  oidc_fully_qualified_subjects = ["system:serviceaccount:${local.ebs_csi_service_account_namespace}:${local.ebs_csi_service_account_name}"]
}
#data.aws_iam_openid_connect_provider.eks-oidc-provider
cluster_addons = {
    aws-ebs-csi-driver = {
      service_account_role_arn = module.ebs_csi_controller_role.arn
      addon_version = "v1.13.0-eksbuild.2"
      resolve_conflicts="PRESERVE"
    }
  }

resource "aws_iam_policy" "custom_kms_policy" {
  name        = "${var.custom-kms-key-policy}"
  description = "Custom policy for KMS Key"

  # Your updated custom policy document for Policy 2
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow",
        Action    = "ec2:CreateSnapshot",
        Resource  = "*",
      },
      foreach key_arn in var.kms_keys : {
        Effect    = "Allow",
        Action    = [
          "kms:CreateGrant",
          "kms:ListGrants",
          "kms:RevokeGrant"
        ],
        Resource  = key_arn,
        Condition = {
          Bool = {
            "kms:GrantIsForAWSResource" = "true"
          }
        }
      },
      foreach key_arn in var.kms_keys : {
        Effect    = "Allow",
        Action    = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ],
        Resource  = key_arn
      }
    ]
  })
}