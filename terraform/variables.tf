variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project name used for naming all resources"
  type        = string
  default     = "resume-screener"
}

variable "instance_type" {
  description = "EC2 instance type (t2.micro is Free Tier eligible)"
  type        = string
  default     = "t2.micro"
}

variable "key_pair_name" {
  description = "Name of the AWS key pair for SSH access"
  type        = string
  default     = "resume-screener-key"
}

variable "db_password" {
  description = "MySQL root password (stored in SSM Parameter Store)"
  type        = string
  sensitive   = true
  default     = "DevOps@2026!"
}
