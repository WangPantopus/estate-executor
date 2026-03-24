"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { useApi } from "./use-api";
import type {
  AssetCreate,
  AssetFilters,
  AssetUpdate,
  AssetValuation,
  CommunicationCreate,
  CommunicationFilters,
  DeadlineCreate,
  DeadlineFilters,
  DeadlineUpdate,
  DistributionCreate,
  EntityCreate,
  EntityUpdate,
  EventFilters,
  MatterCreate,
  MatterFilters,
  MatterUpdate,
  StakeholderInvite,
  TaskCreate,
  TaskFilters,
  TaskUpdate,
  UserProfile,
  DocumentConfirmType,
  DocumentRequestCreate,
  DisputeFlagCreate,
  DisputeStatusUpdate,
  MilestoneSettingUpdate,
  TimeEntryCreate,
  TimeEntryUpdate,
  FirmUpdate,
  InviteMemberRequest,
  UpdateMemberRoleRequest,
} from "@/lib/types";

// ─── Query key factories ────────────────────────────────────────────────────

export const queryKeys = {
  me: ["me"] as const,
  firms: ["firms"] as const,
  firm: (firmId: string) => ["firms", firmId] as const,
  firmMembers: (firmId: string) => ["firms", firmId, "members"] as const,
  matters: (firmId: string, filters?: MatterFilters) =>
    ["firms", firmId, "matters", filters] as const,
  matterDashboard: (firmId: string, matterId: string) =>
    ["firms", firmId, "matters", matterId, "dashboard"] as const,
  tasks: (firmId: string, matterId: string, filters?: TaskFilters) =>
    ["firms", firmId, "matters", matterId, "tasks", filters] as const,
  task: (firmId: string, matterId: string, taskId: string) =>
    ["firms", firmId, "matters", matterId, "tasks", taskId] as const,
  assets: (firmId: string, matterId: string, filters?: AssetFilters) =>
    ["firms", firmId, "matters", matterId, "assets", filters] as const,
  asset: (firmId: string, matterId: string, assetId: string) =>
    ["firms", firmId, "matters", matterId, "assets", assetId] as const,
  entities: (firmId: string, matterId: string) =>
    ["firms", firmId, "matters", matterId, "entities"] as const,
  entityMap: (firmId: string, matterId: string) =>
    ["firms", firmId, "matters", matterId, "entity-map"] as const,
  stakeholders: (firmId: string, matterId: string) =>
    ["firms", firmId, "matters", matterId, "stakeholders"] as const,
  deadlines: (firmId: string, matterId: string, filters?: DeadlineFilters) =>
    ["firms", firmId, "matters", matterId, "deadlines", filters] as const,
  deadlineCalendar: (firmId: string, matterId: string) =>
    ["firms", firmId, "matters", matterId, "deadlines", "calendar"] as const,
  communications: (
    firmId: string,
    matterId: string,
    filters?: CommunicationFilters,
  ) =>
    [
      "firms",
      firmId,
      "matters",
      matterId,
      "communications",
      filters,
    ] as const,
  events: (firmId: string, matterId: string, filters?: EventFilters) =>
    ["firms", firmId, "matters", matterId, "events", filters] as const,
  documents: (firmId: string, matterId: string) =>
    ["firms", firmId, "matters", matterId, "documents"] as const,
  document: (firmId: string, matterId: string, docId: string) =>
    ["firms", firmId, "matters", matterId, "documents", docId] as const,
  distributions: (firmId: string, matterId: string) =>
    ["firms", firmId, "matters", matterId, "distributions"] as const,
  distributionSummary: (firmId: string, matterId: string) =>
    ["firms", firmId, "matters", matterId, "distributions", "summary"] as const,
};

// ─── Auth ────────────────────────────────────────────────────────────────────

export function useCurrentUser(
  options?: Partial<UseQueryOptions<UserProfile>>,
) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: () => api.getMe(),
    ...options,
  });
}

// ─── Firms ──────────────────────────────────────────────────────────────────

