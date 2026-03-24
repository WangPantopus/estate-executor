/**
 * Estate Executor OS — Mobile API Client
 *
 * Same pattern as the web frontend ApiClient, adapted for React Native.
 * Uses SecureStore for token persistence.
 */

import type {
  MatterDashboard,
  PaginatedResponse,
  Matter,
  Task,
  CommunicationResponse,
  UserProfile,
} from "./types";

// ─── Error classes ──────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function buildQueryString(params?: Record<string, unknown>): string {
  if (!params) return "";
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) {
      qs.set(k, String(v));
    }
  }
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export type GetAccessTokenFn = () => Promise<string | null>;

// ─── API Client ─────────────────────────────────────────────────────────────

export class ApiClient {
  private baseUrl: string;
  private getAccessToken: GetAccessTokenFn;

  constructor(opts: { baseUrl: string; getAccessToken: GetAccessTokenFn }) {
    this.baseUrl = opts.baseUrl;
    this.getAccessToken = opts.getAccessToken;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    const token = await this.getAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const url = `${this.baseUrl}${path}`;

    const res = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!res.ok) {
      let message = `Request failed with status ${res.status}`;
      try {
        const errorBody = await res.json();
        message = errorBody?.detail ?? message;
      } catch {
        // response body is not JSON
      }
      throw new ApiError(res.status, message);
    }

    if (res.status === 204) {
      return undefined as T;
    }

    return res.json() as Promise<T>;
  }

  private get<T>(path: string): Promise<T> {
    return this.request<T>("GET", path);
  }

  private post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("POST", path, body);
  }

  // ─── Auth ─────────────────────────────────────────────────────────────

  async getMe(): Promise<UserProfile> {
    return this.get("/auth/me");
  }

  // ─── Matters ──────────────────────────────────────────────────────────

  async getMatters(
    firmId: string,
    params?: { page?: number; per_page?: number; status?: string; search?: string },
  ): Promise<PaginatedResponse<Matter>> {
    return this.get(`/firms/${firmId}/matters${buildQueryString(params)}`);
  }

  async getMatterDashboard(firmId: string, matterId: string): Promise<MatterDashboard> {
    return this.get(`/firms/${firmId}/matters/${matterId}`);
  }

  // ─── Tasks ────────────────────────────────────────────────────────────

  async getTasks(
    firmId: string,
    matterId: string,
    params?: { page?: number; status?: string; assigned_to?: string },
  ): Promise<PaginatedResponse<Task>> {
    return this.get(
      `/firms/${firmId}/matters/${matterId}/tasks${buildQueryString(params)}`,
    );
  }

  async completeTask(
    firmId: string,
    matterId: string,
    taskId: string,
  ): Promise<Task> {
    return this.post(
      `/firms/${firmId}/matters/${matterId}/tasks/${taskId}/complete`,
      {},
    );
  }

  // ─── Communications ───────────────────────────────────────────────────

  async getCommunications(
    firmId: string,
    matterId: string,
    params?: { page?: number; type?: string },
  ): Promise<PaginatedResponse<CommunicationResponse>> {
    return this.get(
      `/firms/${firmId}/matters/${matterId}/communications${buildQueryString(params)}`,
    );
  }

  async createCommunication(
    firmId: string,
    matterId: string,
    data: { type: string; subject?: string; body: string },
  ): Promise<CommunicationResponse> {
    return this.post(
      `/firms/${firmId}/matters/${matterId}/communications`,
      data,
    );
  }
}
