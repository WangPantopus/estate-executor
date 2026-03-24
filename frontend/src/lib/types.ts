/**
 * Estate Executor OS — TypeScript Type System
 *
 * Mirrors all backend Pydantic schemas and enums.
 * Keep in sync with backend/app/schemas/ and backend/app/models/enums.py.
 */

// ─── Enums ───────────────────────────────────────────────────────────────────

export type FirmType = 'law_firm' | 'ria' | 'trust_company' | 'family_office' | 'other';
export type SubscriptionTier = 'starter' | 'professional' | 'growth' | 'enterprise';
export type FirmRole = 'owner' | 'admin' | 'member';

export type MatterStatus = 'active' | 'on_hold' | 'closed' | 'archived';
export type EstateType =
  | 'testate_probate'
  | 'intestate_probate'
  | 'trust_administration'
  | 'conservatorship'
  | 'mixed_probate_trust'
  | 'other';
export type MatterPhase = 'immediate' | 'administration' | 'distribution' | 'closing';

export type StakeholderRole = 'matter_admin' | 'professional' | 'executor_trustee' | 'beneficiary' | 'read_only';
export type InviteStatus = 'pending' | 'accepted' | 'revoked';

export type TaskPhase =
  | 'immediate'
  | 'asset_inventory'
  | 'notification'
  | 'probate_filing'
  | 'tax'
  | 'transfer_distribution'
  | 'family_communication'
  | 'closing'
  | 'custom';
export type TaskStatus = 'not_started' | 'in_progress' | 'blocked' | 'complete' | 'waived' | 'cancelled';
export type TaskPriority = 'critical' | 'normal' | 'informational';

export type AssetType =
  | 'real_estate'
  | 'bank_account'
  | 'brokerage_account'
  | 'retirement_account'
  | 'life_insurance'
  | 'business_interest'
  | 'vehicle'
  | 'digital_asset'
  | 'personal_property'
  | 'receivable'
  | 'other';
export type OwnershipType =
  | 'in_trust'
  | 'joint_tenancy'
  | 'community_property'
  | 'pod_tod'
  | 'individual'
  | 'business_owned'
  | 'other';
export type TransferMechanism =
  | 'probate'
  | 'trust_administration'
  | 'beneficiary_designation'
  | 'joint_survivorship'
  | 'other';
export type AssetStatus = 'discovered' | 'valued' | 'transferred' | 'distributed';

export type DistributionType = 'cash' | 'asset_transfer' | 'in_kind';

export type EntityType =
  | 'revocable_trust'
  | 'irrevocable_trust'
  | 'llc'
  | 'flp'
  | 'corporation'
  | 'foundation'
  | 'other';
export type FundingStatus = 'unknown' | 'fully_funded' | 'partially_funded' | 'unfunded';

export type DeadlineSource = 'auto' | 'manual';
export type DeadlineStatus = 'upcoming' | 'completed' | 'extended' | 'missed';

export type CommunicationType =
  | 'message'
  | 'milestone_notification'
  | 'distribution_notice'
  | 'document_request'
  | 'dispute_flag';
export type CommunicationVisibility = 'all_stakeholders' | 'professionals_only' | 'specific';
export type ActorType = 'user' | 'system' | 'ai';

// ─── Common ──────────────────────────────────────────────────────────────────