export function useFirm(firmId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.firm(firmId),
    queryFn: () => api.getFirm(firmId),
    enabled: !!firmId,
  });
}

export function useUpdateFirm(firmId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: FirmUpdate) => api.updateFirm(firmId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.firm(firmId) });
      qc.invalidateQueries({ queryKey: queryKeys.me });
    },
  });
}

export function useFirmMembers(firmId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.firmMembers(firmId),
    queryFn: () => api.getFirmMembers(firmId),
    enabled: !!firmId,
  });
}

export function useInviteFirmMember(firmId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: InviteMemberRequest) => api.inviteFirmMember(firmId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.firmMembers(firmId) });
    },
  });
}

export function useUpdateFirmMember(firmId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ membershipId, data }: { membershipId: string; data: UpdateMemberRoleRequest }) =>
      api.updateFirmMember(firmId, membershipId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.firmMembers(firmId) });
    },
  });
}

export function useRemoveFirmMember(firmId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (membershipId: string) => api.removeFirmMember(firmId, membershipId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.firmMembers(firmId) });
    },
  });
}

// ─── Matters ─────────────────────────────────────────────────────────────────

export function useMatters(firmId: string, filters?: MatterFilters) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.matters(firmId, filters),
    queryFn: () => api.getMatters(firmId, filters),
    enabled: !!firmId,
  });
}

export function usePortfolio(firmId: string, filters?: MatterFilters) {
  const api = useApi();
  return useQuery({
    queryKey: ["firms", firmId, "portfolio", filters] as const,
    queryFn: () => api.getPortfolio(firmId, filters),
    enabled: !!firmId,
  });
}

export function useMatterDashboard(firmId: string, matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.matterDashboard(firmId, matterId),
    queryFn: () => api.getMatterDashboard(firmId, matterId),
    enabled: !!firmId && !!matterId,
  });
}

export function useCreateMatter(firmId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MatterCreate) => api.createMatter(firmId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.matters(firmId) });
    },
  });
}

export function useUpdateMatter(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MatterUpdate) =>
      api.updateMatter(firmId, matterId, data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.matterDashboard(firmId, matterId),
      });
      qc.invalidateQueries({ queryKey: queryKeys.matters(firmId) });
    },
  });
}

export function useCloseMatter(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.closeMatter(firmId, matterId),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.matterDashboard(firmId, matterId),
      });
      qc.invalidateQueries({ queryKey: queryKeys.matters(firmId) });
    },
  });
}

// ─── Tasks ───────────────────────────────────────────────────────────────────

export function useTasks(
  firmId: string,
  matterId: string,
  filters?: TaskFilters,
) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.tasks(firmId, matterId, filters),
    queryFn: () => api.getTasks(firmId, matterId, filters),
    enabled: !!firmId && !!matterId,
  });
}

export function useTask(firmId: string, matterId: string, taskId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.task(firmId, matterId, taskId),
    queryFn: () => api.getTask(firmId, matterId, taskId),
    enabled: !!firmId && !!matterId && !!taskId,
  });
}

export function useCreateTask(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskCreate) =>
      api.createTask(firmId, matterId, data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.tasks(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.matterDashboard(firmId, matterId),
      });
    },
  });
}

export function useUpdateTask(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      taskId,
      data,
    }: {
      taskId: string;
      data: TaskUpdate;
    }) => api.updateTask(firmId, matterId, taskId, data),
    onSuccess: (_, { taskId }) => {
      qc.invalidateQueries({
        queryKey: queryKeys.task(firmId, matterId, taskId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.tasks(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.matterDashboard(firmId, matterId),
      });
    },
  });
}

export function useCompleteTask(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      taskId,
      notes,
    }: {
      taskId: string;
      notes?: string;
    }) => api.completeTask(firmId, matterId, taskId, notes ? { notes } : undefined),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.tasks(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.matterDashboard(firmId, matterId),
      });
    },
  });
}

export function useWaiveTask(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      taskId,
      reason,
    }: {
      taskId: string;
      reason: string;
    }) => api.waiveTask(firmId, matterId, taskId, { reason }),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.tasks(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.matterDashboard(firmId, matterId),
      });
    },
  });
}

