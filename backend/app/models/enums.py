import enum


class FirmType(enum.StrEnum):
    law_firm = "law_firm"
    ria = "ria"
    trust_company = "trust_company"
    family_office = "family_office"
    other = "other"


class SubscriptionTier(enum.StrEnum):
    starter = "starter"
    professional = "professional"
    growth = "growth"
    enterprise = "enterprise"


class FirmRole(enum.StrEnum):
    owner = "owner"
    admin = "admin"
    member = "member"


class MatterStatus(enum.StrEnum):
    active = "active"
    on_hold = "on_hold"
    closed = "closed"
    archived = "archived"


class EstateType(enum.StrEnum):
    testate_probate = "testate_probate"
    intestate_probate = "intestate_probate"
    trust_administration = "trust_administration"
    conservatorship = "conservatorship"
    mixed_probate_trust = "mixed_probate_trust"
    other = "other"


class MatterPhase(enum.StrEnum):
    immediate = "immediate"
    administration = "administration"
    distribution = "distribution"
    closing = "closing"


class StakeholderRole(enum.StrEnum):
    matter_admin = "matter_admin"
    professional = "professional"
    executor_trustee = "executor_trustee"
    beneficiary = "beneficiary"
    read_only = "read_only"


class InviteStatus(enum.StrEnum):
    pending = "pending"
    accepted = "accepted"
    revoked = "revoked"


class TaskPhase(enum.StrEnum):
    immediate = "immediate"
    asset_inventory = "asset_inventory"
    notification = "notification"
    probate_filing = "probate_filing"
    tax = "tax"
    transfer_distribution = "transfer_distribution"
    family_communication = "family_communication"
    closing = "closing"
    custom = "custom"


class TaskStatus(enum.StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    blocked = "blocked"
    complete = "complete"
    waived = "waived"
    cancelled = "cancelled"


class TaskPriority(enum.StrEnum):
    critical = "critical"
    normal = "normal"
    informational = "informational"


class AssetType(enum.StrEnum):
    real_estate = "real_estate"
    bank_account = "bank_account"
    brokerage_account = "brokerage_account"
    retirement_account = "retirement_account"
    life_insurance = "life_insurance"
    business_interest = "business_interest"
    vehicle = "vehicle"
    digital_asset = "digital_asset"
    personal_property = "personal_property"
    receivable = "receivable"
    other = "other"


class OwnershipType(enum.StrEnum):
    in_trust = "in_trust"
    joint_tenancy = "joint_tenancy"
    community_property = "community_property"
    pod_tod = "pod_tod"
    individual = "individual"
    business_owned = "business_owned"
    other = "other"


class TransferMechanism(enum.StrEnum):
    probate = "probate"
    trust_administration = "trust_administration"
    beneficiary_designation = "beneficiary_designation"
    joint_survivorship = "joint_survivorship"
    other = "other"


class AssetStatus(enum.StrEnum):
    discovered = "discovered"
    valued = "valued"
    transferred = "transferred"
    distributed = "distributed"


class EntityType(enum.StrEnum):
    revocable_trust = "revocable_trust"
    irrevocable_trust = "irrevocable_trust"
    llc = "llc"
    flp = "flp"
    corporation = "corporation"
    foundation = "foundation"
    other = "other"


class FundingStatus(enum.StrEnum):
    unknown = "unknown"
    fully_funded = "fully_funded"
    partially_funded = "partially_funded"
    unfunded = "unfunded"


class DeadlineSource(enum.StrEnum):
    auto = "auto"
    manual = "manual"


class DeadlineStatus(enum.StrEnum):
    upcoming = "upcoming"
    completed = "completed"
    extended = "extended"
    missed = "missed"


class CommunicationType(enum.StrEnum):
    message = "message"
    milestone_notification = "milestone_notification"
    distribution_notice = "distribution_notice"
    document_request = "document_request"
    dispute_flag = "dispute_flag"


class CommunicationVisibility(enum.StrEnum):
    all_stakeholders = "all_stakeholders"
    professionals_only = "professionals_only"
    specific = "specific"


class DistributionType(enum.StrEnum):
    cash = "cash"
    asset_transfer = "asset_transfer"
    in_kind = "in_kind"


class DisputeStatus(enum.StrEnum):
    open = "open"
    under_review = "under_review"
    resolved = "resolved"


class DocumentRequestStatus(enum.StrEnum):
    pending = "pending"
    uploaded = "uploaded"
    expired = "expired"


class ActorType(enum.StrEnum):
    user = "user"
    system = "system"
    ai = "ai"


class SubscriptionStatus(enum.StrEnum):
    trialing = "trialing"
    active = "active"
    past_due = "past_due"
    canceled = "canceled"
    unpaid = "unpaid"
    incomplete = "incomplete"
    paused = "paused"


class BillingInterval(enum.StrEnum):
    month = "month"
    year = "year"


class IntegrationProvider(enum.StrEnum):
    clio = "clio"
    quickbooks = "quickbooks"
    xero = "xero"
    docusign = "docusign"


class IntegrationStatus(enum.StrEnum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"
    pending = "pending"


class SyncDirection(enum.StrEnum):
    push = "push"
    pull = "pull"
    bidirectional = "bidirectional"


class SyncStatus(enum.StrEnum):
    idle = "idle"
    syncing = "syncing"
    success = "success"
    failed = "failed"
