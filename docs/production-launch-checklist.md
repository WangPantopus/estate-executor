# Production Launch Checklist

> **Last updated:** 2026-03-24
> **Owner:** Platform Team
> **Review cadence:** Before every major release

Mark each item `[x]` only after direct verification — not when "probably fine."
Items marked **BLOCKER** must be resolved before launch. Others are strongly recommended.

---

## Table of Contents

1. [DNS & Domain Configuration](#1-dns--domain-configuration)
2. [SSL Certificate Verification](#2-ssl-certificate-verification)
3. [Environment Variable Audit](#3-environment-variable-audit)
4. [Database Migration Verification](#4-database-migration-verification)
5. [Stripe Webhook Configuration](#5-stripe-webhook-configuration)
6. [Auth0 Production Tenant Configuration](#6-auth0-production-tenant-configuration)
7. [Email Sending Verification](#7-email-sending-verification)
8. [Security Header Verification](#8-security-header-verification)
9. [Performance Baseline](#9-performance-baseline)
10. [Monitoring & Alerting Verification](#10-monitoring--alerting-verification)
11. [Common Operational Runbooks](#11-common-operational-runbooks)
12. [On-Call Rotation Setup](#12-on-call-rotation-setup)
13. [Incident Response Procedure](#13-incident-response-procedure)

---

## 1. DNS & Domain Configuration

### Records

- [ ] `api.estate-executor.com` → backend load balancer (A / CNAME)
- [ ] `estate-executor.com` → frontend (A / CNAME, Vercel or CDN)
- [ ] `www.estate-executor.com` → redirect to apex
- [ ] TTL reduced to 300s at least 48 hours before cutover; restore to ≥ 3600s after

### Verification

```bash
# Confirm DNS resolves correctly from multiple vantage points
dig +short api.estate-executor.com
dig +short estate-executor.com

# Confirm no stale CNAME chains
dig api.estate-executor.com CNAME
```

- [ ] `api.estate-executor.com` resolves to the correct load balancer IP
- [ ] `estate-executor.com` resolves to the correct frontend IP / CDN edge
- [ ] No `localhost` or staging IPs remain in DNS

### Backend & Frontend URLs

- [ ] `BACKEND_URL=https://api.estate-executor.com` in backend `.env`
- [ ] `FRONTEND_URL=https://estate-executor.com` in backend `.env`
- [ ] `NEXT_PUBLIC_API_URL=https://api.estate-executor.com/api/v1` in frontend `.env`
- [ ] `APP_BASE_URL=https://estate-executor.com` in frontend `.env`

---

## 2. SSL Certificate Verification

- [ ] **BLOCKER** TLS certificate issued for `api.estate-executor.com` and `estate-executor.com`
- [ ] Certificate authority is trusted by all major browsers (Let's Encrypt, AWS ACM, etc.)
- [ ] Certificate expiry > 60 days from launch date
- [ ] Auto-renewal is configured (ACM auto-renews; Let's Encrypt requires certbot cron)
- [ ] HSTS is active — `Strict-Transport-Security` header present on all responses (see §8)
- [ ] No mixed-content warnings in browser console on the login and dashboard pages

```bash
# Check certificate validity and expiry
echo | openssl s_client -connect api.estate-executor.com:443 -servername api.estate-executor.com 2>/dev/null \
  | openssl x509 -noout -dates -subject -issuer

# Confirm TLS 1.2+ only (TLS 1.0/1.1 must not be accepted)
nmap --script ssl-enum-ciphers -p 443 api.estate-executor.com
```

---

## 3. Environment Variable Audit

The app calls `settings.validate_production_secrets()` on startup and **refuses to start** if any of the following are missing or using placeholder values. Verify each directly in the production secrets manager (AWS Secrets Manager / Parameter Store).

### BLOCKER — startup will fail without these

| Variable | Expected value |
|---|---|
| `APP_ENV` | `production` |
| `ENVIRONMENT` | `production` |
| `APP_SECRET_KEY` | Random 64-char hex (`openssl rand -hex 32`) — **not** `change-me-to-a-random-secret` |
| `ENCRYPTION_MASTER_KEY` | 32-byte base64 key for field-level encryption |
| `AUTH0_DOMAIN` | `your-tenant.us.auth0.com` (production tenant, not dev) |
| `AUTH0_API_AUDIENCE` | `https://api.estate-executor.com` |
| `AUTH0_CLIENT_SECRET` | Production Auth0 application secret |
| `E2E_MOCK_AUTH` | `false` — **must not be true in production** |

### Required — service will be degraded without these

| Variable | Notes |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` pointing to production RDS |
| `DATABASE_URL_SYNC` | `postgresql://...` — same host, sync driver for Alembic |
| `REDIS_URL` | Production ElastiCache endpoint (`redis://...`) — DB 0 |
| `CELERY_BROKER_URL` | **Must differ from `REDIS_URL`** — Redis DB 1 (`redis://.../1`) |
| `CELERY_RESULT_BACKEND` | Redis DB 2 (`redis://.../2`) |
| `ANTHROPIC_API_KEY` | Production Anthropic key (`sk-ant-*`) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | IAM credentials for S3 |
| `AWS_S3_BUCKET` | `estate-executor-documents` (production bucket) |
| `AWS_REGION` | `us-east-1` |
| `STRIPE_SECRET_KEY` | `sk_live_*` — **not** `sk_test_*` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_*` from Stripe Dashboard → Webhooks |
| `RESEND_API_KEY` | Production Resend key |
| `SENTRY_DSN` | Backend Sentry DSN |
| `CORS_ORIGINS` / `BACKEND_CORS_ORIGINS` | `https://estate-executor.com` — **not** `localhost` |

### Integration-specific (if enabled)

| Variable | Production value |
|---|---|
| `CLIO_REDIRECT_URI` | `https://api.estate-executor.com/api/v1/integrations/clio/callback` |
| `QBO_ENVIRONMENT` | `production` — **not** `sandbox` |
| `QBO_REDIRECT_URI` | `https://api.estate-executor.com/api/v1/integrations/qbo/callback` |
| `DOCUSIGN_BASE_URL` | `https://account.docusign.com` — **not** `account-d.docusign.com` |
| `DOCUSIGN_AUTH_URL` | `https://account.docusign.com/oauth/auth` |
| `DOCUSIGN_TOKEN_URL` | `https://account.docusign.com/oauth/token` |
| `DOCUSIGN_API_BASE_URL` | `https://na*.docusign.net/restapi` (your account's base URI) |

### Monitoring

| Variable | Notes |
|---|---|
| `UPTIMEROBOT_READONLY_API_KEY` | See §10 |
| `ALERT_DEADLINE_FAILURE_WINDOW_HOURS` | `24` (default) |
| `NEXT_PUBLIC_SENTRY_DSN` | Frontend Sentry DSN |
| `NEXT_PUBLIC_APP_ENV` | `production` |
| `NEXT_PUBLIC_APP_VERSION` | Set from `package.json` during build |

### Verification

```bash
# Trigger the startup validation check directly
cd backend
python -c "
from app.core.config import settings
warnings = settings.validate_production_secrets()
if warnings:
    print('FAILURES:')
    for w in warnings: print(' -', w)
else:
    print('All production secrets validated OK')
"
```

- [ ] Zero warnings from `validate_production_secrets()`
- [ ] No `localhost` URLs in any variable
- [ ] No `*_test_*` or `*sandbox*` keys in any variable
- [ ] All secrets stored in secrets manager — not in `.env` files committed to git
- [ ] `S3_ENDPOINT_URL` is empty (only set for local MinIO)

---

## 4. Database Migration Verification

### Expected migration chain

The production database must be at the latest revision. As of this release, the migration chain is:

```
15ca5130e6b6  initial_models
  └─ a1b2c3d4e5f6  add_task_comments
     └─ b2c3d4e5f6a7  add_email_logs
        └─ c3d4e5f6a7b8  add_ai_usage_logs
           └─ d4e5f6a7b8c9  add_ai_feedback
              └─ e5f6a7b8c9d0  add_distributions
                 └─ f6a7b8c9d0e1  add_document_requests
                    └─ g7b8c9d0e1f2  add_dispute_resolution_fields
                       └─ h8c9d0e1f2g3  add_time_entries
                          └─ i9d0e1f2g3h4  add_subscriptions
                             └─ j0e1f2g3h4i5  add_integration_connections
                                └─ k1f2g3h4i5j6  add_signature_requests
                                   └─ l2g3h4i5j6k7  add_sso_configs
                                      └─ m3h4i5j6k7l8  add_api_keys_webhooks
                                         └─ n4i5j6k7l8m9  add_full_text_search
                                            └─ o5j6k7l8m9n0  add_privacy_requests
                                               └─ p6k7l8m9n0o1  add_performance_indexes_matviews  ← HEAD
```

### Pre-launch steps

```bash
# 1. Confirm current DB head
cd backend
alembic current

# 2. Check for pending migrations
alembic heads
alembic history --verbose | head -20

# 3. Take a manual RDS snapshot before running migrations
./scripts/db-backup.sh snapshot

# 4. Run migrations (uses DATABASE_URL_SYNC)
alembic upgrade head

# 5. Confirm applied
alembic current
# Expected: p6k7l8m9n0o1 (head)
```

- [ ] **BLOCKER** `alembic current` shows `p6k7l8m9n0o1 (head)` on production DB
- [ ] Manual snapshot taken immediately before migration run
- [ ] Migration completed with zero errors
- [ ] No pending migrations: `alembic heads` shows only one head
- [ ] Materialized views created: `SELECT matviewname FROM pg_matviews;` returns expected views
- [ ] Performance indexes created: `SELECT indexname FROM pg_indexes WHERE schemaname = 'public' ORDER BY indexname;` includes the new `ix_tasks_*`, `ix_assets_*`, `ix_deadlines_*`, `ix_events_*` indexes from the latest migration

---

## 5. Stripe Webhook Configuration

### Dashboard setup

1. Log in to [Stripe Dashboard](https://dashboard.stripe.com) → Developers → Webhooks
2. Add endpoint: `https://api.estate-executor.com/api/v1/webhooks/stripe`
3. Select events to listen to:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `checkout.session.completed`
4. Copy the **Signing secret** (`whsec_*`) → set as `STRIPE_WEBHOOK_SECRET`
5. Confirm `STRIPE_SECRET_KEY` is a **live** key (`sk_live_*`)

### Verification

```bash
# Send a test event from Stripe Dashboard → Webhooks → Send test event
# Or use Stripe CLI:
stripe trigger checkout.session.completed \
  --api-key sk_live_... \
  --webhook-endpoint https://api.estate-executor.com/api/v1/webhooks/stripe

# Confirm the webhook returned 200 in Stripe Dashboard → Webhooks → recent deliveries
```

- [ ] **BLOCKER** Webhook endpoint returns `200` for all event types in Stripe's test delivery
- [ ] `STRIPE_SECRET_KEY` is `sk_live_*` not `sk_test_*`
- [ ] `STRIPE_WEBHOOK_SECRET` matches the signing secret shown in Stripe Dashboard
- [ ] Stripe radar rules reviewed for production (no test-mode fraud rules active)

---

## 6. Auth0 Production Tenant Configuration

### Tenant

- [ ] **BLOCKER** Using **production** Auth0 tenant, not development tenant
- [ ] `AUTH0_DOMAIN` does not end in `-dev`, `-staging`, or similar
- [ ] Production tenant has its own M2M application and API audience configured

### Application settings

In Auth0 Dashboard → Applications → [Estate Executor API]:

- [ ] **Allowed Callback URLs** includes `https://estate-executor.com/callback`
- [ ] **Allowed Logout URLs** includes `https://estate-executor.com`
- [ ] **Allowed Web Origins** includes `https://estate-executor.com`
- [ ] **Token Expiration** is ≤ 86400s (24h); shorter is better
- [ ] **Refresh Token Rotation** is enabled
- [ ] **Absolute Expiration** on refresh tokens is set (e.g., 2592000s / 30 days)
- [ ] No `localhost` URLs remain in allowed callback / logout / origin lists

### API settings

In Auth0 Dashboard → APIs → [Estate Executor API]:

- [ ] `AUTH0_API_AUDIENCE` matches the API identifier: `https://api.estate-executor.com`
- [ ] RS256 algorithm selected (default)
- [ ] Token lifetime ≤ 86400s

### SSO / Enterprise connections (if applicable)

- [ ] SAML / OIDC enterprise connections tested end-to-end with a production firm
- [ ] Attribute mappings verified (`email`, `name`, `firm_id` claim propagation)
- [ ] Connection domains locked to correct email domains per firm

### Verification

```bash
# Test token issuance from production Auth0
curl -X POST https://YOUR_AUTH0_DOMAIN/oauth/token \
  -H 'Content-Type: application/json' \
  -d '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "audience": "https://api.estate-executor.com",
    "grant_type": "client_credentials"
  }'

# Test the token against the API
curl -H "Authorization: Bearer <token>" \
  https://api.estate-executor.com/api/v1/health/ready
```

- [ ] M2M token issued successfully by production Auth0 tenant
- [ ] Token accepted by the `/api/v1/health/ready` endpoint (returns 200, not 401)
- [ ] `E2E_MOCK_AUTH=false` confirmed in production environment

---

## 7. Email Sending Verification

### DNS records (for `estate-executor.com`)

Add these in your DNS provider. Values come from your Resend domain setup:

```
# SPF — authorize Resend to send on your behalf
TXT  estate-executor.com   "v=spf1 include:amazonses.com include:_spf.resend.com ~all"

# DKIM — Resend provides the CNAME records; add all three
CNAME resend._domainkey.estate-executor.com  → [provided by Resend]

# DMARC — start with p=none, tighten to p=quarantine / p=reject post-launch
TXT  _dmarc.estate-executor.com  "v=DMARC1; p=none; rua=mailto:dmarc@estate-executor.com; ruf=mailto:dmarc@estate-executor.com; fo=1"
```

### Verification

```bash
# SPF
dig TXT estate-executor.com | grep spf

# DKIM
dig CNAME resend._domainkey.estate-executor.com

# DMARC
dig TXT _dmarc.estate-executor.com

# Online tools
# https://mxtoolbox.com/spf.aspx
# https://dkimvalidator.com
# https://dmarcian.com/dmarc-inspector/
```

- [ ] SPF record includes `include:_spf.resend.com`
- [ ] All DKIM CNAME records resolve correctly
- [ ] DMARC record present (at minimum `p=none` with `rua` reporting address)
- [ ] `EMAIL_FROM` is set to `Estate Executor <notifications@estate-executor.com>` (production domain, not localhost)
- [ ] `RESEND_API_KEY` is a live Resend key, not a test key
- [ ] Send a real email to an external mailbox and verify:
  - [ ] Received without spam classification
  - [ ] DKIM signature passes (`Authentication-Results` header shows `dkim=pass`)
  - [ ] SPF passes (`spf=pass`)
  - [ ] Sender shows as `Estate Executor <notifications@estate-executor.com>`

---

## 8. Security Header Verification

The `SecurityHeadersMiddleware` in `app/core/security_middleware.py` sets these headers on every response. Verify they are present and correctly valued in production.

```bash
curl -sI https://api.estate-executor.com/api/v1/health | grep -E \
  "Strict-Transport|X-Content|X-Frame|Content-Security|Referrer|Permissions|X-Request"
```

| Header | Expected value |
|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | Present and restricts `default-src` to own origins |
| `Permissions-Policy` | Present (restricts camera, microphone, geolocation) |
| `X-Request-ID` | Present on every response (set by `RequestLoggingMiddleware`) |

```bash
# Check frontend security headers
curl -sI https://estate-executor.com | grep -E \
  "Cache-Control|X-Content|X-Frame|Referrer"

# Use securityheaders.com for a full grade
# https://securityheaders.com/?q=estate-executor.com&followRedirects=on
```

- [ ] `Strict-Transport-Security` present with `preload` directive
- [ ] `X-Frame-Options: DENY` (prevents clickjacking)
- [ ] `X-Content-Type-Options: nosniff`
- [ ] `Content-Security-Policy` present and not set to `unsafe-inline` on `script-src`
- [ ] securityheaders.com grade is A or A+
- [ ] **BLOCKER** CSRF is enabled: `CSRF_ENABLED=true` (default for non-test environments)
- [ ] **BLOCKER** Rate limiting is enabled: `RATE_LIMIT_ENABLED=true`
- [ ] CORS origins do not include `localhost` or `*`

---

## 9. Performance Baseline

Establish a baseline before launch so future regressions are detectable. Record results in the table below.

### Load test

Run with [k6](https://k6.io) from outside the VPC (simulates real user traffic):

```bash
# Install k6
brew install k6

# Run the baseline scenario (adjust VUs and duration as needed)
k6 run --vus 50 --duration 5m scripts/load-test.js \
  --env BASE_URL=https://api.estate-executor.com \
  --env AUTH_TOKEN="Bearer <valid_token>"
```

Key scenarios to test:
- `GET /api/v1/firms/{firm_id}/matters` — matter list
- `GET /api/v1/firms/{firm_id}/matters/{matter_id}` — dashboard
- `GET /api/v1/firms/{firm_id}/matters/{matter_id}/tasks` — task list
- `POST /api/v1/firms/{firm_id}/matters/{matter_id}/ai/*` — AI endpoints (concurrency-limited)

### Acceptance thresholds

| Metric | Target | Actual (record at launch) |
|---|---|---|
| P50 latency (API) | < 200ms | |
| P95 latency (API) | < 1000ms | |
| P99 latency (API) | < 5000ms | |
| Error rate (5xx) | < 0.1% | |
| Dashboard load (matter page) | < 2s | |
| DB connection pool utilization | < 60% under 50 VUs | |
| Redis cache hit rate | > 80% under sustained load | |

### Checks

- [ ] Load test run at target VU count with results recorded above
- [ ] No OOM errors or restarts in application logs during test
- [ ] `/api/v1/monitoring/metrics` P99 at peak load is within threshold
- [ ] RDS CPU < 70% during load test (check CloudWatch)
- [ ] Redis memory usage < 80% during load test

---

## 10. Monitoring & Alerting Verification

### Health endpoints

```bash
# Shallow liveness probe (always 200 if process is alive)
curl https://api.estate-executor.com/api/v1/health
# Expected: {"status": "ok"}

# Deep readiness probe (checks DB, Redis, S3, Claude API, Celery)
curl https://api.estate-executor.com/api/v1/health/ready
# Expected: {"status": "ok", "checks": {"database": {"status": "ok"}, ...}}
```

- [ ] `/api/v1/health` returns `{"status": "ok"}` with HTTP 200
- [ ] `/api/v1/health/ready` returns HTTP 200 with all checks passing
- [ ] `/api/v1/health/ready` returns HTTP 503 when Redis is taken offline (test this)

### Sentry

- [ ] Backend Sentry project created for `production` environment
- [ ] Frontend Sentry project created for `production` environment
- [ ] `SENTRY_DSN` set in backend; `NEXT_PUBLIC_SENTRY_DSN` set in frontend
- [ ] Trigger a test error and confirm it appears in Sentry within 60 seconds:
  ```bash
  # Backend — force a test exception (dev only, remove after test)
  curl -X POST https://api.estate-executor.com/api/v1/__sentry_test  # if endpoint exists
  # Or check Sentry Dashboard → Issues for any startup errors
  ```
- [ ] Alert rules configured in Sentry: notify on first occurrence of new issue types
- [ ] Issue assignment routing configured (backend issues → backend team, frontend → frontend team)

### UptimeRobot

Configure three monitors at [uptimerobot.com](https://uptimerobot.com):

| Monitor | URL | Type | Interval |
|---|---|---|---|
| API liveness | `https://api.estate-executor.com/api/v1/health` | HTTP(s) | 1 min |
| API readiness | `https://api.estate-executor.com/api/v1/health/ready` | HTTP(s) | 5 min |
| Frontend | `https://estate-executor.com` | HTTP(s) | 1 min |

- [ ] All three monitors created and showing **Up** status
- [ ] Alert contacts configured: email + Slack channel for all monitors
- [ ] `UPTIMEROBOT_READONLY_API_KEY` set in backend — `/api/v1/monitoring/alerts` will surface any down monitors as CRITICAL alerts

### Internal alert rules

Hit the alerts endpoint and confirm the system is healthy:

```bash
curl -H "Authorization: Bearer <token>" \
  https://api.estate-executor.com/api/v1/monitoring/alerts
# Expected: {"status": "ok", "alert_count": 0, "alerts": []}
```

- [ ] Alert endpoint returns `alert_count: 0` with a valid production token
- [ ] All six alert rules are active:
  - `high_error_rate` (threshold: 5%)
  - `high_p99_latency` (threshold: 5000ms)
  - `high_queue_depth` (threshold: 100)
  - `db_pool_saturation` (threshold: 80%)
  - `deadline_failures` (window: 24h)
  - `redis_connection_failure`
  - `uptime_monitor_down` (requires `UPTIMEROBOT_READONLY_API_KEY`)

### Business metrics dashboard

```bash
curl -H "Authorization: Bearer <token>" \
  https://api.estate-executor.com/api/v1/monitoring/business
```

- [ ] Endpoint returns HTTP 200 (not 401 — auth is now required)
- [ ] `matters.total`, `tasks.total`, `ai_usage_30d` fields present

### Log pipeline

- [ ] Structured JSON logs being shipped to log aggregation (CloudWatch Logs / Datadog / etc.)
- [ ] Log query for `"level": "ERROR"` returns results (not empty — confirm logs are reaching the destination)
- [ ] `request_id` field present in log entries (correlation ID propagation working)

---

## 11. Common Operational Runbooks

### 11.1 Deploy a new backend release

```bash
# 1. Build and push Docker image
docker build -t estate-executor-api:$VERSION .
docker push ECR_REPO/estate-executor-api:$VERSION

# 2. Run any pending migrations BEFORE deploying new code
DATABASE_URL_SYNC=... alembic upgrade head

# 3. Confirm migration is at head
alembic current

# 4. Update ECS task definition / Kubernetes deployment
# (use your CI/CD pipeline — do not deploy manually)

# 5. Confirm health after deploy
curl https://api.estate-executor.com/api/v1/health/ready
```

### 11.2 Roll back a bad deploy

```bash
# ECS: re-deploy the previous task definition revision
aws ecs update-service \
  --cluster estate-executor-production \
  --service api \
  --task-definition estate-executor-api:PREVIOUS_VERSION

# If the migration must also be rolled back:
alembic downgrade -1    # downgrade by one revision
# Verify
alembic current
```

### 11.3 Database restore (see full runbook)

See [docs/runbooks/backup-restoration.md](backup-restoration.md) for the complete procedure.

Quick reference:
```bash
# List available snapshots
./scripts/db-backup.sh list

# Restore from snapshot (creates new instance, does not overwrite production)
./scripts/db-backup.sh restore-snapshot --snapshot-id <id> --target-id estate-executor-restore-test

# Point-in-time recovery
./scripts/db-backup.sh restore-pitr --target-time "2026-03-24T02:00:00Z"
```

### 11.4 Flush Redis cache

```bash
# Flush only the app cache namespace (safe — does not clear Celery queues)
redis-cli -u $REDIS_URL --scan --pattern "cache:*" | xargs redis-cli -u $REDIS_URL DEL

# Verify cache is empty
redis-cli -u $REDIS_URL --scan --pattern "cache:*" | wc -l
```

### 11.5 Clear a stuck Celery queue

```bash
# Inspect queue depths
redis-cli -u $CELERY_BROKER_URL llen default
redis-cli -u $CELERY_BROKER_URL llen ai

# Purge a specific queue (drops all pending tasks — use with caution)
celery -A app.worker purge -Q default --force

# Restart workers
# (via ECS / k8s rolling restart)
```

### 11.6 Rotate a secret

1. Generate new secret value
2. Update in AWS Secrets Manager / Parameter Store
3. Trigger ECS service update (rolling restart picks up new env vars)
4. Verify new secret is active:
   ```bash
   curl https://api.estate-executor.com/api/v1/health/ready
   ```
5. Delete old secret version from Secrets Manager

### 11.7 Manually trigger a backup

```bash
./scripts/db-backup.sh snapshot
# Or via the monthly drill workflow:
gh workflow run backup-drill.yml --ref main
```

---

## 12. On-Call Rotation Setup

### Rotation schedule

| Week | Primary | Secondary |
|---|---|---|
| Rotation 1 | [Name] | [Name] |
| Rotation 2 | [Name] | [Name] |
| Rotation 3 | [Name] | [Name] |

Rotation shifts weekly, Sunday 00:00 UTC.

### Contact channels

| Channel | Purpose |
|---|---|
| PagerDuty / Opsgenie | Primary alert routing — pages primary on-call first, escalates to secondary after 10 min |
| `#incidents` Slack channel | All incident communication; bridge for async context |
| `#alerts` Slack channel | UptimeRobot + Sentry automated alerts (not actionable alone — check `#incidents`) |

### Alert routing

Wire UptimeRobot, Sentry, and the internal `/monitoring/alerts` endpoint to your on-call tool:

- **UptimeRobot** → Slack `#alerts` + PagerDuty webhook
- **Sentry** → `#alerts` for new issues; PagerDuty for `CRITICAL` severity or unhandled exceptions
- **Internal alerting** → Poll `/api/v1/monitoring/alerts` from your observability platform every 5 min; page on non-empty `alerts` array

### On-call expectations

- Acknowledge page within **15 minutes** (business hours) / **30 minutes** (nights/weekends)
- Begin active triage within **30 minutes** of acknowledgment
- Update `#incidents` every 30 minutes during active incidents
- Write a post-mortem within **48 hours** of resolution for any P1 incident

---

## 13. Incident Response Procedure

### Severity definitions

| Severity | Definition | Response time | Examples |
|---|---|---|---|
| **P1 — Critical** | Production is down or data loss is occurring | 15 min acknowledge, immediate response | Site unreachable, DB corruption, auth completely broken |
| **P2 — High** | Major feature broken for all users | 30 min acknowledge | Dashboard won't load, AI features down, payments broken |
| **P3 — Medium** | Feature degraded for some users | 2h acknowledge | Slow queries for specific matters, email delivery delays |
| **P4 — Low** | Minor issue or cosmetic defect | Next business day | UI glitch, non-critical log noise |

### P1 / P2 response steps

```
1. ACKNOWLEDGE
   - Ack the PagerDuty/Opsgenie alert within SLA
   - Post in #incidents: "Acknowledged [ALERT NAME]. Investigating."

2. ASSESS
   - Check https://api.estate-executor.com/api/v1/health/ready
   - Check https://api.estate-executor.com/api/v1/monitoring/alerts
   - Check Sentry for recent error spike
   - Check UptimeRobot for which monitors are down
   - Check CloudWatch / Datadog for CPU, memory, DB connections

3. COMMUNICATE
   - Post incident severity and initial findings in #incidents within 15 min
   - If P1: notify stakeholders via [escalation channel]
   - Update status page if one exists

4. CONTAIN
   - If bad deploy: roll back (see §11.2)
   - If DB issue: check RDS console; failover to Multi-AZ standby if needed
   - If Redis down: check ElastiCache; the app is fail-open on cache (degrades gracefully)
   - If Celery queue backed up: inspect and purge if needed (see §11.5)

5. RESOLVE
   - Confirm https://api.estate-executor.com/api/v1/health/ready returns 200
   - Confirm /monitoring/alerts returns alert_count: 0
   - Confirm UptimeRobot shows all monitors Up
   - Post "RESOLVED" in #incidents with time to resolution

6. POST-MORTEM (P1 and P2)
   - Write post-mortem within 48h using the template below
   - Share in #incidents and schedule a 30-min review meeting
```

### Post-mortem template

```markdown
## Incident Post-Mortem — [DATE] [BRIEF TITLE]

**Severity:** P1 / P2
**Duration:** HH:MM (start → end UTC)
**Impact:** [Who was affected and how]

### Timeline (UTC)
- HH:MM — [First symptom / alert]
- HH:MM — [Acknowledged]
- HH:MM — [Root cause identified]
- HH:MM — [Mitigation applied]
- HH:MM — [Resolved]

### Root Cause
[What went wrong and why]

### Contributing Factors
[What made the issue worse or harder to detect]

### What Went Well
[Detection speed, communication, tooling that helped]

### Action Items
| Item | Owner | Due |
|---|---|---|
| [Preventive fix] | [Name] | [Date] |
| [Monitoring improvement] | [Name] | [Date] |
```

---

## Final Go / No-Go

Complete this immediately before flipping DNS / enabling traffic.

| # | Check | Status |
|---|---|---|
| 1 | All BLOCKER items above are checked | [ ] |
| 2 | `validate_production_secrets()` returns zero warnings | [ ] |
| 3 | `/api/v1/health/ready` returns 200 with all checks passing | [ ] |
| 4 | `alembic current` shows `p6k7l8m9n0o1 (head)` | [ ] |
| 5 | Stripe webhook verified with live key | [ ] |
| 6 | Auth0 production tenant verified, no localhost callbacks | [ ] |
| 7 | Email DNS records verified (SPF + DKIM + DMARC) | [ ] |
| 8 | Security headers verified (A+ on securityheaders.com) | [ ] |
| 9 | Load test run, results within thresholds | [ ] |
| 10 | UptimeRobot monitors created and showing Up | [ ] |
| 11 | Sentry receiving events in production environment | [ ] |
| 12 | `/api/v1/monitoring/alerts` returns `alert_count: 0` | [ ] |
| 13 | On-call rotation configured, PagerDuty routing tested | [ ] |
| 14 | Manual RDS snapshot taken immediately before DNS cutover | [ ] |

**Go / No-Go decision:** ____________________
**Signed off by:** ____________________
**Date/Time (UTC):** ____________________