export interface PaginationMeta {
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

export interface CursorMeta {
  has_more: boolean;
  next_cursor: string | null;
  per_page: number;
}

export interface CursorPaginatedResponse<T> {
  data: T[];
  meta: CursorMeta;
}

export interface ErrorDetail {
  code: string;
  message: string;
  field?: string;
}

export interface APIErrorResponse {
  data: null;
  meta: null;
  errors: ErrorDetail[];
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface FirmMembershipBrief {
  firm_id: string;
  firm_role: FirmRole;
}

export interface FirmMembershipDetail {
  firm_id: string;
  firm_name: string;
  firm_slug: string;
  firm_role: string;
}

export interface CurrentUser {
  user_id: string;
  email: string;
  firm_memberships: FirmMembershipBrief[];
}

export interface UserProfile {
  user_id: string;
  email: string;
  full_name: string;
  firm_memberships: FirmMembershipDetail[];
}

export interface AcceptInviteResponse {
  stakeholder_id: string;
  matter_id: string;
  matter_title: string;
  role: string;
}

// ─── Firms ───────────────────────────────────────────────────────────────────

export interface FirmCreate {
  name: string;
  type: FirmType;
}

export interface FirmUpdate {
  name?: string;
  type?: FirmType;
  settings?: Record<string, unknown>;
}

export interface Firm {
  id: string;
  name: string;
  slug: string;
  type: FirmType;
  subscription_tier: SubscriptionTier;
  settings: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface FirmMember {
  id: string;
  firm_id: string;
  user_id: string;
  email: string;
  full_name: string;
  firm_role: string;
}

export interface InviteMemberRequest {
  email: string;
  full_name: string;
  firm_role: FirmRole;
}

export interface UpdateMemberRoleRequest {
  firm_role: FirmRole;
}

// ─── Matters ─────────────────────────────────────────────────────────────────

export interface MatterCreate {
  title: string;
  estate_type: EstateType;
  jurisdiction_state: string;
  decedent_name: string;
  date_of_death?: string | null;
  date_of_incapacity?: string | null;
  estimated_value?: number | null;
  asset_types_present?: AssetType[];
  flags?: string[];
}

export interface MatterUpdate {
  title?: string;
  status?: MatterStatus;
  phase?: MatterPhase;
  jurisdiction_state?: string;
  estimated_value?: number | null;
  settings?: Record<string, unknown>;
}

export interface Matter {
  id: string;
  firm_id: string;
  title: string;
  status: MatterStatus;
  estate_type: EstateType;
  jurisdiction_state: string;
  date_of_death: string | null;
  decedent_name: string;
  estimated_value: number | null;
  phase: MatterPhase;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
}

export interface TaskSummary {
  total: number;
  not_started: number;
  in_progress: number;
  blocked: number;
  complete: number;
  waived: number;
  overdue: number;
  completion_percentage: number;
}

export interface AssetSummary {
  total_count: number;
  total_estimated_value: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
}

export interface MatterDashboard {
  matter: Matter;
  task_summary: TaskSummary;
  asset_summary: AssetSummary;
  stakeholder_count: number;
  upcoming_deadlines: DeadlineResponse[];
  recent_events: EventResponse[];
}

// ─── Tasks ───────────────────────────────────────────────────────────────────

export interface DocumentBrief {
  id: string;
  filename: string;
  doc_type: string | null;
  created_at: string;
}

export interface CommentBrief {
  id: string;
  author_id: string;
  body: string;
  created_at: string;
}

export interface TaskCreate {
  title: string;
  description?: string;
  instructions?: string;
  phase?: TaskPhase;
  priority?: TaskPriority;
  assigned_to?: string | null;
  due_date?: string | null;
  requires_document?: boolean;
  parent_task_id?: string | null;
  dependency_ids?: string[];
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  instructions?: string;
  phase?: TaskPhase;
  priority?: TaskPriority;
  assigned_to?: string | null;
  due_date?: string | null;
  status?: TaskStatus;
  sort_order?: number;
}

export interface TaskComplete {
  notes?: string;
}

export interface TaskWaive {
  reason: string;
}

export interface TaskAssign {
  stakeholder_id: string;
}

export interface TaskLinkDocument {
  document_id: string;
}

export interface TaskGenerateRequest {
  regenerate?: boolean;
}

export interface Task {
  id: string;
  matter_id: string;
  parent_task_id: string | null;
  template_key: string | null;
  title: string;
  description: string | null;
  instructions: string | null;
  phase: TaskPhase;
  status: TaskStatus;
  priority: TaskPriority;
  assigned_to: string | null;
  due_date: string | null;
  requires_document: boolean;
  completed_at: string | null;
  completed_by: string | null;
  sort_order: number;
  metadata: Record<string, unknown>;
  documents: DocumentBrief[];
  dependencies: string[];
  created_at: string;
  updated_at: string;
}

export interface TaskListItem extends Task {
  document_count: number;
  dependency_ids: string[];
}

export interface TaskDetail extends Task {
  dependents: string[];
  comments: CommentBrief[];
}

// ─── Assets ──────────────────────────────────────────────────────────────────

export interface EntityBrief {
  id: string;
  name: string;
  entity_type: EntityType;
}

export interface AssetCreate {
  asset_type: AssetType;
  title: string;
  description?: string;
  institution?: string;
  account_number?: string;
  ownership_type?: OwnershipType;
  transfer_mechanism?: TransferMechanism;
  date_of_death_value?: number | null;
  current_estimated_value?: number | null;
  metadata?: Record<string, unknown>;
}

export interface AssetUpdate {
  asset_type?: AssetType;
  title?: string;
  description?: string;
  institution?: string;
  account_number?: string;
  ownership_type?: OwnershipType;
  transfer_mechanism?: TransferMechanism;
  status?: AssetStatus;
  date_of_death_value?: number | null;
  current_estimated_value?: number | null;
  metadata?: Record<string, unknown>;
}

export interface AssetLinkDocument {
  document_id: string;
}

export interface AssetValuation {
  type: string;
  value: number;
  notes?: string;
}

export interface ValuationEntry {
  type: string;
  value: number;
  notes: string | null;
  recorded_at: string;
  recorded_by: string | null;
}

export interface AssetListItem {
  id: string;
  matter_id: string;
  asset_type: AssetType;
  title: string;
  description: string | null;
  institution: string | null;
  account_number_masked: string | null;
  ownership_type: OwnershipType | null;
  transfer_mechanism: TransferMechanism | null;
  status: AssetStatus;
  date_of_death_value: number | null;
  current_estimated_value: number | null;
  final_appraised_value: number | null;
  metadata: Record<string, unknown>;
  document_count: number;
  entities: EntityBrief[];
  created_at: string;
  updated_at: string;
}

export interface AssetDetail extends AssetListItem {
  documents: DocumentBrief[];
  valuations: ValuationEntry[];
}

// ─── Entities ────────────────────────────────────────────────────────────────

export interface AssetBrief {
  id: string;
  title: string;
  asset_type: AssetType;
  current_estimated_value: number | null;
}

export interface EntityCreate {
  entity_type: EntityType;
  name: string;
  trustee?: string;
  successor_trustee?: string;
  trigger_conditions?: Record<string, unknown>;
  funding_status?: FundingStatus;
  distribution_rules?: Record<string, unknown>;
  asset_ids?: string[];
}

export interface EntityUpdate {
  entity_type?: EntityType;
  name?: string;
  trustee?: string;
  successor_trustee?: string;
  trigger_conditions?: Record<string, unknown>;
  funding_status?: FundingStatus;
  distribution_rules?: Record<string, unknown>;
  asset_ids?: string[];
}

export interface Entity {
  id: string;
  matter_id: string;
  entity_type: EntityType;
  name: string;
  trustee: string | null;
  successor_trustee: string | null;
  trigger_conditions: Record<string, unknown> | null;
  funding_status: FundingStatus;
  distribution_rules: Record<string, unknown> | null;
  metadata: Record<string, unknown>;
  assets: AssetBrief[];
  created_at: string;
  updated_at: string;
}

export interface FundingDetail {
  entity_id: string;
  entity_name: string;
  funding_status: FundingStatus;
  funded_count: number;
  total_value: number | null;
}

export interface EntityMapResponse {
  entities: Entity[];
  unassigned_assets: AssetBrief[];
  pour_over_candidates: AssetBrief[];
  funding_summary: FundingDetail[];
}

// ─── Documents ───────────────────────────────────────────────────────────────

export interface DocumentUploadRequest {
  filename: string;
  mime_type: string;
}

export interface DocumentRegister {
  filename: string;
  storage_key: string;
  mime_type: string;
  size_bytes: number;
  task_id?: string | null;
  asset_id?: string | null;
}

export interface DocumentUploadURL {
  upload_url: string;
  storage_key: string;
  expires_in: number;
}

export interface DocumentResponse {
  id: string;
  matter_id: string;
  uploaded_by: string;
  filename: string;
  storage_key: string;
  mime_type: string;
  size_bytes: number;
  doc_type: string | null;
  doc_type_confidence: number | null;
  doc_type_confirmed: boolean;
  ai_extracted_data: Record<string, unknown> | null;
  current_version: number;
  created_at: string;
}

export interface DocumentVersionResponse {
  id: string;
  document_id: string;
  version_number: number;
  storage_key: string;
  size_bytes: number;
  uploaded_by: string;
  created_at: string;
}

export interface TaskBriefDoc {
  id: string;
  title: string;
}

export interface AssetBriefDoc {
  id: string;
  title: string;
}

export interface DocumentDetail extends DocumentResponse {
  versions: DocumentVersionResponse[];
  linked_tasks: TaskBriefDoc[];
  linked_assets: AssetBriefDoc[];
}

export interface DownloadURLResponse {
  download_url: string;
  expires_in: number;
}

export interface DocumentConfirmType {
  doc_type: string;
}

export interface DocumentRequestCreate {
  target_stakeholder_id: string;
  doc_type_needed: string;
  task_id?: string | null;
  message?: string;
}

export interface RegisterVersionRequest {
  storage_key: string;
  size_bytes: number;
}

export interface BulkDownloadRequest {
  document_ids: string[];
}

export interface BulkDownloadStatusResponse {
  job_id: string;
  status: string;
  download_url: string | null;
}

// ─── Stakeholders ────────────────────────────────────────────────────────────

export interface StakeholderInvite {
  email: string;
  full_name: string;
  role: StakeholderRole;
  relationship?: string;
}

export interface StakeholderUpdate {
  role?: StakeholderRole;
  relationship?: string;
  notification_preferences?: Record<string, unknown>;
}

export interface Stakeholder {
  id: string;
  matter_id: string;
  user_id: string | null;
  email: string;
  full_name: string;
  role: StakeholderRole;
  relationship: string | null;
  invite_status: InviteStatus;
  created_at: string;
}

// ─── Deadlines ───────────────────────────────────────────────────────────────

export interface TaskBrief {
  id: string;
  title: string;
  status: TaskStatus;
}

export interface DeadlineCreate {
  title: string;
  description?: string;
  due_date: string;
  task_id?: string | null;
  assigned_to?: string | null;
  reminder_config?: Record<string, unknown>;
}

export interface DeadlineUpdate {
  title?: string;
  description?: string;
  due_date?: string;
  status?: DeadlineStatus;
  assigned_to?: string | null;
  reminder_config?: Record<string, unknown>;
}

export interface DeadlineResponse {
  id: string;
  matter_id: string;
  task_id: string | null;
  title: string;
  description: string | null;
  due_date: string;
  source: DeadlineSource;
  rule: Record<string, unknown> | null;
  status: DeadlineStatus;
  assigned_to: string | null;
  assignee_name: string | null;
  task: TaskBrief | null;
  reminder_config: Record<string, unknown> | null;
  last_reminder_sent: string | null;
  created_at: string;
  updated_at: string;
}

export interface CalendarDeadline {
  id: string;
  title: string;
  description: string | null;
  due_date: string;
  status: DeadlineStatus;
  source: DeadlineSource;
  task_id: string | null;
  task_title: string | null;
  assigned_to: string | null;
  assignee_name: string | null;
}

export interface CalendarMonth {
  month: string;
  deadlines: CalendarDeadline[];
}

export interface CalendarResponse {
  data: CalendarMonth[];
}

// ─── Communications ─────────────────────────────────────────────────────────

export interface CommunicationCreate {
  type: CommunicationType;
  subject?: string;
  body: string;
  visibility?: CommunicationVisibility;
  visible_to?: string[];
}

export type DisputeStatus = 'open' | 'under_review' | 'resolved';

export interface CommunicationResponse {
  id: string;
  matter_id: string;
  sender_id: string;
  sender_name: string;
  type: CommunicationType;
  subject: string;
  body: string;
  visibility: CommunicationVisibility;
  acknowledged_by: string[];
  created_at: string;
  // Dispute-specific fields
  disputed_entity_type?: string | null;
  disputed_entity_id?: string | null;
  dispute_status?: DisputeStatus | null;
  dispute_resolution_note?: string | null;
  dispute_resolved_at?: string | null;
  dispute_resolved_by?: string | null;
}

export interface DisputeFlagCreate {
  entity_type: string;
  entity_id: string;
  reason: string;
}

export interface DisputeStatusUpdate {
  status: 'under_review' | 'resolved';
  resolution_note: string;
}

export interface ActiveDisputes {
  disputes: Record<string, Array<{ entity_id: string; dispute_status: DisputeStatus }>>;
}

// ─── Milestones ──────────────────────────────────────────────────────────────

export interface MilestoneStatus {
  key: string;
  title: string;
  description: string;
  phase: string;
  total_tasks: number;
  completed_tasks: number;
  is_complete: boolean;
  achieved_at: string | null;
  auto_notify: boolean;
}

export interface MilestoneStatusResponse {
  milestones: MilestoneStatus[];
}

export interface MilestoneSettingUpdate {
  milestone_key: string;
  enabled: boolean;
}

// ─── Time Tracking ───────────────────────────────────────────────────────────

export interface TimeEntry {
  id: string;
  matter_id: string;
  task_id: string | null;
  task_title: string | null;
  stakeholder_id: string;
  stakeholder_name: string;
  hours: number;
  minutes: number;
  description: string;
  entry_date: string;
  billable: boolean;
  created_at: string;
}

export interface TimeEntryCreate {
  task_id?: string | null;
  hours: number;
  minutes: number;
  description: string;
  entry_date: string;
  billable?: boolean;
}

export interface TimeEntryUpdate {
  task_id?: string | null;
  hours?: number;
  minutes?: number;
  description?: string;
  entry_date?: string;
  billable?: boolean;
}

export interface TimeEntryListResponse {
  data: TimeEntry[];
  meta: PaginationMeta;
}

export interface TimeTrackingSummary {
  total_hours: number;
  total_minutes: number;
  total_decimal_hours: number;
  billable_hours: number;
  non_billable_hours: number;
  by_stakeholder: Array<{ stakeholder_id: string; name: string; total_minutes: number; decimal_hours: number }>;
  by_task: Array<{ task_id: string; title: string; total_minutes: number; decimal_hours: number }>;
}

// ─── Events ──────────────────────────────────────────────────────────────────

export interface EventResponse {
  id: string;
  matter_id: string;
  actor_id: string | null;
  actor_type: ActorType;
  actor_name: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  changes: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

// ─── AI ──────────────────────────────────────────────────────────────────────

export interface AIClassifyResponse {
  doc_type: string;
  confidence: number;
  reasoning: string;
}

export interface AIExtractResponse {
  extracted_fields: Record<string, unknown>;
  confidence: number;
}

export interface AILetterDraftRequest {
  asset_id: string;
  letter_type: string;
}

export interface AILetterDraftResponse {
  subject: string;
  body: string;
  recipient_institution: string;
}

export interface TaskSuggestion {
  title: string;
  description: string;
  phase: string;
  reasoning: string;
}

export interface AISuggestTasksResponse {
  suggestions: TaskSuggestion[];
}

export interface Anomaly {
  type: string;
  description: string;
  document_id: string | null;
  asset_id: string | null;
  severity: string;
}

export interface AIAnomalyResponse {
  anomalies: Anomaly[];
}

export interface AIUsageByOperation {
  operation: string;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface AIUsageByMatter {
  matter_id: string;
  matter_title: string;
  calls: number;
  cost_usd: number;
}

export interface AIUsageStats {
  period_start: string;
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  by_operation: AIUsageByOperation[];
  by_matter: AIUsageByMatter[];
  rate_limits: {
    firm_limit_per_hour: number;
    matter_limit_per_hour: number;
    firm_calls_this_hour: number;
  };
}

// ─── Distributions ──────────────────────────────────────────────────────────

export interface DistributionCreate {
  asset_id?: string | null;
  beneficiary_stakeholder_id: string;
  amount?: number | null;
  description: string;
  distribution_type: DistributionType;
  distribution_date: string;
  notes?: string | null;
}

export interface DistributionResponse {
  id: string;
  matter_id: string;
  asset_id: string | null;
  asset_title: string | null;
  beneficiary_stakeholder_id: string;
  beneficiary_name: string;
  amount: number | null;
  description: string;
  distribution_type: DistributionType;
  distribution_date: string;
  receipt_acknowledged: boolean;
  receipt_acknowledged_at: string | null;
  notes: string | null;
  created_at: string;
}

export interface BeneficiarySummaryItem {
  stakeholder_id: string;
  beneficiary_name: string;
  total_distributed: number;
  distribution_count: number;
  acknowledged_count: number;
  pending_count: number;
}

export interface DistributionSummaryResponse {
  total_distributed: number;
  total_distributions: number;
  total_acknowledged: number;
  total_pending: number;
  by_beneficiary: BeneficiarySummaryItem[];
  by_type: Record<string, number>;
}

// ─── Portal (Beneficiary) ───────────────────────────────────────────────────

export interface PortalMatterBrief {
  matter_id: string;
  firm_id: string;
  decedent_name: string;
  phase: MatterPhase;
  firm_name: string;
}

export interface PortalBeneficiaryMattersResponse {
  matters: PortalMatterBrief[];
}

export interface PortalContactInfo {
  name: string;
  email: string;
  role: string;
}

export interface PortalMilestone {
  title: string;
  date: string;
  completed: boolean;
  is_next: boolean;
}

export interface PortalDistributionSummary {
  total_estate_value: number | null;
  distribution_status: string;
  notices_count: number;
  pending_acknowledgments: number;
}

export interface PortalMatterSummary {
  matter_id: string;
  decedent_name: string;
  estate_type: string;
  jurisdiction_state: string;
  phase: MatterPhase;
  completion_percentage: number;
  estimated_completion: string | null;
}

export interface PortalOverviewResponse {
  matter: PortalMatterSummary;
  your_role: string;
  your_relationship: string | null;
  contacts: PortalContactInfo[];
  milestones: PortalMilestone[];
  distribution: PortalDistributionSummary;
  firm_name: string;
  firm_logo_url: string | null;
}

export interface PortalDocumentItem {
  id: string;
  filename: string;
  doc_type: string | null;
  size_bytes: number;
  shared_at: string;
}

export interface PortalDocumentsResponse {
  documents: PortalDocumentItem[];
  total: number;
}

export interface PortalMessageItem {
  id: string;
  sender_name: string;
  type: string;
  subject: string | null;
  body: string;
  created_at: string;
  requires_acknowledgment: boolean;
  acknowledged: boolean;
}

export interface PortalMessagesResponse {
  messages: PortalMessageItem[];
  total: number;
}

export interface PortalMessageCreate {
  subject?: string;
  body: string;
}

// ─── Filter / query params ──────────────────────────────────────────────────

export interface PaginationParams {
  page?: number;
  per_page?: number;
}

export interface MatterFilters extends PaginationParams {
  status?: MatterStatus;
  search?: string;
}

// ─── Portfolio ────────────────────────────────────────────────────────────────

export type RiskLevel = 'green' | 'amber' | 'red';

export interface PortfolioMatterItem {
  matter: Matter;
  total_task_count: number;
  complete_task_count: number;
  open_task_count: number;
  overdue_task_count: number;
  approaching_deadline_count: number;
  next_deadline: string | null;
  has_dispute: boolean;
  oldest_blocked_task_days: number | null;
  risk_level: RiskLevel;
}

export interface PortfolioSummary {
  total_active_matters: number;
  total_overdue_tasks: number;
  approaching_deadlines_this_week: number;
  matters_by_phase: Record<string, number>;
}

export interface PortfolioResponse {
  summary: PortfolioSummary;
  data: PortfolioMatterItem[];
  meta: PaginationMeta;
}

// ─── Reports ──────────────────────────────────────────────────────────────────

export interface ReportType {
  type: string;
  label: string;
  formats: string[];
}

export interface ReportJobStatus {
  job_id: string;
  status: 'processing' | 'completed' | 'failed';
  download_url?: string | null;
  filename?: string | null;
}

export interface TaskFilters extends PaginationParams {
  phase?: TaskPhase;
  status?: TaskStatus;
  priority?: TaskPriority;
  assigned_to?: string;
}

export interface AssetFilters extends PaginationParams {
  asset_type?: AssetType;
  status?: AssetStatus;
}

export interface DeadlineFilters extends PaginationParams {
  status?: DeadlineStatus;
}

export interface CommunicationFilters extends PaginationParams {
  type?: CommunicationType;
}

export interface EventFilters {
  cursor?: string;
  per_page?: number;
  entity_type?: string;
  action?: string;
}

// ─── Billing / Subscriptions ────────────────────────────────────────────────

export type SubscriptionStatus =
  | 'trialing'
  | 'active'
  | 'past_due'
  | 'canceled'
  | 'unpaid'
  | 'incomplete'
  | 'paused';

export type BillingInterval = 'month' | 'year';

export interface TierLimits {
  max_matters: number;
  max_users: number;
  monthly_price_cents: number;
  annual_price_cents: number;
  stripe_monthly_price_id?: string | null;
  stripe_annual_price_id?: string | null;
}

export interface SubscriptionInfo {
  id: string;
  firm_id: string;
  tier: SubscriptionTier;
  status: SubscriptionStatus;
  billing_interval: BillingInterval;
  stripe_subscription_id?: string | null;
  current_period_start?: string | null;
  current_period_end?: string | null;
  cancel_at_period_end: boolean;
  canceled_at?: string | null;
  trial_end?: string | null;
  grace_period_end?: string | null;
  last_payment_error?: string | null;
  failed_payment_count: number;
  matter_count: number;
  user_count: number;
  last_invoice_amount?: number | null;
  last_invoice_paid_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UsageInfo {
  matter_count: number;
  matter_limit: number;
  user_count: number;
  user_limit: number;
}

export interface BillingOverview {
  subscription: SubscriptionInfo | null;
  tier_limits: Record<string, TierLimits>;
  usage: UsageInfo;
}

export interface CheckoutSessionResponse {
  checkout_url: string;
  session_id: string;
}

export interface PortalSessionResponse {
  portal_url: string;
}

export interface Invoice {
  id: string;
  amount_due: number;
  amount_paid: number;
  currency: string;
  status?: string | null;
  invoice_url?: string | null;
  invoice_pdf?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  created?: string | null;
}

export interface InvoiceListResponse {
  invoices: Invoice[];
  has_more: boolean;
}

export interface CreateCheckoutRequest {
  tier: string;
  billing_interval?: string;
  success_url?: string;
  cancel_url?: string;
}

export interface CreatePortalSessionRequest {
  return_url?: string;
}

// ─── Integrations ───────────────────────────────────────────────────────────

export type IntegrationProvider = 'clio' | 'quickbooks' | 'xero' | 'docusign';
export type IntegrationConnectionStatus = 'connected' | 'disconnected' | 'error' | 'pending';
export type SyncStatusType = 'idle' | 'syncing' | 'success' | 'failed';

export interface IntegrationConnection {
  id: string;
  firm_id: string;
  provider: IntegrationProvider;
  status: IntegrationConnectionStatus;
  external_account_id?: string | null;
  external_account_name?: string | null;
  last_sync_at?: string | null;
  last_sync_status: SyncStatusType;
  last_sync_error?: string | null;
  settings: Record<string, unknown>;
  connected_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface IntegrationListResponse {
  connections: IntegrationConnection[];
}

export interface OAuthInitResponse {
  authorize_url: string;
  state: string;
}

export interface SyncRequest {
  resource: 'matters' | 'time_entries' | 'contacts' | 'distributions' | 'transactions' | 'account_balances';
  direction?: string;
  matter_id?: string;
}

export interface SyncResultResponse {
  resource: string;
  direction: string;
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
  synced_at?: string | null;
}

export interface ClioSettingsUpdate {
  auto_sync_matters?: boolean;
  auto_sync_time_entries?: boolean;
  auto_sync_contacts?: boolean;
  sync_interval_minutes?: number;
  default_practice_area?: string;
}

export interface QBAccountBalance {
  qbo_id: string;
  name: string;
  account_type: string;
  account_sub_type: string;
  current_balance: number;
  currency: string;
  active: boolean;
}

export interface QBBalancesResponse {
  resource: string;
  direction: string;
  accounts: QBAccountBalance[];
  errors: string[];
  synced_at?: string | null;
}

export interface DisconnectResponse {
  disconnected: boolean;
  provider: string;
}

// ─── DocuSign / Signatures ──────────────────────────────────────────────────

export type SignatureRequestStatus =
  | 'draft' | 'sent' | 'delivered' | 'signed'
  | 'completed' | 'declined' | 'voided' | 'expired';

export type SignatureRequestType =
  | 'distribution_consent' | 'beneficiary_acknowledgment'
  | 'executor_oath' | 'general';

export interface SignerInfo {
  email: string;
  name: string;
  role?: string;
  stakeholder_id?: string;
}

export interface SendForSignatureRequest {
  document_id: string;
  request_type?: SignatureRequestType;
  subject: string;
  message?: string;
  signers: SignerInfo[];
}

export interface SignatureRequest {
  id: string;
  matter_id: string;
  document_id?: string | null;
  request_type: SignatureRequestType;
  status: SignatureRequestStatus;
  envelope_id?: string | null;
  subject: string;
  message?: string | null;
  signers: Array<{
    email: string;
    name: string;
    role: string;
    status?: string | null;
    signed_at?: string | null;
    stakeholder_id?: string | null;
  }>;
  sent_by: string;
  sent_at?: string | null;
  completed_at?: string | null;
  voided_at?: string | null;
  expires_at?: string | null;
  signed_document_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SignatureRequestListResponse {
  data: SignatureRequest[];
  total: number;
}

export interface VoidEnvelopeRequest {
  reason?: string;
}

// ─── White-Label / Branding ─────────────────────────────────────────────────

export interface WhiteLabelConfig {
  logo_url?: string | null;
  logo_dark_url?: string | null;
  favicon_url?: string | null;
  primary_color?: string | null;
  secondary_color?: string | null;
  accent_color?: string | null;
  firm_display_name?: string | null;
  portal_welcome_text?: string | null;
  email_footer_text?: string | null;
  custom_domain?: string | null;
  custom_domain_verified?: boolean;
  powered_by_visible?: boolean;
}

export interface WhiteLabelUpdate {
  logo_url?: string | null;
  logo_dark_url?: string | null;
  favicon_url?: string | null;
  primary_color?: string | null;
  secondary_color?: string | null;
  accent_color?: string | null;
  firm_display_name?: string | null;
  portal_welcome_text?: string | null;
  email_footer_text?: string | null;
  custom_domain?: string | null;
  powered_by_visible?: boolean;
}

export interface LogoUploadResponse {
  upload_url: string;
  logo_url: string;
  field: string;
}

// ─── Enterprise SSO ─────────────────────────────────────────────────────────

export interface SSOConfig {
  id: string;
  firm_id: string;
  protocol: 'saml' | 'oidc';
  saml_metadata_url?: string | null;
  saml_entity_id?: string | null;
  saml_sso_url?: string | null;
  oidc_discovery_url?: string | null;
  oidc_client_id?: string | null;
  auth0_connection_id?: string | null;
  auth0_connection_name?: string | null;
  enabled: boolean;
  enforce_sso: boolean;
  auto_provision: boolean;
  default_role: string;
  allowed_domains: string[];
  verified: boolean;
  verified_at?: string | null;
  last_login_at?: string | null;
  configured_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SSOConfigCreate {
  protocol: 'saml' | 'oidc';
  saml_metadata_url?: string;
  saml_metadata_xml?: string;
  oidc_discovery_url?: string;
  oidc_client_id?: string;
  oidc_client_secret?: string;
  enforce_sso?: boolean;
  auto_provision?: boolean;
  default_role?: string;
  allowed_domains?: string[];
}

export interface SSOConfigUpdate {
  enabled?: boolean;
  enforce_sso?: boolean;
  auto_provision?: boolean;
  default_role?: string;
  allowed_domains?: string[];
  saml_metadata_url?: string;
  oidc_discovery_url?: string;
  oidc_client_id?: string;
  oidc_client_secret?: string;
}

export interface SSOLoginUrlResponse {
  login_url: string;
  connection_name: string;
  protocol: string;
}
