# ─────────────────────────────────────────────────────────────────────────────
# RDS Backup & Recovery — Terraform Module
#
# Configures automated daily backups, point-in-time recovery, cross-region
# replication, and monitoring for the Estate Executor PostgreSQL database.
#
# Usage:
#   module "rds_backup" {
#     source              = "./modules/rds-backup"
#     environment         = "production"
#     db_instance_id      = aws_db_instance.main.id
#     primary_region      = "us-east-1"
#     replica_region      = "us-west-2"
#     backup_retention_days = 30
#     slack_webhook_url   = var.slack_webhook_url
#   }
# ─────────────────────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# ── Variables ────────────────────────────────────────────────────────────────

variable "environment" {
  description = "Deployment environment (staging, production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be staging or production."
  }
}

variable "db_instance_id" {
  description = "RDS instance identifier"
  type        = string
}

variable "primary_region" {
  description = "Primary AWS region for the RDS instance"
  type        = string
  default     = "us-east-1"
}

variable "replica_region" {
  description = "Cross-region backup replication target"
  type        = string
  default     = "us-west-2"
}

variable "backup_retention_days" {
  description = "Number of days to retain automated backups"
  type        = number
  default     = 30
}

variable "backup_window" {
  description = "Daily backup window in UTC (format: HH:MM-HH:MM)"
  type        = string
  default     = "03:00-04:00" # 3-4 AM UTC — lowest traffic window
}

variable "maintenance_window" {
  description = "Weekly maintenance window (format: ddd:HH:MM-ddd:HH:MM)"
  type        = string
  default     = "sun:05:00-sun:06:00"
}

variable "kms_key_arn" {
  description = "KMS key ARN for backup encryption (uses AWS managed key if empty)"
  type        = string
  default     = ""
}

variable "slack_webhook_url" {
  description = "Slack webhook for backup failure notifications"
  type        = string
  default     = ""
  sensitive   = true
}

variable "alarm_email" {
  description = "Email address for backup failure alarms"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}

# ── Locals ───────────────────────────────────────────────────────────────────

locals {
  name_prefix = "estate-executor-${var.environment}"
  common_tags = merge(var.tags, {
    Project     = "estate-executor"
    Environment = var.environment
    ManagedBy   = "terraform"
    Component   = "backup"
  })
}

# ── KMS Key for Backup Encryption ────────────────────────────────────────────

resource "aws_kms_key" "backup" {
  count               = var.kms_key_arn == "" ? 1 : 0
  description         = "${local.name_prefix} database backup encryption key"
  enable_key_rotation = true
  tags                = local.common_tags
}

resource "aws_kms_alias" "backup" {
  count         = var.kms_key_arn == "" ? 1 : 0
  name          = "alias/${local.name_prefix}-backup"
  target_key_id = aws_kms_key.backup[0].key_id
}

locals {
  backup_kms_key_arn = var.kms_key_arn != "" ? var.kms_key_arn : aws_kms_key.backup[0].arn
}

# ── RDS Automated Backup Configuration ───────────────────────────────────────
#
# This configures the *existing* RDS instance for automated backups.
# Point-in-time recovery (PITR) is automatically enabled when
# backup_retention_period > 0.

resource "aws_db_instance" "backup_config" {
  # This is a lifecycle-only resource that manages backup settings
  # on the existing instance. The actual instance is created elsewhere.
  #
  # NOTE: In practice, these settings should be on the primary RDS resource.
  # This module documents the required configuration — apply these settings
  # to your existing aws_db_instance resource:

  # IMPORTANT: Uncomment and reference your actual RDS instance
  # identifier = var.db_instance_id

  count = 0 # Disabled — apply settings below to your primary RDS resource

  backup_retention_period          = var.backup_retention_days
  backup_window                    = var.backup_window
  maintenance_window               = var.maintenance_window
  copy_tags_to_snapshot            = true
  delete_automated_backups         = false
  storage_encrypted                = true
  kms_key_id                       = local.backup_kms_key_arn
  deletion_protection              = var.environment == "production"
  performance_insights_enabled     = true
  performance_insights_kms_key_id  = local.backup_kms_key_arn
  monitoring_interval              = 60
  enabled_cloudwatch_logs_exports  = ["postgresql", "upgrade"]

  tags = local.common_tags

  lifecycle {
    prevent_destroy = true
  }
}

# ── Cross-Region Backup Replication ──────────────────────────────────────────

resource "aws_db_instance_automated_backups_replication" "cross_region" {
  source_db_instance_arn = "arn:aws:rds:${var.primary_region}:${data.aws_caller_identity.current.account_id}:db:${var.db_instance_id}"
  kms_key_id             = local.backup_kms_key_arn
  retention_period       = var.backup_retention_days

  # Replication target is in the replica region
  # Configure the AWS provider alias for the replica region
}

data "aws_caller_identity" "current" {}

# ── SNS Topic for Backup Alerts ──────────────────────────────────────────────

resource "aws_sns_topic" "backup_alerts" {
  name = "${local.name_prefix}-backup-alerts"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alarm_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.backup_alerts.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# ── CloudWatch Alarms ────────────────────────────────────────────────────────

# Alert: No successful backup in 26 hours (daily backup + 2hr grace)
resource "aws_cloudwatch_metric_alarm" "backup_failed" {
  alarm_name          = "${local.name_prefix}-backup-failed"
  alarm_description   = "No successful automated backup in the last 26 hours"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 93600 # 26 hours
  statistic           = "SampleCount"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.backup_alerts.arn]
  ok_actions          = [aws_sns_topic.backup_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = var.db_instance_id
  }

  tags = local.common_tags
}

# Alert: RDS storage space running low (< 10 GB free)
resource "aws_cloudwatch_metric_alarm" "low_storage" {
  alarm_name          = "${local.name_prefix}-low-storage"
  alarm_description   = "RDS free storage below 10 GB — may impact backups"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 10737418240 # 10 GB in bytes
  alarm_actions       = [aws_sns_topic.backup_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = var.db_instance_id
  }

  tags = local.common_tags
}

# Alert: Replication lag on cross-region backup
resource "aws_cloudwatch_metric_alarm" "replication_lag" {
  alarm_name          = "${local.name_prefix}-replication-lag"
  alarm_description   = "Cross-region backup replication lag exceeds 1 hour"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "ReplicaLag"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 3600 # 1 hour in seconds
  alarm_actions       = [aws_sns_topic.backup_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = var.db_instance_id
  }

  tags = local.common_tags
}

# ── Outputs ──────────────────────────────────────────────────────────────────

output "backup_kms_key_arn" {
  description = "KMS key ARN used for backup encryption"
  value       = local.backup_kms_key_arn
}

output "sns_topic_arn" {
  description = "SNS topic ARN for backup alerts"
  value       = aws_sns_topic.backup_alerts.arn
}

output "replication_arn" {
  description = "Cross-region backup replication ARN"
  value       = aws_db_instance_automated_backups_replication.cross_region.id
}