export function useAssignTask(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      taskId,
      stakeholderId,
    }: {
      taskId: string;
      stakeholderId: string;
    }) =>
      api.assignTask(firmId, matterId, taskId, {
        stakeholder_id: stakeholderId,
      }),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.tasks(firmId, matterId),
      });
    },
  });
}

// ─── Assets ──────────────────────────────────────────────────────────────────

export function useAssets(
  firmId: string,
  matterId: string,
  filters?: AssetFilters,
) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.assets(firmId, matterId, filters),
    queryFn: () => api.getAssets(firmId, matterId, filters),
    enabled: !!firmId && !!matterId,
  });
}

export function useAsset(firmId: string, matterId: string, assetId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.asset(firmId, matterId, assetId),
    queryFn: () => api.getAsset(firmId, matterId, assetId),
    enabled: !!firmId && !!matterId && !!assetId,
  });
}

export function useCreateAsset(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AssetCreate) =>
      api.createAsset(firmId, matterId, data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.assets(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.matterDashboard(firmId, matterId),
      });
    },
  });
}

export function useUpdateAsset(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      assetId,
      data,
    }: {
      assetId: string;
      data: AssetUpdate;
    }) => api.updateAsset(firmId, matterId, assetId, data),
    onSuccess: (_, { assetId }) => {
      qc.invalidateQueries({
        queryKey: queryKeys.asset(firmId, matterId, assetId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.assets(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.matterDashboard(firmId, matterId),
      });
    },
  });
}

export function useDeleteAsset(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (assetId: string) =>
      api.deleteAsset(firmId, matterId, assetId),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.assets(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.matterDashboard(firmId, matterId),
      });
    },
  });
}

export function useAddValuation(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      assetId,
      data,
    }: {
      assetId: string;
      data: AssetValuation;
    }) => api.addAssetValuation(firmId, matterId, assetId, data),
    onSuccess: (_, { assetId }) => {
      qc.invalidateQueries({
        queryKey: queryKeys.asset(firmId, matterId, assetId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.assets(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.matterDashboard(firmId, matterId),
      });
    },
  });
}

// ─── Entities ────────────────────────────────────────────────────────────────

export function useEntities(firmId: string, matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.entities(firmId, matterId),
    queryFn: () => api.getEntities(firmId, matterId),
    enabled: !!firmId && !!matterId,
  });
}

export function useEntityMap(firmId: string, matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.entityMap(firmId, matterId),
    queryFn: () => api.getEntityMap(firmId, matterId),
    enabled: !!firmId && !!matterId,
  });
}

export function useCreateEntity(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: EntityCreate) =>
      api.createEntity(firmId, matterId, data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.entities(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.entityMap(firmId, matterId),
      });
    },
  });
}

export function useUpdateEntity(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      entityId,
      data,
    }: {
      entityId: string;
      data: EntityUpdate;
    }) => api.updateEntity(firmId, matterId, entityId, data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.entities(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.entityMap(firmId, matterId),
      });
    },
  });
}

export function useDeleteEntity(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entityId: string) =>
      api.deleteEntity(firmId, matterId, entityId),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.entities(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.entityMap(firmId, matterId),
      });
    },
  });
}

// ─── Stakeholders ────────────────────────────────────────────────────────────

export function useStakeholders(firmId: string, matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.stakeholders(firmId, matterId),
    queryFn: () => api.getStakeholders(firmId, matterId),
    enabled: !!firmId && !!matterId,
  });
}

export function useInviteStakeholder(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: StakeholderInvite) =>
      api.inviteStakeholder(firmId, matterId, data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.stakeholders(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.matterDashboard(firmId, matterId),
      });
    },
  });
}

// ─── Deadlines ───────────────────────────────────────────────────────────────

export function useDeadlines(
  firmId: string,
  matterId: string,
  filters?: DeadlineFilters,
) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.deadlines(firmId, matterId, filters),
    queryFn: () => api.getDeadlines(firmId, matterId, filters),
    enabled: !!firmId && !!matterId,
  });
}

