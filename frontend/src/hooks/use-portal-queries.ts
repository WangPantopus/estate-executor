"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { useApi } from "./use-api";
import type { PortalMessageCreate } from "@/lib/types";

export const portalKeys = {
  matters: ["portal", "matters"] as const,
  overview: (matterId: string) => ["portal", matterId, "overview"] as const,
  documents: (matterId: string) => ["portal", matterId, "documents"] as const,
  messages: (matterId: string) => ["portal", matterId, "messages"] as const,
};

export function usePortalMatters() {
  const api = useApi();
  return useQuery({
    queryKey: portalKeys.matters,
    queryFn: () => api.getPortalMatters(),
  });
}

export function usePortalOverview(matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: portalKeys.overview(matterId),
    queryFn: () => api.getPortalOverview(matterId),
    enabled: !!matterId,
  });
}

export function usePortalDocuments(matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: portalKeys.documents(matterId),
    queryFn: () => api.getPortalDocuments(matterId),
    enabled: !!matterId,
  });
}

export function usePortalMessages(matterId: string) {
  const api = useApi();
  return useQuery({
    queryKey: portalKeys.messages(matterId),
    queryFn: () => api.getPortalMessages(matterId),
    enabled: !!matterId,
  });
}

export function usePostPortalMessage(matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: PortalMessageCreate) =>
      api.postPortalMessage(matterId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: portalKeys.messages(matterId) });
    },
  });
}

export function useAcknowledgeNotice(matterId: string) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (commId: string) =>
      api.acknowledgePortalNotice(matterId, commId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: portalKeys.messages(matterId) });
      qc.invalidateQueries({ queryKey: portalKeys.overview(matterId) });
    },
  });
}
