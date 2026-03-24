/**
 * Estate Executor OS — API Client
 *
 * Typed HTTP client that automatically attaches Auth0 access tokens
 * and provides methods for every backend endpoint.
 */

import type {
  AcceptInviteResponse,
  AIAnomalyResponse,
  AIUsageStats,
  AIClassifyResponse,
  AIExtractResponse,
  AILetterDraftRequest,
  AILetterDraftResponse,
  AISuggestTasksResponse,
  AssetCreate,
  AssetDetail,
  AssetFilters,
  AssetLinkDocument,
  AssetListItem,
  AssetUpdate,
  AssetValuation,
  BulkDownloadRequest,
  BulkDownloadStatusResponse,
  CalendarResponse,
  CommunicationCreate,
  CommunicationFilters,
  CommunicationResponse,
  CursorPaginatedResponse,
  DeadlineCreate,
  DeadlineFilters,
  DeadlineResponse,
  DeadlineUpdate,
  DisputeFlagCreate,
  DisputeStatusUpdate,
  ActiveDisputes,
  MilestoneStatusResponse,
  MilestoneSettingUpdate,
  TimeEntry,
  TimeEntryCreate,
  TimeEntryUpdate,
  TimeEntryListResponse,
  TimeTrackingSummary,
  DocumentConfirmType,
  DocumentDetail,
  DocumentRegister,
  DocumentRequestCreate,
  DocumentResponse,
  DocumentUploadRequest,
  DocumentUploadURL,
  DownloadURLResponse,
  Entity,
  EntityCreate,
  EntityMapResponse,
  EntityUpdate,
  EventFilters,
  EventResponse,
  Firm,
  FirmCreate,
  FirmMember,
  FirmUpdate,
  InviteMemberRequest,
  Matter,
  MatterCreate,
  MatterDashboard,
  MatterFilters,
  MatterUpdate,
  PaginatedResponse,
  PortfolioResponse,
  ReportJobStatus,
  ReportType,
  RegisterVersionRequest,
  Stakeholder,
  StakeholderInvite,
  StakeholderUpdate,
  Task,
  TaskAssign,
  TaskComplete,
  TaskCreate,
  TaskDetail,
  TaskFilters,
  TaskGenerateRequest,
  TaskLinkDocument,
  TaskUpdate,
  TaskWaive,
  UpdateMemberRoleRequest,
  UserProfile,
  PortalBeneficiaryMattersResponse,
  PortalOverviewResponse,
  PortalDocumentsResponse,
  PortalMessagesResponse,
  PortalMessageCreate,
  PortalMessageItem,
  DistributionCreate,
  DistributionResponse,
  DistributionSummaryResponse,
} from './types';

// ─── Error classes ───────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
    public errors?: Array<{ code: string; message: string; field?: string }>,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class NotFoundError extends ApiError {
  constructor(message = 'Resource not found') {
    super(404, message, 'NOT_FOUND');
    this.name = 'NotFoundError';
  }
}

export class ConflictError extends ApiError {
  constructor(message = 'Conflict') {
    super(409, message, 'CONFLICT');
    this.name = 'ConflictError';
  }
}

export class ServerError extends ApiError {
  constructor(message = 'Internal server error') {
    super(500, message, 'SERVER_ERROR');
    this.name = 'ServerError';
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function buildQueryString(params?: Record<string, any>): string {
  if (!params) return '';
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) {
      qs.set(k, String(v));
    }
  }
  const s = qs.toString();
  return s ? `?${s}` : '';
}

export type GetAccessTokenFn = () => Promise<string | null>;

// ─── API Client ──────────────────────────────────────────────────────────────

export class ApiClient {
  private baseUrl: string;
  private getAccessToken: GetAccessTokenFn;

  constructor(opts?: { baseUrl?: string; getAccessToken?: GetAccessTokenFn }) {
    this.baseUrl =
      opts?.baseUrl ??
      process.env.NEXT_PUBLIC_API_URL ??
      'http://localhost:8000/api/v1';
    this.getAccessToken = opts?.getAccessToken ?? (async () => null);
  }

