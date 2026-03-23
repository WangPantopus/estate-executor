import { type APIRequestContext } from '@playwright/test';

const API_BASE = process.env.E2E_API_URL ?? 'http://localhost:8000/api/v1';

interface SeedOptions {
  token: string;
}

/**
 * Helper to make authenticated API requests for test setup/teardown.
 */
async function apiRequest(
  request: APIRequestContext,
  method: string,
  path: string,
  token: string,
  body?: unknown,
) {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  const response = await request[method as 'get' | 'post' | 'patch' | 'delete'](url, {
    headers,
    data: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok()) {
    const text = await response.text().catch(() => '');
    throw new Error(`API ${method.toUpperCase()} ${path} failed (${response.status()}): ${text}`);
  }

  if (response.status() === 204) return undefined;
  return response.json();
}

/**
 * Seed a complete test firm with a matter, tasks, assets, and stakeholders.
 */
export async function seedTestData(
  request: APIRequestContext,
  opts: SeedOptions,
) {
  const { token } = opts;

  // Create firm
  const firm = await apiRequest(request, 'post', '/firms', token, {
    name: `E2E Test Firm ${Date.now()}`,
    type: 'law_firm',
  });

  const firmId = firm.id;

  // Create matter
  const matter = await apiRequest(
    request,
    'post',
    `/firms/${firmId}/matters`,
    token,
    {
      title: `Estate of E2E Decedent ${Date.now()}`,
      estate_type: 'testate_probate',
      jurisdiction_state: 'CA',
      decedent_name: 'John E2E Smith',
      date_of_death: '2024-01-15',
      estimated_value: 2500000,
      asset_types_present: ['real_estate', 'bank_account', 'brokerage_account'],
    },
  );

  const matterId = matter.id;

  // Generate tasks from template
  let tasks: { data: Array<{ id: string; title: string }> } | undefined;
  try {
    tasks = await apiRequest(
      request,
      'post',
      `/firms/${firmId}/matters/${matterId}/tasks/generate`,
      token,
      {},
    );
  } catch {
    // Task generation may not be available — create a manual task
  }

  // Create a manual task
  const manualTask = await apiRequest(
    request,
    'post',
    `/firms/${firmId}/matters/${matterId}/tasks`,
    token,
    {
      title: 'E2E Manual Task',
      description: 'A task created for end-to-end testing',
      phase: 'immediate',
      priority: 'normal',
      due_date: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
    },
  );

  // Create an asset
  const asset = await apiRequest(
    request,
    'post',
    `/firms/${firmId}/matters/${matterId}/assets`,
    token,
    {
      asset_type: 'bank_account',
      title: 'E2E Chase Checking',
      institution: 'Chase Bank',
      ownership_type: 'individual',
      transfer_mechanism: 'probate',
      current_estimated_value: 150000,
    },
  );

  // Create a deadline
  const deadline = await apiRequest(
    request,
    'post',
    `/firms/${firmId}/matters/${matterId}/deadlines`,
    token,
    {
      title: 'E2E Filing Deadline',
      description: 'Court filing deadline for testing',
      due_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
    },
  );

  // Create an overdue deadline (past due)
  const overdueDeadline = await apiRequest(
    request,
    'post',
    `/firms/${firmId}/matters/${matterId}/deadlines`,
    token,
    {
      title: 'E2E Overdue Deadline',
      description: 'An overdue deadline for testing',
      due_date: new Date(Date.now() - 5 * 86400000).toISOString().slice(0, 10),
    },
  );

  return {
    firmId,
    matterId,
    tasks: tasks?.data ?? [],
    manualTask,
    asset,
    deadline,
    overdueDeadline,
  };
}

/**
 * Invite a stakeholder and return the invite data.
 */
export async function inviteStakeholder(
  request: APIRequestContext,
  firmId: string,
  matterId: string,
  token: string,
  data: { email: string; full_name: string; role: string; relationship?: string },
) {
  return apiRequest(
    request,
    'post',
    `/firms/${firmId}/matters/${matterId}/stakeholders`,
    token,
    data,
  );
}

export { apiRequest };
