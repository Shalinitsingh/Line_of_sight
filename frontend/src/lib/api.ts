// Typed client for the Line-of-Sight FastAPI backend.
// Reads the JWT from localStorage and attaches it to every protected call.

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Industry = "corporate" | "hospital";

function token(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("los_token");
}

async function request<T>(
  path: string,
  opts: { method?: string; body?: unknown; auth?: boolean; form?: FormData } = {}
): Promise<T> {
  const headers: Record<string, string> = {};
  const init: RequestInit = { method: opts.method || "GET", headers };

  if (opts.form) {
    init.body = opts.form; // browser sets multipart boundary
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(opts.body);
  }
  if (opts.auth) {
    const t = token();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }

  const res = await fetch(`${BASE}${path}`, init);
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = data?.detail || res.statusText;
    throw new ApiError(
      typeof detail === "string" ? detail : "Request failed",
      res.status
    );
  }
  return data as T;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

// ----- Auth -----
export interface AuthResult {
  token: string;
  org_id?: string;
  role?: string;
  industry?: Industry;
  full_name?: string | null;
}

export const api = {
  signup: (b: {
    full_name?: string;
    email: string;
    password: string;
    industry: Industry;
  }) => request<AuthResult>("/auth/signup", { method: "POST", body: b }),

  login: (b: { email: string; password: string }) =>
    request<AuthResult>("/auth/login", { method: "POST", body: b }),

  sendCode: (b: { email: string; purpose: "email_verify" | "password_reset" }) =>
    request<{ sent: boolean; expires_in_minutes: number; dev_code?: string }>(
      "/auth/send-code",
      { method: "POST", body: b }
    ),

  verifyCode: (b: {
    email: string;
    code: string;
    purpose: "email_verify" | "password_reset";
  }) =>
    request<{ verified: boolean }>("/auth/verify-code", { method: "POST", body: b }),

  resetPassword: (b: { email: string; code: string; new_password: string }) =>
    request<{ reset: boolean }>("/auth/reset-password", { method: "POST", body: b }),

  // ----- Datasets -----
  listDatasets: () =>
    request<Array<{ id: string; name: string; status: string; row_count: number }>>(
      "/datasets",
      { auth: true }
    ),

  uploadDataset: (file: File, name: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("name", name);
    return request<{
      dataset_id: string;
      rows: number;
      columns: Array<{ key: string; header: string; type: string; numeric: boolean }>;
    }>("/datasets", { method: "POST", form, auth: true });
  },

  datasetColumns: (id: string) =>
    request<
      Array<{
        id: string;
        original_header: string;
        normalized_key: string;
        data_type: string;
        is_numeric: boolean;
      }>
    >(`/datasets/${id}/columns`, { auth: true }),

  // ----- Metrics / formulas (AI tracker) -----
  createMetric: (b: { name: string; unit?: string; default_viz?: string }) =>
    request<{ metric_id: string }>("/metrics", { method: "POST", body: b, auth: true }),

  proposeFormula: (metricId: string, b: { goal: string; dataset_id: string }) =>
    request<{
      formula_id: string;
      expression: string;
      variables: string[];
      rationale?: string;
      status: string;
    }>(`/metrics/${metricId}/propose`, { method: "POST", body: b, auth: true }),

  validateFormula: (formulaId: string) =>
    request<{ status: string }>(`/formulas/${formulaId}/validate`, {
      method: "POST",
      auth: true,
    }),

  executeFormula: (formulaId: string) =>
    request<{ expression: string; result: number | unknown }>(
      `/formulas/${formulaId}/execute`,
      { method: "POST", auth: true }
    ),

  // ----- Reports / audit -----
  listReports: () =>
    request<Array<{ id: string; title: string; created_at: string }>>("/reports", {
      auth: true,
    }),

  createReport: (b: { title: string; payload?: unknown }) =>
    request<{ report_id: string }>("/reports", { method: "POST", body: b, auth: true }),

  audit: () =>
    request<Array<{ action: string; created_at: string; target_type?: string }>>(
      "/audit",
      { auth: true }
    ),
};
