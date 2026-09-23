// Typed client for the real CloudWise API (cloudwise/apps/api). Every
// function here hits a live, tested backend route.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type AWSAccount = {
  id: string;
  aws_account_id: string;
  role_arn: string;
  label: string | null;
  status: "pending" | "connected" | "error";
  created_at: string;
};

export type Finding = {
  id: string;
  account_id: string;
  rule_id: string;
  resource_id: string;
  resource_type: string;
  monthly_savings: number;
  effort: "low" | "medium" | "high";
  risk: "low" | "medium" | "high";
  status: "open" | "approved" | "done" | "dismissed";
  evidence?: Record<string, unknown>;
};

export type SpendByGroup = { key: string; cost: number };

export type SpendSummary = {
  start_date: string;
  end_date: string;
  view: string;
  group_by: string;
  currency: string;
  total_cost: number;
  breakdown: SpendByGroup[];
};

export type ChangeRequest = {
  id: string;
  finding_id: string;
  action_type: string;
  status: "pending" | "approved" | "rejected" | "executed" | "failed";
  rollback_plan: string | null;
  execution_result: Record<string, unknown> | null;
  executed_at: string | null;
  created_at: string;
};

export type Entitlement = {
  tier: "free" | "starter" | "growth";
  status: string;
  max_accounts: number | null;
};

export type CopilotResponse = {
  text: string;
  tool_calls: string[];
  grounding_warnings: string[];
};

export type Me = {
  id: string;
  org_id: string;
  email: string;
  role: string;
};

export type AuditLogEntry = {
  id: string;
  actor_id: string | null;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type Budget = {
  id: string;
  account_id: string | null;
  name: string;
  monthly_limit_usd: number;
  spent_this_month: number;
};

export type Anomaly = {
  service: string;
  baseline_daily_avg: number;
  recent_daily_avg: number;
  delta_monthly: number;
  since: string;
};

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  token: string | null,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON; fall back to statusText
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  me: (token: string) => request<Me>("/auth/me", token),

  listAccounts: (token: string) => request<AWSAccount[]>("/accounts", token),
  createAccount: (
    token: string,
    payload: { aws_account_id: string; role_arn: string; external_id: string; label?: string }
  ) => request<AWSAccount>("/accounts", token, { method: "POST", body: JSON.stringify(payload) }),
  scanAccount: (token: string, accountId: string) =>
    request<{ resources_scanned: number; findings_written: number }>(
      `/accounts/${accountId}/scan`,
      token,
      { method: "POST" }
    ),

  listFindings: (token: string) => request<Finding[]>("/findings", token),

  getSpend: (
    token: string,
    params: { group_by?: string; view?: string; start_date?: string; end_date?: string } = {}
  ) => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return request<SpendSummary>(`/spend${query ? `?${query}` : ""}`, token);
  },

  listChangeRequests: (token: string) => request<ChangeRequest[]>("/change-requests", token),
  approveChangeRequest: (token: string, id: string) =>
    request<ChangeRequest>(`/change-requests/${id}/approve`, token, { method: "POST" }),
  executeChangeRequest: (token: string, id: string) =>
    request<ChangeRequest>(`/change-requests/${id}/execute`, token, { method: "POST" }),

  getEntitlement: (token: string) => request<Entitlement>("/billing/entitlement", token),
  createCheckout: (token: string, tier: "starter" | "growth", successUrl: string, cancelUrl: string) =>
    request<{ checkout_url: string }>("/billing/checkout", token, {
      method: "POST",
      body: JSON.stringify({ tier, success_url: successUrl, cancel_url: cancelUrl }),
    }),

  copilotChat: (token: string, message: string) =>
    request<CopilotResponse>("/copilot/chat", token, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),

  listAuditLog: (token: string) => request<AuditLogEntry[]>("/audit-log", token),

  listBudgets: (token: string) => request<Budget[]>("/budgets", token),
  createBudget: (token: string, payload: { name: string; monthly_limit_usd: number; account_id?: string }) =>
    request<Budget>("/budgets", token, { method: "POST", body: JSON.stringify(payload) }),

  listAnomalies: (token: string) => request<Anomaly[]>("/anomalies", token),

  // Demo endpoints need no auth token at all.
  demoAccounts: () => request<AWSAccount[]>("/demo/accounts", null),
  demoFindings: () => request<Finding[]>("/demo/findings", null),
  demoSpend: (params: { group_by?: string; view?: string } = {}) => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return request<SpendSummary>(`/demo/spend${query ? `?${query}` : ""}`, null);
  },
};

export { ApiError };