export function useDeadlineCalendar(firmId: string, matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.deadlineCalendar(firmId, matterId),
    queryFn: () => api.getDeadlineCalendar(firmId, matterId),
    enabled: !!firmId && !!matterId,
  });
}

export function useCreateDeadline(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DeadlineCreate) =>
      api.createDeadline(firmId, matterId, data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.deadlines(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.deadlineCalendar(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.matterDashboard(firmId, matterId),
      });
    },
  });
}

export function useUpdateDeadline(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      deadlineId,
      data,
    }: {
      deadlineId: string;
      data: DeadlineUpdate;
    }) => api.updateDeadline(firmId, matterId, deadlineId, data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.deadlines(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.deadlineCalendar(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: queryKeys.matterDashboard(firmId, matterId),
      });
    },
  });
}

// ─── Communications ─────────────────────────────────────────────────────────

export function useCommunications(
  firmId: string,
  matterId: string,
  filters?: CommunicationFilters,
) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.communications(firmId, matterId, filters),
    queryFn: () => api.getCommunications(firmId, matterId, filters),
    enabled: !!firmId && !!matterId,
  });
}

export function useCreateCommunication(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CommunicationCreate) =>
      api.createCommunication(firmId, matterId, data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.communications(firmId, matterId),
      });
    },
  });
}

export function useAcknowledgeCommunication(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (commId: string) =>
      api.acknowledgeCommunication(firmId, matterId, commId),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.communications(firmId, matterId),
      });
    },
  });
}

export function useCreateDisputeFlag(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DisputeFlagCreate) =>
      api.createDisputeFlag(firmId, matterId, data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.communications(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: [...queryKeys.communications(firmId, matterId), "disputes"],
      });
    },
  });
}

export function useUpdateDisputeStatus(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: { commId: string; data: DisputeStatusUpdate }) =>
      api.updateDisputeStatus(firmId, matterId, params.commId, params.data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.communications(firmId, matterId),
      });
      qc.invalidateQueries({
        queryKey: [...queryKeys.communications(firmId, matterId), "disputes"],
      });
    },
  });
}

export function useActiveDisputes(firmId: string, matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: [...queryKeys.communications(firmId, matterId), "disputes"],
    queryFn: () => api.getActiveDisputes(firmId, matterId),
  });
}

// ─── Time Tracking ───────────────────────────────────────────────────────────

export function useTimeEntries(
  firmId: string,
  matterId: string,
  params?: { task_id?: string; page?: number },
) {
  const api = useApi();
  return useQuery({
    queryKey: ["firms", firmId, "matters", matterId, "time", params],
    queryFn: () => api.getTimeEntries(firmId, matterId, params),
    enabled: !!firmId && !!matterId,
  });
}

export function useTimeSummary(firmId: string, matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: ["firms", firmId, "matters", matterId, "time", "summary"],
    queryFn: () => api.getTimeSummary(firmId, matterId),
    enabled: !!firmId && !!matterId,
  });
}

export function useCreateTimeEntry(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TimeEntryCreate) =>
      api.createTimeEntry(firmId, matterId, data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["firms", firmId, "matters", matterId, "time"],
      });
    },
  });
}

export function useUpdateTimeEntry(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: { entryId: string; data: TimeEntryUpdate }) =>
      api.updateTimeEntry(firmId, matterId, params.entryId, params.data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["firms", firmId, "matters", matterId, "time"],
      });
    },
  });
}

export function useDeleteTimeEntry(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) =>
      api.deleteTimeEntry(firmId, matterId, entryId),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["firms", firmId, "matters", matterId, "time"],
      });
    },
  });
}

// ─── Milestones ──────────────────────────────────────────────────────────────

export function useMilestones(firmId: string, matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: ["firms", firmId, "matters", matterId, "milestones"],
    queryFn: () => api.getMilestones(firmId, matterId),
  });
}

export function useUpdateMilestoneSetting(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MilestoneSettingUpdate) =>
      api.updateMilestoneSetting(firmId, matterId, data),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["firms", firmId, "matters", matterId, "milestones"],
      });
    },
  });
}

