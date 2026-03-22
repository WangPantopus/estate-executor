# Estate Executor OS — Engineering Design Document

**Version:** 1.0  
**Status:** Draft  
**Author:** Engineering  
**Date:** March 2026  
**Classification:** Confidential

---

## Table of Contents

1. [Overview & Goals](#1-overview--goals)
2. [System Architecture](#2-system-architecture)
3. [Data Model](#3-data-model)
4. [API Design](#4-api-design)
5. [Core Subsystems](#5-core-subsystems)
6. [AI Pipeline](#6-ai-pipeline)
7. [Authentication, Authorization & Multi-Tenancy](#7-authentication-authorization--multi-tenancy)
8. [Real-Time & Notification System](#8-real-time--notification-system)
9. [Document Management](#9-document-management)
10. [Compliance Calendar Engine](#10-compliance-calendar-engine)
11. [Beneficiary Portal & Family Communication](#11-beneficiary-portal--family-communication)
12. [Integrations Architecture](#12-integrations-architecture)
13. [Infrastructure & Deployment](#13-infrastructure--deployment)
14. [Security & Compliance](#14-security--compliance)
15. [Observability & Operations](#15-observability--operations)
16. [Performance Requirements](#16-performance-requirements)
17. [Phased Implementation Plan](#17-phased-implementation-plan)
18. [Risk Register & Technical Mitigations](#18-risk-register--technical-mitigations)
19. [Open Questions & ADRs](#19-open-questions--adrs)
20. [Appendix](#20-appendix)

---

## 1. Overview & Goals

### 1.1 Product Context

Estate Executor OS is a B2B SaaS workflow platform for the estate administration period — the weeks-to-years process between a triggering event (death or incapacity) and final asset distribution. It serves as the coordination operating system for estate attorneys, RIAs, trust companies, executors, and beneficiaries.

The platform is **not** a document vault, estate planning tool, or fiduciary accounting system. It is a multi-party action system: coordinating tasks, deadlines, stakeholders, documents, and decisions across all participants involved in settling an estate.

### 1.2 Engineering Goals

- **Multi-party coordination as a first-class concern.** Every entity, endpoint, and UI surface must account for multiple concurrent users with different roles, permissions, and information needs operating on the same matter.
- **Audit-completeness.** Every state mutation across every entity must produce an immutable event log entry. The system must be capable of reconstructing the full history of any matter at any point in time.
- **Deadline integrity.** The compliance calendar is a safety-critical subsystem. Missed deadlines (IRS filings, creditor windows, probate filings) carry legal and financial consequences for end users. The system must guarantee reliable deadline tracking and notification delivery.
- **Extensible workflow engine.** Estate administration varies dramatically by state jurisdiction, estate type, asset profile, and trust structure. The task/workflow engine must support configurable templates without requiring code changes.
- **AI as accelerator, not authority.** All AI-generated outputs (document classification, data extraction, letter drafts, clause detection) are treated as suggestions requiring human confirmation. No AI output may alter matter state without explicit user action.
- **Security posture appropriate for fiduciary data.** Estate data includes PII, financial account details, SSNs, legal documents, and family-sensitive information. The system must be designed from day one for SOC 2 Type II compliance.

### 1.3 Scale Assumptions (18-Month Horizon)

| Dimension | Assumption |
|---|---|
| Firms (tenants) | Up to 500 |
| Concurrent matters (system-wide) | Up to 15,000 |
| Stakeholders per matter | 3–15 |
| Tasks per matter | 50–300 |
| Documents per matter | 20–200 |
| Assets per matter | 5–100 |
| Peak concurrent users | ~500 |
| AI extraction requests/day | ~2,000 |

These figures inform infrastructure sizing and database indexing strategy but are not hard limits. The architecture should scale horizontally beyond these numbers.

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                   │
│                                                                          │
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────────────────────────┐  │
│  │  Web App    │  │  Mobile App       │  │  Beneficiary Portal         │  │
│  │  (Next.js)  │  │  (React Native)   │  │  (Next.js, read-heavy)     │  │
│  └──────┬──────┘  └────────┬─────────┘  └─────────────┬───────────────┘  │
└─────────┼──────────────────┼──────────────────────────┼──────────────────┘
          │                  │                          │
          ▼                  ▼                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY / EDGE                              │
│                     (Vercel Edge / Cloudflare)                            │
│             Rate limiting, auth token validation, routing                 │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
┌──────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│   Core API       │  │   AI Service         │  │   Notification       │
│   (Node/Express) │  │   (Node worker)      │  │   Service            │
│                  │  │                      │  │   (Node worker)      │
│  - Matter CRUD   │  │  - Doc classification│  │  - Email dispatch    │
│  - Task engine   │  │  - Data extraction   │  │  - In-app push       │
│  - Asset mgmt    │  │  - Clause extraction │  │  - Deadline triggers │
│  - Stakeholders  │  │  - Letter drafting   │  │  - Webhook delivery  │
│  - Documents     │  │  - Anomaly detection │  │                      │
│  - Events/audit  │  │                      │  │                      │
└────────┬─────────┘  └──────────┬───────────┘  └──────────┬───────────┘
         │                       │                         │
         ▼                       ▼                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                      │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  ┌────────────────┐  │
│  │  PostgreSQL  │  │  Redis       │  │  S3 / GCS │  │  Job Queue     │  │
│  │  (Primary)   │  │  (Cache +    │  │  (Docs)   │  │  (BullMQ /     │  │
│  │              │  │   Pub/Sub)   │  │           │  │   Redis)       │  │
│  └──────────────┘  └──────────────┘  └───────────┘  └────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     EXTERNAL SERVICES                                    │
│                                                                          │
│  Anthropic Claude API  ·  Auth0/Clerk  ·  Stripe  ·  Resend/Postmark    │
│  DocuSign  ·  Clio API  ·  QuickBooks API  ·  Estateably API            │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Service Boundaries

The system is a **modular monolith** deployed as a single Node.js application with clear internal module boundaries, plus two separately deployed worker processes for AI and notifications. This approach optimizes for solo-founder velocity while maintaining the ability to extract services later.

| Module | Responsibility | Deployment |
|---|---|---|
| `core-api` | HTTP endpoints, request validation, business logic orchestration | Primary server |
| `workflow-engine` | Task generation, dependency resolution, state machine transitions | Library within core-api |
| `ai-service` | Document processing pipeline, Claude API calls, extraction jobs | Separate worker process |
| `notification-service` | Email dispatch, in-app notifications, deadline monitoring | Separate worker process |
| `event-store` | Immutable event logging, audit trail queries | Library within core-api |

### 2.3 Key Architectural Decisions

**Why a modular monolith instead of microservices:** A solo founder managing the full stack benefits from a single deployment unit, shared type definitions, and simplified local development. The module boundaries are designed so that extraction to separate services is straightforward if needed post-seed.

**Why separate worker processes for AI and notifications:** Both are long-running, I/O-bound workloads that should not block API request processing. AI extraction jobs may take 10–60 seconds per document. Notification delivery involves external SMTP/API calls with retry logic. Isolating these as workers connected via a job queue (BullMQ backed by Redis) keeps the API responsive.

**Why PostgreSQL as the sole primary datastore:** The domain is inherently relational — matters contain tasks which reference assets which link to documents which belong to stakeholders. PostgreSQL's row-level security, JSONB columns (for flexible task metadata and template configuration), and mature ecosystem make it the right single-database choice at this scale.

---

## 3. Data Model

### 3.1 Entity-Relationship Overview

```
Firm (tenant)
 └── Matter
      ├── Stakeholder (junction: user ↔ matter ↔ role)
      ├── Task
      │    ├── TaskDependency
      │    ├── TaskDocument (junction: task ↔ document)
      │    └── TaskComment
      ├── Asset
      │    ├── AssetDocument (junction: asset ↔ document)
      │    └── AssetValuation
      ├── Entity (trust, LLC, FLP)
      │    └── EntityAsset (junction: entity ↔ asset)
      ├── Document
      │    └── DocumentVersion
      ├── Deadline
      ├── Communication (family messages)
      └── Event (immutable audit log)

User (global, cross-firm)
 └── FirmMembership (junction: user ↔ firm ↔ firm-level role)
```

### 3.2 Core Table Definitions

#### `firms`

```sql
CREATE TABLE firms (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    type            TEXT NOT NULL CHECK (type IN ('law_firm', 'ria', 'trust_company', 'family_office', 'other')),
    subscription_tier TEXT NOT NULL DEFAULT 'starter',
    stripe_customer_id TEXT,
    settings        JSONB NOT NULL DEFAULT '{}',
    white_label     JSONB,  -- branding config for enterprise
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### `users`

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_provider_id TEXT NOT NULL UNIQUE,  -- Auth0/Clerk external ID
    email           TEXT NOT NULL UNIQUE,
    full_name       TEXT NOT NULL,
    phone           TEXT,
    avatar_url      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### `firm_memberships`

```sql
CREATE TABLE firm_memberships (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firm_id         UUID NOT NULL REFERENCES firms(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    firm_role       TEXT NOT NULL CHECK (firm_role IN ('owner', 'admin', 'member')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (firm_id, user_id)
);
```

#### `matters`

```sql
CREATE TABLE matters (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firm_id         UUID NOT NULL REFERENCES firms(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,  -- e.g., "Estate of John Smith"
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'on_hold', 'closed', 'archived')),
    estate_type     TEXT NOT NULL CHECK (estate_type IN (
                        'testate_probate', 'intestate_probate',
                        'trust_administration', 'conservatorship',
                        'mixed_probate_trust', 'other'
                    )),
    jurisdiction_state TEXT NOT NULL,  -- two-letter state code
    date_of_death   DATE,
    date_of_incapacity DATE,
    decedent_name   TEXT NOT NULL,
    decedent_ssn_encrypted BYTEA,  -- AES-256 encrypted
    estimated_value NUMERIC(15,2),
    phase           TEXT NOT NULL DEFAULT 'immediate'
                    CHECK (phase IN ('immediate', 'administration', 'distribution', 'closing')),
    settings        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at       TIMESTAMPTZ
);

CREATE INDEX idx_matters_firm_id ON matters(firm_id);
CREATE INDEX idx_matters_status ON matters(status) WHERE status = 'active';
CREATE INDEX idx_matters_jurisdiction ON matters(jurisdiction_state);
```

#### `stakeholders`

```sql
CREATE TABLE stakeholders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    matter_id       UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id),  -- NULL for invited-but-unregistered
    email           TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN (
                        'matter_admin', 'professional', 'executor_trustee',
                        'beneficiary', 'read_only'
                    )),
    relationship    TEXT,  -- e.g., "estate attorney", "CPA", "spouse", "child"
    permissions     JSONB NOT NULL DEFAULT '{}',
    invite_status   TEXT NOT NULL DEFAULT 'pending'
                    CHECK (invite_status IN ('pending', 'accepted', 'revoked')),
    invite_token    TEXT UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (matter_id, email)
);

CREATE INDEX idx_stakeholders_matter_id ON stakeholders(matter_id);
CREATE INDEX idx_stakeholders_user_id ON stakeholders(user_id);
```

#### `tasks`

```sql
CREATE TABLE tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    matter_id       UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    parent_task_id  UUID REFERENCES tasks(id),  -- for subtasks
    template_key    TEXT,  -- reference to task template library
    title           TEXT NOT NULL,
    description     TEXT,
    instructions    TEXT,  -- plain-language instructions for non-professional users
    phase           TEXT NOT NULL CHECK (phase IN (
                        'immediate', 'asset_inventory', 'notification',
                        'probate_filing', 'tax', 'transfer_distribution',
                        'family_communication', 'closing', 'custom'
                    )),
    status          TEXT NOT NULL DEFAULT 'not_started'
                    CHECK (status IN (
                        'not_started', 'in_progress', 'blocked',
                        'complete', 'waived', 'cancelled'
                    )),
    priority        TEXT NOT NULL DEFAULT 'normal'
                    CHECK (priority IN ('critical', 'normal', 'informational')),
    assigned_to     UUID REFERENCES stakeholders(id),
    due_date        DATE,
    due_date_rule   JSONB,  -- e.g., {"relative_to": "date_of_death", "offset_months": 9}
    requires_document BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at    TIMESTAMPTZ,
    completed_by    UUID REFERENCES stakeholders(id),
    sort_order      INTEGER NOT NULL DEFAULT 0,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tasks_matter_id ON tasks(matter_id);
CREATE INDEX idx_tasks_assigned_to ON tasks(assigned_to);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due_date ON tasks(due_date) WHERE status NOT IN ('complete', 'waived', 'cancelled');
```

#### `task_dependencies`

```sql
CREATE TABLE task_dependencies (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id             UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on_task_id  UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    CHECK (task_id != depends_on_task_id),
    UNIQUE (task_id, depends_on_task_id)
);
```

#### `assets`

```sql
CREATE TABLE assets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    matter_id       UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    asset_type      TEXT NOT NULL CHECK (asset_type IN (
                        'real_estate', 'bank_account', 'brokerage_account',
                        'retirement_account', 'life_insurance', 'business_interest',
                        'vehicle', 'digital_asset', 'personal_property',
                        'receivable', 'other'
                    )),
    title           TEXT NOT NULL,
    description     TEXT,
    institution     TEXT,  -- bank name, brokerage name, etc.
    account_number_encrypted BYTEA,
    ownership_type  TEXT CHECK (ownership_type IN (
                        'in_trust', 'joint_tenancy', 'community_property',
                        'pod_tod', 'individual', 'business_owned', 'other'
                    )),
    transfer_mechanism TEXT CHECK (transfer_mechanism IN (
                        'probate', 'trust_administration', 'beneficiary_designation',
                        'joint_survivorship', 'other'
                    )),
    status          TEXT NOT NULL DEFAULT 'discovered'
                    CHECK (status IN ('discovered', 'valued', 'transferred', 'distributed')),
    date_of_death_value NUMERIC(15,2),
    current_estimated_value NUMERIC(15,2),
    final_appraised_value NUMERIC(15,2),
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_assets_matter_id ON assets(matter_id);
CREATE INDEX idx_assets_type ON assets(asset_type);
```

#### `entities`

```sql
CREATE TABLE entities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    matter_id       UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    entity_type     TEXT NOT NULL CHECK (entity_type IN (
                        'revocable_trust', 'irrevocable_trust', 'llc',
                        'flp', 'corporation', 'foundation', 'other'
                    )),
    name            TEXT NOT NULL,
    trustee         TEXT,
    successor_trustee TEXT,
    trigger_conditions JSONB,  -- conditions under which successor trustee takes over
    funding_status  TEXT DEFAULT 'unknown'
                    CHECK (funding_status IN ('unknown', 'fully_funded', 'partially_funded', 'unfunded')),
    distribution_rules JSONB,  -- structured rules for who gets what
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE entity_assets (
    entity_id   UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    asset_id    UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    PRIMARY KEY (entity_id, asset_id)
);
```

#### `documents`

```sql
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    matter_id       UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    uploaded_by     UUID NOT NULL REFERENCES stakeholders(id),
    filename        TEXT NOT NULL,
    storage_key     TEXT NOT NULL,  -- S3/GCS object key
    mime_type       TEXT NOT NULL,
    size_bytes      BIGINT NOT NULL,
    doc_type        TEXT,  -- AI-classified: 'death_certificate', 'deed', 'account_statement', etc.
    doc_type_confidence REAL,  -- 0.0–1.0
    doc_type_confirmed BOOLEAN NOT NULL DEFAULT FALSE,  -- human-verified
    ai_extracted_data JSONB,  -- structured data extracted by AI pipeline
    current_version INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE document_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    storage_key     TEXT NOT NULL,
    size_bytes      BIGINT NOT NULL,
    uploaded_by     UUID NOT NULL REFERENCES stakeholders(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, version_number)
);

-- Junction tables
CREATE TABLE task_documents (
    task_id     UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, document_id)
);

CREATE TABLE asset_documents (
    asset_id    UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    PRIMARY KEY (asset_id, document_id)
);

CREATE INDEX idx_documents_matter_id ON documents(matter_id);
```

#### `deadlines`

```sql
CREATE TABLE deadlines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    matter_id       UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    task_id         UUID REFERENCES tasks(id),
    title           TEXT NOT NULL,
    description     TEXT,
    due_date        DATE NOT NULL,
    source          TEXT NOT NULL CHECK (source IN ('auto', 'manual')),
    rule            JSONB,  -- for auto-generated: {"type": "federal_estate_tax", "base": "date_of_death", "months": 9}
    status          TEXT NOT NULL DEFAULT 'upcoming'
                    CHECK (status IN ('upcoming', 'completed', 'extended', 'missed')),
    assigned_to     UUID REFERENCES stakeholders(id),
    reminder_config JSONB NOT NULL DEFAULT '{"days_before": [30, 7, 1]}',
    last_reminder_sent TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_deadlines_matter_id ON deadlines(matter_id);
CREATE INDEX idx_deadlines_due_date ON deadlines(due_date) WHERE status = 'upcoming';
```

#### `events` (Immutable Audit Log)

```sql
CREATE TABLE events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    matter_id       UUID NOT NULL,
    actor_id        UUID,  -- stakeholder who performed the action; NULL for system events
    actor_type      TEXT NOT NULL CHECK (actor_type IN ('user', 'system', 'ai')),
    entity_type     TEXT NOT NULL,  -- 'task', 'asset', 'document', 'stakeholder', 'matter', etc.
    entity_id       UUID NOT NULL,
    action          TEXT NOT NULL,  -- 'created', 'updated', 'completed', 'uploaded', etc.
    changes         JSONB,  -- diff of what changed: {"status": {"from": "not_started", "to": "complete"}}
    metadata        JSONB NOT NULL DEFAULT '{}',
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- This table is append-only. No UPDATE or DELETE operations are permitted at the application layer.
-- Partitioned by month for query performance and archival.
CREATE INDEX idx_events_matter_id ON events(matter_id);
CREATE INDEX idx_events_entity ON events(entity_type, entity_id);
CREATE INDEX idx_events_created_at ON events(created_at);
```

#### `communications`

```sql
CREATE TABLE communications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    matter_id       UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    sender_id       UUID NOT NULL REFERENCES stakeholders(id),
    type            TEXT NOT NULL CHECK (type IN (
                        'message', 'milestone_notification', 'distribution_notice',
                        'document_request', 'dispute_flag'
                    )),
    subject         TEXT,
    body            TEXT NOT NULL,
    visibility      TEXT NOT NULL DEFAULT 'all_stakeholders'
                    CHECK (visibility IN ('all_stakeholders', 'professionals_only', 'specific')),
    visible_to      UUID[],  -- specific stakeholder IDs when visibility = 'specific'
    acknowledged_by UUID[],  -- for distribution notices requiring acknowledgment
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_communications_matter_id ON communications(matter_id);
```

### 3.3 Multi-Tenancy Strategy

Data isolation is enforced through a **firm_id foreign key chain**. Every query path from the API passes through firm-scoped middleware:

```
firm_id → matter.firm_id → (all child entities inherit matter_id scope)
```

At the PostgreSQL level, Row-Level Security (RLS) policies serve as a defense-in-depth layer:

```sql
ALTER TABLE matters ENABLE ROW LEVEL SECURITY;

CREATE POLICY firm_isolation ON matters
    USING (firm_id = current_setting('app.current_firm_id')::UUID);
```

The API sets `app.current_firm_id` via `SET LOCAL` at the start of every request transaction after validating the authenticated user's firm membership. This means even a bug in application-level filtering cannot leak cross-tenant data.

---

## 4. API Design

### 4.1 REST API Structure

The API follows a resource-oriented REST design. All endpoints are prefixed with `/api/v1`.

#### Resource Hierarchy

```
/firms/:firmId
/firms/:firmId/matters
/firms/:firmId/matters/:matterId
/firms/:firmId/matters/:matterId/tasks
/firms/:firmId/matters/:matterId/tasks/:taskId
/firms/:firmId/matters/:matterId/assets
/firms/:firmId/matters/:matterId/assets/:assetId
/firms/:firmId/matters/:matterId/entities
/firms/:firmId/matters/:matterId/stakeholders
/firms/:firmId/matters/:matterId/documents
/firms/:firmId/matters/:matterId/deadlines
/firms/:firmId/matters/:matterId/communications
/firms/:firmId/matters/:matterId/events
```

#### Key Endpoint Examples

**Matter Operations**

```
POST   /firms/:firmId/matters                    Create new matter (triggers task generation)
GET    /firms/:firmId/matters                    List matters (with filters: status, phase, search)
GET    /firms/:firmId/matters/:matterId          Get matter dashboard (aggregated view)
PATCH  /firms/:firmId/matters/:matterId          Update matter details
POST   /firms/:firmId/matters/:matterId/close    Close matter (validates all required tasks complete)
```

**Task Operations**

```
GET    /firms/:firmId/matters/:matterId/tasks              List tasks (filters: phase, status, assignee)
POST   /firms/:firmId/matters/:matterId/tasks              Create custom task
PATCH  /firms/:firmId/matters/:matterId/tasks/:taskId      Update task (status, assignment, due date)
POST   /firms/:firmId/matters/:matterId/tasks/:taskId/complete   Mark complete (validates doc requirements)
POST   /firms/:firmId/matters/:matterId/tasks/:taskId/waive      Waive task with reason
POST   /firms/:firmId/matters/:matterId/tasks/generate     Re-run task generation for updated matter config
```

**Document Operations**

```
POST   /firms/:firmId/matters/:matterId/documents/upload-url   Get pre-signed upload URL
POST   /firms/:firmId/matters/:matterId/documents              Register uploaded document (triggers AI pipeline)
GET    /firms/:firmId/matters/:matterId/documents/:docId/download   Get pre-signed download URL
POST   /firms/:firmId/matters/:matterId/documents/:docId/confirm-type   Confirm AI classification
POST   /firms/:firmId/matters/:matterId/documents/request    Send document request to stakeholder
POST   /firms/:firmId/matters/:matterId/documents/bulk-download  Generate ZIP of all/filtered documents
```

**AI Operations**

```
POST   /firms/:firmId/matters/:matterId/ai/classify/:docId     Trigger document classification
POST   /firms/:firmId/matters/:matterId/ai/extract/:docId      Trigger data extraction
POST   /firms/:firmId/matters/:matterId/ai/draft-letter        Generate notification letter
POST   /firms/:firmId/matters/:matterId/ai/suggest-tasks       Get AI-suggested additional tasks
POST   /firms/:firmId/matters/:matterId/ai/detect-anomalies    Run anomaly detection across registry
```

### 4.2 Request/Response Conventions

- All responses follow a consistent envelope: `{ data, meta?, errors? }`.
- List endpoints support cursor-based pagination: `?cursor=...&limit=50`.
- Filters are query parameters: `?status=in_progress&phase=immediate&assigned_to=...`.
- All mutating operations return the updated entity plus the generated event ID.
- Error responses use RFC 7807 Problem Details format.

### 4.3 Webhook API (Outbound)

For integrations, the platform fires webhooks on key events:

```
matter.created, matter.closed
task.completed, task.overdue
document.uploaded, document.classified
deadline.approaching, deadline.missed
stakeholder.invited, stakeholder.accepted
distribution.recorded
```

Webhook delivery uses exponential backoff retry (1s, 10s, 60s, 300s, 3600s) with HMAC-SHA256 signature verification.

---

## 5. Core Subsystems

### 5.1 Workflow Engine

The workflow engine is the central subsystem. It manages the lifecycle of tasks within a matter.

#### 5.1.1 Task Generation Pipeline

When a new matter is created, the system runs a task generation pipeline:

```
MatterCreationInput
  ├── estate_type (testate_probate | trust_administration | mixed | ...)
  ├── jurisdiction_state
  ├── asset_types_present (initial selection by user)
  └── flags (e.g., has_business_interest, multi_state, minor_beneficiaries)
         │
         ▼
   ┌─────────────────────┐
   │  Template Resolver   │
   │                      │
   │  Loads base template │
   │  for estate_type,    │
   │  applies state-      │
   │  specific overlays,  │
   │  includes conditional│
   │  tasks by flags      │
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  Date Calculator     │
   │                      │
   │  Resolves relative   │
   │  due dates from      │
   │  date_of_death and   │
   │  jurisdiction rules  │
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  Task Materializer   │
   │                      │
   │  Creates task rows,  │
   │  dependency edges,   │
   │  and linked deadline │
   │  entries             │
   └──────────┬──────────┘
              │
              ▼
     [tasks], [deadlines], [events]
```

#### 5.1.2 Task State Machine

```
                ┌─────────────┐
                │ not_started  │
                └──────┬──────┘
                       │ start
                       ▼
                ┌─────────────┐      block
                │ in_progress  │ ──────────► ┌─────────┐
                └──────┬──────┘              │ blocked │
                       │ complete            └────┬────┘
                       │                         │ unblock
                       │    ◄────────────────────┘
                       ▼
                ┌─────────────┐
                │  complete    │ (terminal)
                └─────────────┘

  Any non-terminal state ──► waived (terminal, requires reason)
  Any non-terminal state ──► cancelled (terminal, system only)
```

Every state transition produces an event log entry. The `complete` transition enforces pre-conditions:
- If `requires_document = TRUE`, at least one document must be linked via `task_documents`.
- All upstream dependencies (via `task_dependencies`) must be in a terminal state (`complete` or `waived`).

#### 5.1.3 Task Template Library

Templates are stored as JSONB configuration, versioned and managed through an admin interface (Phase 2) or seed data (Phase 0–1).

```typescript
interface TaskTemplate {
  key: string;                   // e.g., "obtain_death_certificates"
  title: string;
  description: string;
  instructions: string;          // plain-language for executors
  phase: TaskPhase;
  priority: TaskPriority;
  default_assignee_role: StakeholderRole;
  requires_document: boolean;
  due_date_rule?: {
    relative_to: 'date_of_death' | 'matter_created' | 'task_completed';
    reference_task_key?: string;  // for task_completed
    offset_days?: number;
    offset_months?: number;
  };
  dependencies?: string[];       // keys of tasks that must complete first
  conditions?: {                 // only include if conditions match
    estate_types?: EstateType[];
    states?: string[];
    asset_types?: AssetType[];
    flags?: string[];
  };
  subtasks?: TaskTemplate[];
}
```

### 5.2 Asset & Entity Management

#### Asset Lifecycle

```
discovered → valued → transferred → distributed
```

Each transition is a task-driven action — the asset does not move to "valued" until the relevant appraisal/valuation task is completed and a valuation figure is entered.

#### Entity-Asset Ownership Graph

The `entities` and `entity_assets` tables form a directed graph showing which legal entities own which assets. The API exposes a `GET .../matters/:id/entity-map` endpoint that returns the full graph for visualization:

```typescript
interface EntityMap {
  entities: Array<{
    id: string;
    name: string;
    type: EntityType;
    trustee: string;
    funding_status: FundingStatus;
    assets: Array<{ id: string; title: string; value: number }>;
  }>;
  unassigned_assets: Array<{ id: string; title: string }>;  // assets not in any entity
  pour_over_candidates: Array<{ id: string; title: string }>;  // probate → trust flow
}
```

---

## 6. AI Pipeline

### 6.1 Architecture

AI operations are asynchronous. A document upload or manual trigger enqueues a job to the AI worker via BullMQ. The worker calls the Anthropic Claude API, processes results, and writes back to PostgreSQL.

```
[Upload/Trigger] → [BullMQ Queue] → [AI Worker] → [Claude API] → [DB Write] → [Event + Notification]
```

### 6.2 Document Classification

**Input:** Document binary (PDF, image, Word doc) + matter context.

**Process:**
1. Extract text from document (PDF via `pdf-parse`, images via Tesseract OCR, DOCX via `mammoth`).
2. Send extracted text (truncated to relevant portions) to Claude with a classification prompt.
3. Claude returns a document type and confidence score.

**Prompt structure (simplified):**

```
You are classifying a document uploaded to an estate administration matter.

The document text is:
<document_text>{extracted_text}</document_text>

Classify this document into exactly one of these categories:
- death_certificate
- will
- trust_document
- deed
- account_statement
- insurance_policy
- court_filing
- tax_return
- appraisal
- correspondence
- other

Respond with JSON: {"type": "...", "confidence": 0.0-1.0, "reasoning": "..."}
```

**Output:** Updates `documents.doc_type`, `documents.doc_type_confidence`. Flagged as unconfirmed until a professional user verifies.

### 6.3 Data Extraction

For classified documents, a second pipeline extracts structured fields:

| Document Type | Extracted Fields |
|---|---|
| `account_statement` | institution, account_number (last 4), account_type, balance, as_of_date |
| `deed` | property_address, grantee, recording_date, parcel_number |
| `insurance_policy` | carrier, policy_number, face_value, beneficiary, policy_type |
| `trust_document` | trust_name, trustee, successor_trustee, distribution_provisions (summary), key_clauses |
| `appraisal` | property_description, appraised_value, appraisal_date, appraiser |

Extracted data is stored in `documents.ai_extracted_data` as JSONB and surfaced to the user as pre-filled fields they can accept, edit, or reject when adding/updating asset registry entries.

### 6.4 Letter Drafting

The AI generates institution notification letters from asset data:

**Input:** Asset record (institution, account info) + matter context (decedent name, executor name, date of death, case number).

**Output:** Draft letter text (not sent — presented to the user for review and download/print).

### 6.5 Anomaly Detection

Periodic job (or on-demand) that compares the full set of AI-extracted data across all documents against the asset registry to flag:
- Accounts mentioned in documents but not in the registry.
- Institutions referenced in correspondence that don't match any registered asset.
- Discrepancies in values (e.g., statement balance vs. registered value differs by >10%).

### 6.6 Safety and Accuracy Controls

- All AI outputs are labeled as "AI Suggested" in the UI with explicit "Confirm" / "Reject" actions.
- No AI output writes directly to primary entity tables — all outputs go through a staging JSONB field or a suggestions queue.
- Extraction confidence below 0.7 triggers a "Low Confidence" flag for mandatory human review.
- AI usage is logged in the event table with `actor_type = 'ai'` for full traceability.
- Rate limiting: per-firm and per-matter limits on AI calls to prevent abuse and manage API costs.

---

## 7. Authentication, Authorization & Multi-Tenancy

### 7.1 Authentication

Authentication is delegated to Auth0 (or Clerk as alternative). The platform does not store passwords.

**Auth flow:**
1. Client authenticates via Auth0 Universal Login (supports email/password, Google SSO, enterprise SAML/OIDC for trust companies).
2. Auth0 issues a JWT access token containing `sub` (Auth0 user ID) and custom claims (`firm_ids`, `roles`).
3. API validates the JWT on every request, extracts user context, and resolves the internal `user_id` and `firm_membership`.

**Stakeholder access (non-firm users — executors, beneficiaries):**
Stakeholders who are not firm members receive a magic-link email. Clicking it authenticates them via Auth0 passwordless flow and grants scoped access to their specific matter(s) based on the `stakeholders` table.

### 7.2 Authorization Model

Authorization is a two-layer system:

**Layer 1 — Firm Membership:** A user must be a member of the firm that owns the matter, OR be a stakeholder on that specific matter.

**Layer 2 — Stakeholder Role (per-matter):** Permissions are resolved from the `stakeholders.role` column.

```typescript
const ROLE_PERMISSIONS: Record<StakeholderRole, Permission[]> = {
  matter_admin: [
    'matter:read', 'matter:write', 'matter:close',
    'task:read', 'task:write', 'task:assign', 'task:complete',
    'asset:read', 'asset:write',
    'entity:read', 'entity:write',
    'document:read', 'document:upload', 'document:download',
    'stakeholder:invite', 'stakeholder:manage',
    'communication:read', 'communication:write',
    'event:read',
    'ai:trigger',
    'report:generate',
  ],
  professional: [
    'matter:read',
    'task:read', 'task:write', 'task:assign', 'task:complete',
    'asset:read', 'asset:write',
    'entity:read', 'entity:write',
    'document:read', 'document:upload', 'document:download',
    'communication:read', 'communication:write',
    'event:read',
    'ai:trigger',
    'report:generate',
  ],
  executor_trustee: [
    'matter:read',
    'task:read:assigned', 'task:complete:assigned',
    'asset:read',
    'document:read:linked', 'document:upload',
    'communication:read', 'communication:write',
  ],
  beneficiary: [
    'matter:read:summary',
    'task:read:milestones',
    'document:read:shared',
    'communication:read:visible',
  ],
  read_only: [
    'matter:read:summary',
    'task:read:milestones',
  ],
};
```

Authorization is enforced at the API middleware layer. Every route handler declares its required permission, and middleware resolves the authenticated user's stakeholder role on the target matter before proceeding.

### 7.3 Multi-Tenancy Enforcement

See Section 3.3. The combination of application-level firm_id scoping and PostgreSQL RLS ensures complete tenant isolation. Cross-tenant API requests return 404 (not 403) to avoid confirming resource existence.

---

## 8. Real-Time & Notification System

### 8.1 In-App Real-Time Updates

The web and mobile clients maintain a WebSocket connection (via Socket.IO) to receive real-time updates when other users modify the same matter. Events pushed include:

- Task status changes
- New comments
- Document uploads
- Stakeholder activity
- Deadline status changes

The server publishes events to Redis Pub/Sub keyed by `matter:{matterId}`. Connected clients subscribe to their active matter channel.

### 8.2 Email Notifications

The notification worker processes a BullMQ queue and dispatches emails via Resend (or Postmark) for:

| Trigger | Recipient | Template |
|---|---|---|
| Stakeholder invited | Invitee | Invitation with magic link |
| Task assigned | Assignee | Task details with action link |
| Task overdue | Assignee + matter admin | Overdue alert |
| Deadline approaching (30d, 7d, 1d) | Assigned stakeholder + matter admin | Deadline reminder |
| Deadline missed | Matter admin | Urgent missed deadline alert |
| Document requested | Target stakeholder | Request with upload link |
| Milestone reached | Beneficiaries | Progress update |
| Distribution recorded | Beneficiary | Distribution notice with acknowledgment link |
| Comment/message posted | Relevant stakeholders | Message notification |

### 8.3 Notification Preferences

Each stakeholder has configurable notification preferences stored in `stakeholders.settings`:

```typescript
interface NotificationPreferences {
  email_enabled: boolean;
  digest_mode: 'immediate' | 'daily' | 'weekly';
  notify_on: {
    task_assigned: boolean;
    task_overdue: boolean;
    deadline_approaching: boolean;
    document_uploaded: boolean;
    comment_posted: boolean;
    milestone_reached: boolean;
  };
}
```

---

## 9. Document Management

### 9.1 Upload Flow

```
Client                    API                     S3/GCS              AI Worker
  │                        │                        │                    │
  │  POST /upload-url      │                        │                    │
  │ ─────────────────────► │                        │                    │
  │                        │  Generate presigned    │                    │
  │                        │  PUT URL               │                    │
  │  ◄───────────────────  │                        │                    │
  │                        │                        │                    │
  │  PUT (binary upload)   │                        │                    │
  │ ──────────────────────────────────────────────► │                    │
  │                        │                        │                    │
  │  POST /documents       │                        │                    │
  │  (register metadata)   │                        │                    │
  │ ─────────────────────► │                        │                    │
  │                        │  Insert document row   │                    │
  │                        │  Enqueue AI job ──────────────────────────► │
  │                        │  Emit event            │                    │
  │  ◄───────────────────  │                        │                    │
  │  { document, event }   │                        │                    │
```

Documents are uploaded directly to object storage via pre-signed URLs to avoid routing large binaries through the API server. The API server only handles metadata registration and triggers the AI pipeline.

### 9.2 Document Request Workflow

A professional can request a document from any stakeholder:

1. Professional creates a document request (POST `/documents/request`) specifying the target stakeholder, document type needed, and related task.
2. System sends the target stakeholder an email with a unique upload link.
3. Stakeholder clicks the link, authenticates (magic link), and uploads the document.
4. Document is registered, linked to the requesting task, and the requesting professional is notified.

### 9.3 Bulk Export

The `POST /documents/bulk-download` endpoint generates a ZIP archive containing all documents for a matter (or a filtered subset), organized into folders by document type. This is an async operation — the API enqueues a ZIP generation job and notifies the requesting user when the download is ready.

---

## 10. Compliance Calendar Engine

### 10.1 Deadline Auto-Population

When a matter is created, the system auto-generates deadlines based on jurisdiction and estate type:

```typescript
const FEDERAL_DEADLINES: DeadlineRule[] = [
  {
    type: 'federal_estate_tax',
    title: 'Federal Estate Tax Return (Form 706) Due',
    base: 'date_of_death',
    offset_months: 9,
    conditions: { estimated_value_above: 12_920_000 },  // 2023 exemption threshold, configurable
  },
  {
    type: 'federal_estate_tax_extension',
    title: 'Form 706 Extension Deadline',
    base: 'date_of_death',
    offset_months: 15,
    conditions: { estimated_value_above: 12_920_000 },
  },
  {
    type: 'final_income_tax',
    title: 'Decedent Final Income Tax Return Due',
    base: 'date_of_death',
    offset_rule: 'next_april_15',
  },
];

// State-specific rules are loaded per jurisdiction
const STATE_DEADLINES: Record<string, DeadlineRule[]> = {
  CA: [
    { type: 'creditor_notice', title: 'Creditor Claim Period Closes', base: 'probate_filed', offset_months: 4 },
    // ...
  ],
  NY: [
    { type: 'creditor_notice', title: 'Creditor Claim Period Closes', base: 'letters_issued', offset_months: 7 },
    // ...
  ],
  // ... additional states
};
```

### 10.2 Deadline Monitoring

The notification worker runs a periodic job (every hour) that queries for upcoming and overdue deadlines:

```sql
-- Deadlines needing reminder
SELECT d.* FROM deadlines d
WHERE d.status = 'upcoming'
  AND d.due_date - CURRENT_DATE <= ANY(
    (d.reminder_config->'days_before')::int[]
  )
  AND (d.last_reminder_sent IS NULL
       OR d.last_reminder_sent < CURRENT_DATE - INTERVAL '1 day');

-- Deadlines that just became overdue
SELECT d.* FROM deadlines d
WHERE d.status = 'upcoming'
  AND d.due_date < CURRENT_DATE;
```

Missed deadlines trigger an immediate email to the matter admin and update the deadline status to `missed`. This is a safety-critical path and is covered by integration tests and monitoring alerts.

---

## 11. Beneficiary Portal & Family Communication

### 11.1 Beneficiary Portal

Beneficiaries see a restricted, read-only view of the matter:

- **Progress summary:** Estate phase, completion percentage, key milestones reached.
- **Shared documents:** Only documents explicitly shared with beneficiaries (e.g., distribution notices, court filings).
- **Timeline:** Milestone events only (no internal task details).
- **Messages:** Communications marked as visible to beneficiaries.

The portal is a separate Next.js route group (`/portal/...`) sharing the same deployment but with a distinct layout and restricted API access enforced by the stakeholder role permission model.

### 11.2 Dispute Flagging

Any stakeholder can flag a disputed item:

1. Stakeholder creates a dispute flag on a task, asset, or distribution.
2. The dispute is logged as a `communication` with `type = 'dispute_flag'`.
3. The matter admin is notified immediately.
4. The disputed item is visually flagged in the UI for all professionals.
5. The dispute does not block workflow unless a professional explicitly sets the related task to `blocked`.

---

## 12. Integrations Architecture

### 12.1 Integration Framework

Integrations are implemented as adapter modules within the core API, each conforming to a common interface:

```typescript
interface IntegrationAdapter {
  id: string;
  name: string;
  configure(credentials: EncryptedCredentials): Promise<void>;
  sync(matterId: string, direction: 'push' | 'pull'): Promise<SyncResult>;
  webhookHandler?(payload: unknown): Promise<void>;
  healthCheck(): Promise<boolean>;
}
```

### 12.2 Phase 2+ Integration Targets

| Integration | Direction | Data Flow |
|---|---|---|
| Clio / PracticePanther | Bidirectional | Matter ↔ Case, time entries, billing |
| QuickBooks / Xero | Push | Estate bank transactions → accounting |
| Estateably | Push | Asset data → fiduciary accounting |
| DocuSign / HelloSign | Bidirectional | Send signature requests, receive signed docs |
| Schwab / Fidelity APIs | Pull | Account balances, statements |
| Stripe | Internal | Subscription billing management |

### 12.3 OAuth Credential Storage

Integration credentials (OAuth tokens, API keys) are encrypted at rest using AES-256 with a per-firm encryption key derived from a master key stored in a cloud KMS (GCP KMS or AWS KMS). Tokens are never logged or exposed in API responses.

---

## 13. Infrastructure & Deployment

### 13.1 Deployment Topology

```
┌─────────────────────────────────────────┐
│              Vercel                       │
│  ┌───────────────────────────────────┐   │
│  │  Next.js Web App                   │   │
│  │  (SSR + client-side)               │   │
│  │  + API Routes (lightweight proxy)  │   │
│  └───────────────────────────────────┘   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         GCP Cloud Run (or Railway)       │
│                                          │
│  ┌──────────────┐  ┌──────────────────┐  │
│  │  Core API    │  │  AI Worker       │  │
│  │  (Node.js)   │  │  (Node.js)       │  │
│  │  Port 8080   │  │  BullMQ consumer │  │
│  └──────────────┘  └──────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │  Notification Worker             │    │
│  │  (Node.js)                       │    │
│  │  BullMQ consumer + cron          │    │
│  └──────────────────────────────────┘    │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           Managed Services               │
│                                          │
│  PostgreSQL  — GCP Cloud SQL / Supabase  │
│  Redis       — GCP Memorystore / Upstash │
│  S3/GCS      — Document storage          │
│  KMS         — Encryption key management │
└─────────────────────────────────────────┘
```

### 13.2 Environment Strategy

| Environment | Purpose | Database | Infra |
|---|---|---|---|
| `local` | Developer machine | Docker Compose (PG + Redis) | Local Node processes |
| `staging` | Pre-production testing | Isolated Cloud SQL instance | Cloud Run (min 0 instances) |
| `production` | Live customer traffic | Cloud SQL HA (regional) | Cloud Run (min 1 instance, autoscale) |

### 13.3 CI/CD

- **Source control:** GitHub monorepo.
- **CI:** GitHub Actions — lint, type-check, unit tests, integration tests (against Docker PG/Redis).
- **CD:** Merge to `main` deploys to staging automatically. Production deploy via manual GitHub Actions trigger after staging validation.
- **Database migrations:** Managed via `node-pg-migrate` or Prisma Migrate, applied as part of the deploy pipeline before the new application version starts receiving traffic.

---

## 14. Security & Compliance

### 14.1 Data Classification

| Classification | Examples | Controls |
|---|---|---|
| **Critical PII** | SSNs, account numbers | AES-256 encryption at field level, never logged, never returned in full via API |
| **Sensitive PII** | Names, addresses, DOB, email | Encrypted at rest (disk-level), TLS in transit, access-logged |
| **Legal Documents** | Wills, trusts, court filings | Encrypted at rest in object storage, signed URLs with 15-min expiry |
| **Financial Data** | Asset values, balances | Encrypted at rest, role-gated access |
| **Operational Data** | Task status, events, communications | Encrypted at rest, audit-logged |

### 14.2 Encryption

- **At rest:** AES-256 via cloud-managed encryption (GCP Cloud SQL default encryption + customer-managed keys for Critical PII fields).
- **In transit:** TLS 1.3 enforced on all endpoints. HSTS headers with `max-age=31536000`.
- **Field-level:** SSNs and account numbers use application-level AES-256-GCM encryption with keys stored in Cloud KMS. Decryption requires an explicit API call that logs the access event.

### 14.3 SOC 2 Type II Readiness

The following controls are designed into the system from Phase 0:

- Immutable, append-only audit log (events table) with no application-level DELETE or UPDATE.
- Role-based access control enforced at API middleware layer with PostgreSQL RLS as defense-in-depth.
- All authentication events logged (login, logout, failed attempts, magic link generation).
- Data retention policies: matters retained for 7 years after closing (configurable per firm); event logs retained indefinitely.
- Quarterly access reviews supported by stakeholder permission reports.
- Penetration testing scheduled before first enterprise customer (target: Month 10).

### 14.4 GDPR / CCPA Compliance

- Data deletion workflow: beneficiary data can be purged on request while preserving matter integrity (anonymization of PII fields, retention of structural data for audit).
- Data export: per-stakeholder data export endpoint for subject access requests.
- Cookie consent and privacy controls managed at the application layer.

---

## 15. Observability & Operations

### 15.1 Logging

- Structured JSON logging via `pino` (Node.js).
- Log levels: `error`, `warn`, `info`, `debug`.
- All logs include: `requestId`, `firmId`, `matterId`, `userId`, `timestamp`.
- Sensitive fields are redacted before logging (SSN, account numbers, auth tokens).
- Shipped to a centralized log platform (GCP Cloud Logging, or Datadog if budget allows).

### 15.2 Metrics

Key application metrics exported via Prometheus-compatible endpoint (or cloud-native equivalent):

- `api_request_duration_seconds` (histogram, by route, method, status code)
- `api_requests_total` (counter, by route, method, status code)
- `active_matters_total` (gauge, by firm)
- `tasks_completed_total` (counter)
- `ai_jobs_duration_seconds` (histogram, by job type)
- `ai_jobs_failed_total` (counter, by job type)
- `notification_delivery_total` (counter, by channel, status)
- `deadline_missed_total` (counter) — **this is an alerting metric**

### 15.3 Alerting

| Alert | Condition | Severity | Response |
|---|---|---|---|
| API error rate spike | 5xx rate > 5% over 5 min | P1 | Page on-call |
| Deadline notification failure | Notification worker queue depth > 100 or consumer stopped | P1 | Page on-call |
| AI worker backlog | AI queue depth > 500 for > 15 min | P2 | Investigate |
| Database connection saturation | Active connections > 80% pool | P2 | Scale or investigate |
| Storage upload failure rate | S3/GCS 5xx > 1% over 10 min | P2 | Investigate |
| Auth provider outage | Auth0 health check failing | P1 | Switch to cached tokens, monitor |

### 15.4 Error Tracking

Application exceptions are captured via Sentry (or equivalent), tagged with `firmId`, `matterId`, and `userId` for rapid triage.

---

## 16. Performance Requirements

| Operation | Target Latency (p95) | Notes |
|---|---|---|
| Matter dashboard load | < 500ms | Aggregation query; consider materialized view if slow |
| Task list (50 tasks) | < 200ms | Indexed query |
| Document upload initiation | < 300ms | Pre-signed URL generation |
| AI classification job | < 30s end-to-end | Async; user sees "Processing…" state |
| AI data extraction job | < 60s end-to-end | Async |
| Search (tasks, assets, docs within matter) | < 300ms | PostgreSQL full-text search or trigram index |
| Event log query (paginated) | < 200ms | Partitioned table, indexed by matter_id + created_at |
| Deadline reminder cron cycle | < 60s for full scan | Indexed query on due_date |

---

## 17. Phased Implementation Plan

### Phase 0 — Foundation (Months 1–2)

**Goal:** Core infrastructure, auth, multi-tenancy, basic matter and task CRUD.

**Deliverables:**
- Repository setup (monorepo: `apps/web`, `apps/api`, `packages/shared`)
- PostgreSQL schema: `firms`, `users`, `firm_memberships`, `matters`, `stakeholders`, `tasks`, `task_dependencies`, `events`
- Auth0 integration: signup, login, JWT validation, magic links
- Multi-tenancy middleware with RLS
- Core API: matter CRUD, task CRUD, stakeholder invite
- Event logging on all mutations
- Basic Next.js web app: login, matter list, matter detail, task list
- CI/CD pipeline (GitHub Actions → Cloud Run)
- Local dev environment (Docker Compose)

**Exit criteria:** A firm admin can create a matter, add tasks manually, invite a stakeholder, and see an activity feed.

### Phase 1 — MVP Workflow (Months 3–4)

**Goal:** Task generation engine, compliance calendar, asset registry, document upload, stakeholder permissions.

**Deliverables:**
- Task template library (initial set: 5 core states — CA, TX, NY, FL, IL)
- Task generation pipeline (from matter creation input)
- Deadline auto-population and monitoring cron
- Asset and entity CRUD with ownership mapping
- Document upload (pre-signed URLs), metadata registration, linking to tasks/assets
- Stakeholder permission enforcement across all endpoints
- Email notifications: invitations, task assignments, deadline reminders
- Web app: matter dashboard with aggregated stats, compliance calendar view, asset registry, document panel

**Exit criteria:** An estate attorney can create a matter, receive auto-generated tasks and deadlines, invite a CPA and executor, upload documents, and track the workflow through to completion.

### Phase 2 — Intelligence (Months 5–6)

**Goal:** AI document pipeline, entity visualization, letter drafting.

**Deliverables:**
- AI worker deployment (BullMQ consumer)
- Document classification pipeline (Claude API)
- Data extraction pipeline for account statements, deeds, insurance policies, trust documents
- Clause extraction for trust documents
- AI-suggested tasks based on asset profile
- Anomaly detection (documents vs. registry)
- Letter drafting (institution notification letters)
- Entity/trust ownership map visualization (web app)
- All AI outputs marked as suggestions with confirm/reject UX

**Exit criteria:** Uploading a trust document automatically classifies it, extracts key provisions, and suggests additional tasks. An attorney can generate notification letters with one click.

### Phase 3 — Distribution & Mobile (Months 7–9)

**Goal:** Beneficiary portal, family communication, distribution ledger, mobile app (executor).

**Deliverables:**
- Beneficiary portal (read-only progress view, shared documents, milestone timeline)
- Communication center (messages, milestone notifications, distribution notices)
- Distribution ledger (recording distributions, receipt acknowledgments)
- Dispute flagging workflow
- React Native mobile app (executor/trustee: view assigned tasks, upload documents, post questions)
- Push notifications (mobile)
- Document request workflow (email → upload link)

**Exit criteria:** A beneficiary can log in, see estate progress, receive distribution notices, and acknowledge receipt. An executor can manage assigned tasks from a phone.

### Phase 4 — Platform & Enterprise (Months 10–12)

**Goal:** Third-party integrations, white-label, SSO, reporting.

**Deliverables:**
- Clio integration (matter sync, time tracking)
- QuickBooks/Xero integration (transaction sync)
- DocuSign integration (signature requests)
- White-label configuration (firm branding, custom domain)
- Enterprise SSO (SAML/OIDC via Auth0)
- Portfolio view for multi-matter firms (all matters, risk flags, staff utilization)
- Reporting engine: matter summary, asset inventory, task audit, distribution ledger, time tracking export
- Bulk document export (ZIP generation)
- Webhook API for outbound events
- SOC 2 Type II audit preparation

**Exit criteria:** A trust company can deploy the platform under their brand, connect to Clio and QuickBooks, manage 50+ matters in a portfolio view, and export compliance reports.

---

## 18. Risk Register & Technical Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| **AI extraction produces incorrect data that a professional acts on** | Medium | High | All AI output staged as "suggested" with mandatory human confirmation. Confidence thresholds with forced manual review. Disclaimers in ToS. No AI output directly mutates primary records. |
| **Missed deadline notification due to worker failure** | Low | Critical | Notification worker runs as a separate process with health monitoring. Dead-letter queue for failed deliveries. Hourly cron with catch-up logic (idempotent). P1 alert on queue depth or consumer failure. |
| **Cross-tenant data leak** | Very Low | Critical | PostgreSQL RLS as defense-in-depth beyond application-level scoping. Integration tests that verify cross-tenant isolation. Penetration test before first enterprise customer. |
| **Auth provider (Auth0) outage** | Low | High | Short-lived JWTs (15 min) + refresh tokens. API validates JWT signature locally (no Auth0 call needed for existing sessions). Cached JWKS with 24h TTL. Monitor Auth0 status. |
| **Claude API outage or rate limiting** | Medium | Medium | AI features are async and non-blocking. Queue retries with exponential backoff. Graceful degradation: manual classification/entry remains fully functional. Consider secondary LLM provider as fallback. |
| **Solo founder availability (bus factor = 1)** | Medium | High | Infrastructure as code (Terraform/Pulumi). Comprehensive documentation. CI/CD automated. Database backups automated with point-in-time recovery. Runbook for common operational tasks. |
| **State-specific legal complexity in task templates** | High | Medium | Launch with 5 states. Templates are data (JSONB), not code — can be updated without deployments. Partner with estate attorneys for template review. Flag state coverage gaps in UI. |
| **Document storage costs at scale** | Low | Low | Lifecycle policies: move documents to infrequent-access storage 1 year after matter closes. Archive to cold storage after 3 years. Compress on upload where possible. |

---

## 19. Open Questions & ADRs

### ADR-001: Modular Monolith vs. Microservices

**Decision:** Modular monolith with separated worker processes.  
**Rationale:** Solo founder velocity, shared types, single deployment. Worker separation for I/O-bound workloads (AI, notifications). Service extraction is straightforward at the module boundary if needed post-seed.  
**Status:** Accepted.

### ADR-002: PostgreSQL as Sole Primary Datastore

**Decision:** PostgreSQL only (no MongoDB, no DynamoDB).  
**Rationale:** The domain is inherently relational. JSONB columns provide schema flexibility where needed (task templates, settings, AI extracted data). RLS provides tenant isolation. Mature tooling. One database to backup, monitor, and scale.  
**Status:** Accepted.

### ADR-003: Event Sourcing vs. Audit Log

**Decision:** Audit log (append-only events table), not full event sourcing.  
**Rationale:** Full event sourcing (rebuilding state from events) adds significant complexity without proportional benefit at this scale. A traditional CRUD model with an append-only event log achieves the audit requirements without the operational overhead of event replay, snapshotting, and eventual consistency.  
**Status:** Accepted.

### ADR-004: Auth0 vs. Clerk vs. Custom Auth

**Decision:** Auth0 (preferred) or Clerk.  
**Rationale:** Enterprise SSO (SAML/OIDC) is a requirement for trust company and large RIA customers. Both Auth0 and Clerk support this. Auth0 has deeper enterprise penetration. Custom auth is ruled out due to the security surface area and solo founder constraints.  
**Status:** Pending final evaluation.

### Open Questions

1. **Task template authoring tool:** Should firms be able to create custom task templates (Phase 2+), or is this admin-only? Custom templates increase product stickiness but add UX complexity.

2. **Offline mobile access:** Do executors need offline task/document access on mobile? This significantly increases mobile app complexity (local DB sync).

3. **Multi-jurisdiction matters:** For estates with assets in multiple states, should the system generate jurisdiction-specific task subsets per state, or a unified task list? This affects the template resolver design.

4. **Billing model for AI features:** Are AI extraction calls included in the subscription tier, or metered separately? This affects the rate limiting design and cost forecasting.

5. **Data residency:** Will enterprise customers require data residency guarantees (e.g., US-only storage)? If yes, this constrains infrastructure provider selection.

---

## 20. Appendix

### 20.1 Technology Stack Summary

| Layer | Technology | Rationale |
|---|---|---|
| Web frontend | Next.js 14+ (App Router) | SSR, RSC, file-based routing, Vercel-native |
| UI components | Tailwind CSS + shadcn/ui | Rapid, consistent UI development |
| Mobile | React Native (Expo) | Cross-platform, shared JS/TS types with web/API |
| API server | Node.js + Express | Team familiarity, async I/O, large ecosystem |
| Language | TypeScript (end-to-end) | Type safety across frontend, API, and shared packages |
| Database | PostgreSQL 15+ | Relational model, RLS, JSONB, mature ecosystem |
| ORM / Query | Prisma or Drizzle ORM | Type-safe queries, migration management |
| Cache / Pub-Sub | Redis 7+ | Session cache, BullMQ backing, real-time pub/sub |
| Job queue | BullMQ | Reliable, Redis-backed, dead-letter support, dashboard UI |
| Object storage | GCP Cloud Storage (or S3) | Document storage with signed URLs |
| AI/ML | Anthropic Claude API (Sonnet) | Document classification, extraction, drafting |
| Auth | Auth0 (or Clerk) | SSO, SAML, magic links, RBAC |
| Email | Resend (or Postmark) | Transactional email, deliverability |
| Payments | Stripe | Subscription billing |
| Infra | GCP Cloud Run + Cloud SQL | Managed, autoscaling, minimal ops |
| Web hosting | Vercel | Next.js native, edge functions, preview deploys |
| CI/CD | GitHub Actions | Monorepo-aware, free tier sufficient |
| Monitoring | GCP Cloud Monitoring + Sentry | Metrics, alerts, error tracking |
| IaC | Terraform (or Pulumi) | Reproducible infrastructure |

### 20.2 Monorepo Structure

```
estate-executor-os/
├── apps/
│   ├── web/                    # Next.js web application
│   │   ├── app/                # App Router pages and layouts
│   │   ├── components/         # UI components
│   │   └── lib/                # Client-side utilities
│   ├── api/                    # Node.js API server
│   │   ├── src/
│   │   │   ├── modules/        # Feature modules
│   │   │   │   ├── matters/
│   │   │   │   ├── tasks/
│   │   │   │   ├── assets/
│   │   │   │   ├── entities/
│   │   │   │   ├── documents/
│   │   │   │   ├── stakeholders/
│   │   │   │   ├── deadlines/
│   │   │   │   ├── communications/
│   │   │   │   ├── events/
│   │   │   │   ├── ai/
│   │   │   │   ├── notifications/
│   │   │   │   └── integrations/
│   │   │   ├── middleware/      # Auth, tenancy, permissions, logging
│   │   │   ├── workers/        # AI worker, notification worker entry points
│   │   │   └── server.ts
│   │   └── prisma/             # Schema, migrations, seed
│   └── mobile/                 # React Native (Expo) app
├── packages/
│   ├── shared/                 # Shared TypeScript types, constants, validation
│   ├── task-templates/         # Task template definitions (JSON/TS)
│   └── deadline-rules/         # Jurisdiction-specific deadline rules
├── infrastructure/             # Terraform / Pulumi IaC
├── docs/                       # Architecture docs, ADRs, runbooks
├── .github/
│   └── workflows/              # CI/CD pipelines
├── docker-compose.yml          # Local dev (PG, Redis)
├── turbo.json                  # Turborepo config
└── package.json
```

### 20.3 Glossary

| Term | Definition |
|---|---|
| Matter | A single estate administration case within the platform |
| Stakeholder | Any person participating in a matter (attorney, CPA, executor, beneficiary) |
| Task Template | A reusable task definition that is instantiated per matter during generation |
| Deadline Rule | A configuration defining how a compliance deadline is calculated from a reference date |
| Entity | A legal structure (trust, LLC, FLP) that owns assets within an estate |
| Event | An immutable log entry recording a state change (audit trail) |
| Firm | The top-level tenant account (law firm, RIA, trust company) |

---

*End of document.*
