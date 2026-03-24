# ─────────────────────────────────────────────────────────────────────────────
# Reference RDS Configuration
#
# Copy these settings to your primary aws_db_instance resource to enable
# automated backups, PITR, encryption, and monitoring.
# ─────────────────────────────────────────────────────────────────────────────
#
# resource "aws_db_instance" "main" {
#   identifier = "estate-executor-production"
#   engine     = "postgres"
#   engine_version = "16.4"
#
#   # Instance sizing
#   instance_class          = "db.r6g.large"       # Production: r6g.large+
#   allocated_storage       = 100                    # GB
#   max_allocated_storage   = 500                    # Autoscaling upper limit
#   storage_type            = "gp3"
#   storage_encrypted       = true
#   kms_key_id              = module.rds_backup.backup_kms_key_arn
#
#   # ── Backup Configuration (CRITICAL) ────────────────────────────────────
#   backup_retention_period = 30                     # 30 days of PITR
#   backup_window           = "03:00-04:00"          # 3-4 AM UTC
#   copy_tags_to_snapshot   = true
#   delete_automated_backups = false                  # Keep backups after delete
#
#   # ── Maintenance ────────────────────────────────────────────────────────
#   maintenance_window              = "sun:05:00-sun:06:00"
#   auto_minor_version_upgrade      = true
#   allow_major_version_upgrade     = false
#
#   # ── High Availability ──────────────────────────────────────────────────
#   multi_az = true                                   # Synchronous standby
#
#   # ── Monitoring ─────────────────────────────────────────────────────────
#   performance_insights_enabled    = true
#   performance_insights_kms_key_id = module.rds_backup.backup_kms_key_arn
#   monitoring_interval             = 60              # Enhanced monitoring
#   monitoring_role_arn             = aws_iam_role.rds_monitoring.arn
#   enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
#
#   # ── Safety ─────────────────────────────────────────────────────────────
#   deletion_protection       = true
#   skip_final_snapshot       = false
#   final_snapshot_identifier = "estate-executor-final-${formatdate("YYYY-MM-DD", timestamp())}"
#
#   tags = {
#     Project     = "estate-executor"
#     Environment = "production"
#     Backup      = "enabled"
#   }
#
#   lifecycle {
#     prevent_destroy = true
#   }
# }
#
# # ── Cross-Region Read Replica (additional DR option) ───────────────────────
# #
# # For faster failover, deploy a read replica in the DR region.
# # This provides near-zero RPO compared to automated backup replication.
# #
# # resource "aws_db_instance" "replica" {
# #   provider               = aws.dr_region
# #   identifier             = "estate-executor-dr-replica"
# #   replicate_source_db    = aws_db_instance.main.arn
# #   instance_class         = "db.r6g.large"
# #   storage_encrypted      = true
# #   kms_key_id             = aws_kms_key.dr_backup.arn
# #   multi_az               = false
# #   backup_retention_period = 7
# #
# #   tags = {
# #     Project     = "estate-executor"
# #     Environment = "production"
# #     Role        = "dr-replica"
# #   }
# # }
