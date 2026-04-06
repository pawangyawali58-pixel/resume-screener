terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state stored in S3 (created below)
  # Uncomment this block after running: terraform apply -target=aws_s3_bucket.terraform_state
  # backend "s3" {
  #   bucket = "resume-screener-tfstate-718513646121"
  #   key    = "resume-screener/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
}