// ─── Events ──────────────────────────────────────────────────────────────────

export function useEvents(
  firmId: string,
  matterId: string,
  filters?: EventFilters,
) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.events(firmId, matterId, filters),
    queryFn: () => api.getEvents(firmId, matterId, filters),
    enabled: !!firmId && !!matterId,
  });
}

// ─── Documents ──────────────────────────────────────────────────────────────

export function useDocuments(firmId: string, matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.documents(firmId, matterId),
    queryFn: () => api.getDocuments(firmId, matterId),
    enabled: !!firmId && !!matterId,
  });
}

export function useDocument(firmId: string, matterId: string, docId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.document(firmId, matterId, docId),
    queryFn: () => api.getDocument(firmId, matterId, docId),
    enabled: !!firmId && !!matterId && !!docId,
  });
}

export function useConfirmDocType(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ docId, data }: { docId: string; data: DocumentConfirmType }) =>
      api.confirmDocType(firmId, matterId, docId, data),
    onSuccess: (_, { docId }) => {
      qc.invalidateQueries({ queryKey: queryKeys.document(firmId, matterId, docId) });
      qc.invalidateQueries({ queryKey: queryKeys.documents(firmId, matterId) });
    },
  });
}

export function useRequestDocument(firmId: string, matterId: string) {
  const api = useApi();
  return useMutation({
    mutationFn: (data: DocumentRequestCreate) =>
      api.requestDocument(firmId, matterId, data),
  });
}

export function useExtractData(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (docId: string) => api.extractData(firmId, matterId, docId),
    onSuccess: (_, docId) => {
      qc.invalidateQueries({ queryKey: queryKeys.document(firmId, matterId, docId) });
      qc.invalidateQueries({ queryKey: queryKeys.documents(firmId, matterId) });
    },
  });
}

export function useDraftLetter(firmId: string, matterId: string) {
  const api = useApi();
  return useMutation({
    mutationFn: (data: { asset_id: string; letter_type: string }) =>
      api.draftLetter(firmId, matterId, data),
  });
}

export function useSuggestTasks(firmId: string, matterId: string) {
  const api = useApi();
  return useMutation({
    mutationFn: () => api.suggestTasks(firmId, matterId),
  });
}

export function useDetectAnomalies(firmId: string, matterId: string) {
  const api = useApi();
  return useMutation({
    mutationFn: () => api.detectAnomalies(firmId, matterId),
  });
}

export function useAIUsageStats(firmId: string, matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: ["firms", firmId, "matters", matterId, "ai-usage-stats"] as const,
    queryFn: () => api.getAIUsageStats(firmId, matterId),
    staleTime: 60_000, // Cache for 1 minute
    enabled: !!firmId && !!matterId,
  });
}

// ─── Distributions ──────────────────────────────────────────────────────────

export function useDistributions(firmId: string, matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.distributions(firmId, matterId),
    queryFn: () => api.getDistributions(firmId, matterId),
    enabled: !!firmId && !!matterId,
  });
}

export function useDistributionSummary(firmId: string, matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.distributionSummary(firmId, matterId),
    queryFn: () => api.getDistributionSummary(firmId, matterId),
    enabled: !!firmId && !!matterId,
  });
}

export function useRecordDistribution(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DistributionCreate) =>
      api.recordDistribution(firmId, matterId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.distributions(firmId, matterId) });
      qc.invalidateQueries({ queryKey: queryKeys.distributionSummary(firmId, matterId) });
      qc.invalidateQueries({ queryKey: queryKeys.matterDashboard(firmId, matterId) });
      qc.invalidateQueries({ queryKey: queryKeys.communications(firmId, matterId) });
    },
  });
}

export function useAcknowledgeDistribution(firmId: string, matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (distId: string) =>
      api.acknowledgeDistribution(firmId, matterId, distId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.distributions(firmId, matterId) });
      qc.invalidateQueries({ queryKey: queryKeys.distributionSummary(firmId, matterId) });
    },
  });
}