  // ── Generic request method ──────────────────────────────────────────────

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    const token = await this.getAccessToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const url = `${this.baseUrl}${path}`;

    if (process.env.NODE_ENV === 'development') {
      console.debug(`[API] ${method} ${path}`);
    }

    const res = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!res.ok) {
      await this.handleErrorResponse(res);
    }

    if (res.status === 204) {
      return undefined as T;
    }

    return res.json() as Promise<T>;
  }

  private async handleErrorResponse(res: Response): Promise<never> {
    let errorBody: {
      detail?: string;
      errors?: Array<{ code: string; message: string; field?: string }>;
    } | null = null;
    try {
      errorBody = await res.json();
    } catch {
      // response body is not JSON
    }

    const message =
      errorBody?.detail ?? `Request failed with status ${res.status}`;

    if (res.status === 401) {
      if (typeof window !== 'undefined') {
        window.location.href = '/auth/login';
      }
      throw new ApiError(401, 'Unauthorized');
    }

    if (res.status === 404) {
      throw new NotFoundError(message);
    }

    if (res.status === 409) {
      throw new ConflictError(message);
    }

    if (res.status >= 500) {
      throw new ServerError(message);
    }

    throw new ApiError(res.status, message, undefined, errorBody?.errors);
  }

  private get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path);
  }

  private post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>('POST', path, body);
  }

  private patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>('PATCH', path, body);
  }

  private put<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>('PUT', path, body);
  }

  private del<T = void>(path: string): Promise<T> {
    return this.request<T>('DELETE', path);
  }

  // ─── Auth ─────────────────────────────────────────────────────────────

  async getMe(): Promise<UserProfile> {
    return this.get('/auth/me');
  }

  async acceptInvite(token: string): Promise<AcceptInviteResponse> {
    return this.post('/auth/accept-invite', { invite_token: token });
  }

  // ─── Firms ────────────────────────────────────────────────────────────

  async createFirm(data: FirmCreate): Promise<Firm> {
    return this.post('/firms', data);
  }

  async getFirms(): Promise<PaginatedResponse<Firm>> {
    return this.get('/firms');
  }

  async getFirm(firmId: string): Promise<Firm> {
    return this.get(`/firms/${firmId}`);
  }

  async updateFirm(firmId: string, data: FirmUpdate): Promise<Firm> {
    return this.patch(`/firms/${firmId}`, data);
  }

  async getFirmMembers(
    firmId: string,
  ): Promise<PaginatedResponse<FirmMember>> {
    return this.get(`/firms/${firmId}/members`);
  }

  async inviteFirmMember(
    firmId: string,
    data: InviteMemberRequest,
  ): Promise<FirmMember> {
    return this.post(`/firms/${firmId}/members`, data);
  }

  async updateFirmMember(
    firmId: string,
    membershipId: string,
    data: UpdateMemberRoleRequest,
  ): Promise<FirmMember> {
    return this.patch(`/firms/${firmId}/members/${membershipId}`, data);
  }

  async removeFirmMember(
    firmId: string,
    membershipId: string,
  ): Promise<void> {
    return this.del(`/firms/${firmId}/members/${membershipId}`);
  }

  // ─── Matters ──────────────────────────────────────────────────────────

  async createMatter(firmId: string, data: MatterCreate): Promise<Matter> {
    return this.post(`/firms/${firmId}/matters`, data);
  }

  async getMatters(
    firmId: string,
    params?: MatterFilters,
  ): Promise<PaginatedResponse<Matter>> {
    return this.get(`/firms/${firmId}/matters${buildQueryString(params)}`);
  }

  async getPortfolio(
    firmId: string,
    params?: MatterFilters,
  ): Promise<PortfolioResponse> {
    const qs = buildQueryString({ ...params, view: "portfolio" });
    return this.get(`/firms/${firmId}/matters${qs}`);
  }

  async getMatterDashboard(
    firmId: string,
    matterId: string,
  ): Promise<MatterDashboard> {
    return this.get(`/firms/${firmId}/matters/${matterId}`);
  }

  async updateMatter(
    firmId: string,
    matterId: string,
    data: MatterUpdate,
  ): Promise<Matter> {
    return this.patch(`/firms/${firmId}/matters/${matterId}`, data);
  }

  async closeMatter(firmId: string, matterId: string): Promise<Matter> {
    return this.post(`/firms/${firmId}/matters/${matterId}/close`);
  }

  // ─── Tasks ────────────────────────────────────────────────────────────

  private taskBase(firmId: string, matterId: string) {
    return `/firms/${firmId}/matters/${matterId}/tasks`;
  }

  async getTasks(
    firmId: string,
    matterId: string,
    params?: TaskFilters,
  ): Promise<PaginatedResponse<Task>> {
    return this.get(
      `${this.taskBase(firmId, matterId)}${buildQueryString(params)}`,
    );
  }

  async createTask(
    firmId: string,
    matterId: string,
    data: TaskCreate,
  ): Promise<Task> {
    return this.post(this.taskBase(firmId, matterId), data);
  }

  async generateTasks(
    firmId: string,
    matterId: string,
    data?: TaskGenerateRequest,
  ): Promise<PaginatedResponse<Task>> {
    return this.post(
      `${this.taskBase(firmId, matterId)}/generate`,
      data ?? {},
    );
  }

  async getTask(
    firmId: string,
    matterId: string,
    taskId: string,
  ): Promise<TaskDetail> {
    return this.get(`${this.taskBase(firmId, matterId)}/${taskId}`);
  }

  async updateTask(
    firmId: string,
    matterId: string,
    taskId: string,
    data: TaskUpdate,
  ): Promise<Task> {
    return this.patch(`${this.taskBase(firmId, matterId)}/${taskId}`, data);
  }

  async completeTask(
    firmId: string,
    matterId: string,
    taskId: string,
    data?: TaskComplete,
  ): Promise<Task> {
    return this.post(
      `${this.taskBase(firmId, matterId)}/${taskId}/complete`,
      data ?? {},
    );
  }

  async waiveTask(
    firmId: string,
    matterId: string,
    taskId: string,
    data: TaskWaive,
  ): Promise<Task> {
    return this.post(
      `${this.taskBase(firmId, matterId)}/${taskId}/waive`,
      data,
    );
  }

  async assignTask(
    firmId: string,
    matterId: string,
    taskId: string,
    data: TaskAssign,
  ): Promise<Task> {
    return this.post(
      `${this.taskBase(firmId, matterId)}/${taskId}/assign`,
      data,
    );
  }

  async linkTaskDocument(
    firmId: string,
    matterId: string,
    taskId: string,
    data: TaskLinkDocument,
  ): Promise<void> {
    return this.post(
      `${this.taskBase(firmId, matterId)}/${taskId}/documents`,
      data,
    );
  }

  // ─── Assets ───────────────────────────────────────────────────────────

  private assetBase(firmId: string, matterId: string) {
    return `/firms/${firmId}/matters/${matterId}/assets`;
  }

  async getAssets(
    firmId: string,
    matterId: string,
    params?: AssetFilters,
  ): Promise<PaginatedResponse<AssetListItem>> {
    return this.get(
      `${this.assetBase(firmId, matterId)}${buildQueryString(params)}`,
    );
  }

  async createAsset(
    firmId: string,
    matterId: string,
    data: AssetCreate,
  ): Promise<AssetListItem> {
    return this.post(this.assetBase(firmId, matterId), data);
  }

  async getAsset(
    firmId: string,
    matterId: string,
    assetId: string,
  ): Promise<AssetDetail> {
    return this.get(`${this.assetBase(firmId, matterId)}/${assetId}`);
  }

  async updateAsset(
    firmId: string,
    matterId: string,
    assetId: string,
    data: AssetUpdate,
  ): Promise<AssetListItem> {
    return this.patch(`${this.assetBase(firmId, matterId)}/${assetId}`, data);
  }

  async deleteAsset(
    firmId: string,
    matterId: string,
    assetId: string,
  ): Promise<void> {
    return this.del(`${this.assetBase(firmId, matterId)}/${assetId}`);
  }

  async linkAssetDocument(
    firmId: string,
    matterId: string,
    assetId: string,
    data: AssetLinkDocument,
  ): Promise<void> {
    return this.post(
      `${this.assetBase(firmId, matterId)}/${assetId}/documents`,
      data,
    );
  }

  async addAssetValuation(
    firmId: string,
    matterId: string,
    assetId: string,
    data: AssetValuation,
  ): Promise<AssetListItem> {
    return this.post(
      `${this.assetBase(firmId, matterId)}/${assetId}/valuations`,
      data,
    );
  }

  // ─── Entities ─────────────────────────────────────────────────────────

  private entityBase(firmId: string, matterId: string) {
    return `/firms/${firmId}/matters/${matterId}/entities`;
  }

  async getEntities(firmId: string, matterId: string): Promise<Entity[]> {
    return this.get(this.entityBase(firmId, matterId));
  }

  async createEntity(
    firmId: string,
    matterId: string,
    data: EntityCreate,
  ): Promise<Entity> {
    return this.post(this.entityBase(firmId, matterId), data);
  }

  async getEntity(
    firmId: string,
    matterId: string,
    entityId: string,
  ): Promise<Entity> {
    return this.get(`${this.entityBase(firmId, matterId)}/${entityId}`);
  }

  async updateEntity(
    firmId: string,
    matterId: string,
    entityId: string,
    data: EntityUpdate,
  ): Promise<Entity> {
    return this.patch(
      `${this.entityBase(firmId, matterId)}/${entityId}`,
      data,
    );
  }

  async deleteEntity(
    firmId: string,
    matterId: string,
    entityId: string,
  ): Promise<void> {
    return this.del(`${this.entityBase(firmId, matterId)}/${entityId}`);
  }

  async getEntityMap(
    firmId: string,
    matterId: string,
  ): Promise<EntityMapResponse> {
    return this.get(`/firms/${firmId}/matters/${matterId}/entity-map`);
  }

  // ─── Stakeholders ────────────────────────────────────────────────────

  private stakeholderBase(firmId: string, matterId: string) {
    return `/firms/${firmId}/matters/${matterId}/stakeholders`;
  }

  async getStakeholders(
    firmId: string,
    matterId: string,
  ): Promise<PaginatedResponse<Stakeholder>> {
    return this.get(this.stakeholderBase(firmId, matterId));
  }

  async inviteStakeholder(
    firmId: string,
    matterId: string,
    data: StakeholderInvite,
  ): Promise<Stakeholder> {
    return this.post(this.stakeholderBase(firmId, matterId), data);
  }

  async updateStakeholder(
    firmId: string,
    matterId: string,
    stakeholderId: string,
    data: StakeholderUpdate,
  ): Promise<Stakeholder> {
    return this.patch(
      `${this.stakeholderBase(firmId, matterId)}/${stakeholderId}`,
      data,
    );
  }

  async removeStakeholder(
    firmId: string,
    matterId: string,
    stakeholderId: string,
  ): Promise<void> {
    return this.del(
      `${this.stakeholderBase(firmId, matterId)}/${stakeholderId}`,
    );
  }

  async resendStakeholderInvite(
    firmId: string,
    matterId: string,
    stakeholderId: string,
  ): Promise<Stakeholder> {
    return this.post(
      `${this.stakeholderBase(firmId, matterId)}/${stakeholderId}/resend-invite`,
    );
  }

  // ─── Documents ────────────────────────────────────────────────────────

  private docBase(firmId: string, matterId: string) {
    return `/firms/${firmId}/matters/${matterId}/documents`;
  }

  async getUploadUrl(
    firmId: string,
    matterId: string,
    data: DocumentUploadRequest,
  ): Promise<DocumentUploadURL> {
    return this.post(`${this.docBase(firmId, matterId)}/upload-url`, data);
  }

  async registerDocument(
    firmId: string,
    matterId: string,
    data: DocumentRegister,
  ): Promise<DocumentDetail> {
    return this.post(this.docBase(firmId, matterId), data);
  }

  async getDocuments(
    firmId: string,
    matterId: string,
  ): Promise<PaginatedResponse<DocumentResponse>> {
    return this.get(this.docBase(firmId, matterId));
  }

  async getDocument(
    firmId: string,
    matterId: string,
    docId: string,
  ): Promise<DocumentDetail> {
    return this.get(`${this.docBase(firmId, matterId)}/${docId}`);
  }

  async getDownloadUrl(
    firmId: string,
    matterId: string,
    docId: string,
  ): Promise<DownloadURLResponse> {
    return this.get(`${this.docBase(firmId, matterId)}/${docId}/download`);
  }

  async confirmDocType(
    firmId: string,
    matterId: string,
    docId: string,
    data: DocumentConfirmType,
  ): Promise<DocumentResponse> {
    return this.post(
      `${this.docBase(firmId, matterId)}/${docId}/confirm-type`,
      data,
    );
  }

  async requestDocument(
    firmId: string,
    matterId: string,
    data: DocumentRequestCreate,
  ): Promise<{ message: string }> {
    return this.post(`${this.docBase(firmId, matterId)}/request`, data);
  }

  async getReuploadUrl(
    firmId: string,
    matterId: string,
    docId: string,
  ): Promise<DocumentUploadURL> {
    return this.post(`${this.docBase(firmId, matterId)}/${docId}/reupload`);
  }

  async registerDocumentVersion(
    firmId: string,
    matterId: string,
    docId: string,
    data: RegisterVersionRequest,
  ): Promise<DocumentDetail> {
    return this.post(
      `${this.docBase(firmId, matterId)}/${docId}/version`,
      data,
    );
  }

  async bulkDownload(
    firmId: string,
    matterId: string,
    data: BulkDownloadRequest,
  ): Promise<BulkDownloadStatusResponse> {
    return this.post(`${this.docBase(firmId, matterId)}/bulk-download`, data);
  }

  async getBulkDownloadStatus(
    firmId: string,
    matterId: string,
    jobId: string,
  ): Promise<BulkDownloadStatusResponse> {
    return this.get(
      `${this.docBase(firmId, matterId)}/bulk-download/${jobId}`,
    );
  }

  // ─── Deadlines ────────────────────────────────────────────────────────

  private deadlineBase(firmId: string, matterId: string) {
    return `/firms/${firmId}/matters/${matterId}/deadlines`;
  }

  async getDeadlines(
    firmId: string,
    matterId: string,
    params?: DeadlineFilters,
  ): Promise<PaginatedResponse<DeadlineResponse>> {
    return this.get(
      `${this.deadlineBase(firmId, matterId)}${buildQueryString(params)}`,
    );
  }

  async createDeadline(
    firmId: string,
    matterId: string,
    data: DeadlineCreate,
  ): Promise<DeadlineResponse> {
    return this.post(this.deadlineBase(firmId, matterId), data);
  }

  async updateDeadline(
    firmId: string,
    matterId: string,
    deadlineId: string,
    data: DeadlineUpdate,
  ): Promise<DeadlineResponse> {
    return this.patch(
      `${this.deadlineBase(firmId, matterId)}/${deadlineId}`,
      data,
    );
  }

  async getDeadlineCalendar(
    firmId: string,
    matterId: string,
  ): Promise<CalendarResponse> {
    return this.get(`${this.deadlineBase(firmId, matterId)}/calendar`);
  }

  // ─── Communications ──────────────────────────────────────────────────

  private commBase(firmId: string, matterId: string) {
    return `/firms/${firmId}/matters/${matterId}/communications`;
  }

  async getCommunications(
    firmId: string,
    matterId: string,
    params?: CommunicationFilters,
  ): Promise<PaginatedResponse<CommunicationResponse>> {
    return this.get(
      `${this.commBase(firmId, matterId)}${buildQueryString(params)}`,
    );
  }

  async createCommunication(
    firmId: string,
    matterId: string,
    data: CommunicationCreate,
  ): Promise<CommunicationResponse> {
    return this.post(this.commBase(firmId, matterId), data);
  }

  async acknowledgeCommunication(
    firmId: string,
    matterId: string,
    commId: string,
  ): Promise<CommunicationResponse> {
    return this.post(
      `${this.commBase(firmId, matterId)}/${commId}/acknowledge`,
    );
  }

  async createDisputeFlag(
    firmId: string,
    matterId: string,
    data: DisputeFlagCreate,
  ): Promise<CommunicationResponse> {
    return this.post(
      `/firms/${firmId}/matters/${matterId}/dispute-flag`,
      data,
    );
  }

  async updateDisputeStatus(
    firmId: string,
    matterId: string,
    commId: string,
    data: DisputeStatusUpdate,
  ): Promise<CommunicationResponse> {
    return this.put(
      `/firms/${firmId}/matters/${matterId}/dispute-flag/${commId}`,
      data,
    );
  }

  async getActiveDisputes(
    firmId: string,
    matterId: string,
    entityType?: string,
  ): Promise<ActiveDisputes> {
    const params = entityType ? `?entity_type=${entityType}` : '';
    return this.get(
      `${this.commBase(firmId, matterId)}/disputes${params}`,
    );
  }

  // ─── Time Tracking ──────────────────────────────────────────────────

  private timeBase(firmId: string, matterId: string): string {
    return `/firms/${firmId}/matters/${matterId}/time`;
  }

  async getTimeEntries(
    firmId: string,
    matterId: string,
    params?: { task_id?: string; stakeholder_id?: string; billable?: boolean; date_from?: string; date_to?: string; page?: number; per_page?: number },
  ): Promise<TimeEntryListResponse> {
    return this.get(
      `${this.timeBase(firmId, matterId)}${buildQueryString(params)}`,
    );
  }

  async createTimeEntry(
    firmId: string,
    matterId: string,
    data: TimeEntryCreate,
  ): Promise<TimeEntry> {
    return this.post(this.timeBase(firmId, matterId), data);
  }

  async updateTimeEntry(
    firmId: string,
    matterId: string,
    entryId: string,
    data: TimeEntryUpdate,
  ): Promise<TimeEntry> {
    return this.put(`${this.timeBase(firmId, matterId)}/${entryId}`, data);
  }

  async deleteTimeEntry(
    firmId: string,
    matterId: string,
    entryId: string,
  ): Promise<void> {
    return this.del(`${this.timeBase(firmId, matterId)}/${entryId}`);
  }

  async getTimeSummary(
    firmId: string,
    matterId: string,
  ): Promise<TimeTrackingSummary> {
    return this.get(`${this.timeBase(firmId, matterId)}/summary`);
  }

  // ─── Milestones ──────────────────────────────────────────────────────

  async getMilestones(
    firmId: string,
    matterId: string,
  ): Promise<MilestoneStatusResponse> {
    return this.get(
      `/firms/${firmId}/matters/${matterId}/milestones`,
    );
  }

  async updateMilestoneSetting(
    firmId: string,
    matterId: string,
    data: MilestoneSettingUpdate,
  ): Promise<{ milestone_notifications: Record<string, boolean> }> {
    return this.put(
      `/firms/${firmId}/matters/${matterId}/milestones/settings`,
      data,
    );
  }

  // ─── Events ──────────────────────────────────────────────────────────

  async getEvents(
    firmId: string,
    matterId: string,
    params?: EventFilters,
  ): Promise<CursorPaginatedResponse<EventResponse>> {
    return this.get(
      `/firms/${firmId}/matters/${matterId}/events${buildQueryString(params)}`,
    );
  }

  // ─── Reports ────────────────────────────────────────────────────────

  private reportBase(firmId: string, matterId: string) {
    return `/firms/${firmId}/matters/${matterId}/reports`;
  }

  async getReportTypes(
    firmId: string,
    matterId: string,
  ): Promise<ReportType[]> {
    return this.get(this.reportBase(firmId, matterId));
  }

  generateReportUrl(
    firmId: string,
    matterId: string,
    reportType: string,
    format: string = "pdf",
  ): string {
    return `${this.baseUrl}${this.reportBase(firmId, matterId)}/${reportType}?format=${format}`;
  }

  async generateReportAsync(
    firmId: string,
    matterId: string,
    reportType: string,
    format: string = "pdf",
  ): Promise<ReportJobStatus> {
    return this.post(
      `${this.reportBase(firmId, matterId)}/${reportType}/async?format=${format}`,
      {},
    );
  }

  async getReportJobStatus(
    firmId: string,
    matterId: string,
    jobId: string,
  ): Promise<ReportJobStatus> {
    return this.get(
      `${this.reportBase(firmId, matterId)}/jobs/${jobId}`,
    );
  }

  // ─── AI ──────────────────────────────────────────────────────────────

  private aiBase(firmId: string, matterId: string) {
    return `/firms/${firmId}/matters/${matterId}/ai`;
  }

  async classifyDocument(
    firmId: string,
    matterId: string,
    docId: string,
  ): Promise<AIClassifyResponse> {
    return this.post(`${this.aiBase(firmId, matterId)}/classify/${docId}`);
  }

  async extractData(
    firmId: string,
    matterId: string,
    docId: string,
  ): Promise<AIExtractResponse> {
    return this.post(`${this.aiBase(firmId, matterId)}/extract/${docId}`);
  }

  async draftLetter(
    firmId: string,
    matterId: string,
    data: AILetterDraftRequest,
  ): Promise<AILetterDraftResponse> {
    return this.post(`${this.aiBase(firmId, matterId)}/draft-letter`, data);
  }

  async suggestTasks(
    firmId: string,
    matterId: string,
  ): Promise<AISuggestTasksResponse> {
    return this.post(`${this.aiBase(firmId, matterId)}/suggest-tasks`);
  }

  async detectAnomalies(
    firmId: string,
    matterId: string,
  ): Promise<AIAnomalyResponse> {
    return this.post(`${this.aiBase(firmId, matterId)}/detect-anomalies`);
  }

  async getAIUsageStats(
    firmId: string,
    matterId: string,
  ): Promise<AIUsageStats> {
    return this.get(`${this.aiBase(firmId, matterId)}/usage-stats`);
  }

  // ─── Distributions ─────────────────────────────────────────────────────

  private distBase(firmId: string, matterId: string) {
    return `/firms/${firmId}/matters/${matterId}/distributions`;
  }

  async getDistributions(
    firmId: string,
    matterId: string,
    params?: { page?: number; per_page?: number; beneficiary_id?: string },
  ): Promise<PaginatedResponse<DistributionResponse>> {
    return this.get(
      `${this.distBase(firmId, matterId)}${buildQueryString(params)}`,
    );
  }

  async recordDistribution(
    firmId: string,
    matterId: string,
    data: DistributionCreate,
  ): Promise<DistributionResponse> {
    return this.post(this.distBase(firmId, matterId), data);
  }

  async acknowledgeDistribution(
    firmId: string,
    matterId: string,
    distId: string,
  ): Promise<DistributionResponse> {
    return this.post(
      `${this.distBase(firmId, matterId)}/${distId}/acknowledge`,
    );
  }

  async getDistributionSummary(
    firmId: string,
    matterId: string,
  ): Promise<DistributionSummaryResponse> {
    return this.get(`${this.distBase(firmId, matterId)}/summary`);
  }

  // ─── Portal (Beneficiary) ──────────────────────────────────────────────

  async getPortalMatters(): Promise<PortalBeneficiaryMattersResponse> {
    return this.get('/portal/matters');
  }

  async getPortalOverview(matterId: string): Promise<PortalOverviewResponse> {
    return this.get(`/portal/matters/${matterId}/overview`);
  }

  async getPortalDocuments(matterId: string): Promise<PortalDocumentsResponse> {
    return this.get(`/portal/matters/${matterId}/documents`);
  }

  async getPortalMessages(matterId: string): Promise<PortalMessagesResponse> {
    return this.get(`/portal/matters/${matterId}/messages`);
  }

  async postPortalMessage(
    matterId: string,
    data: PortalMessageCreate,
  ): Promise<PortalMessageItem> {
    return this.post(`/portal/matters/${matterId}/messages`, data);
  }

  async acknowledgePortalNotice(
    matterId: string,
    commId: string,
  ): Promise<PortalMessageItem> {
    return this.post(
      `/portal/matters/${matterId}/messages/${commId}/acknowledge`,
    );
  }
}
