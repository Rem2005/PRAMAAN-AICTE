/** API client for PRAMAAN-AICTE frontend.
 *
 * All requests carry credentials because the session lives in an HttpOnly
 * cookie the browser can neither read nor set. In development the Vite proxy
 * makes `/api` and `/health` same-origin, so the cookie is first-party; set
 * `VITE_API_BASE_URL` to point elsewhere.
 */

export type HealthResult = { status: "ok" } | { status: "error" };

export type SessionUser = {
  authenticated: boolean;
  username: string;
  institution_id: number;
  institution_name: string;
  roles: string[];
};

export const ANONYMOUS_SESSION: SessionUser = {
  authenticated: false,
  username: "",
  institution_id: 0,
  institution_name: "",
  roles: [],
};

/** Read the current session. Never throws: an unreadable session means signed out. */
export async function fetchSession(): Promise<SessionUser> {
  try {
    const response = await fetch(`${apiBase()}/api/v1/auth/me`, {
      credentials: "include",
    });
    if (!response.ok) return ANONYMOUS_SESSION;
    return (await response.json()) as SessionUser;
  } catch {
    return ANONYMOUS_SESSION;
  }
}

export async function login(
  username: string,
  password: string,
): Promise<SessionUser> {
  const response = await fetch(`${apiBase()}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Sign-in failed" }));
    throw new Error(error.detail || `Sign-in failed (${response.status})`);
  }
  return response.json();
}

export async function logout(): Promise<void> {
  await fetch(`${apiBase()}/api/v1/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export async function checkHealth(
  baseUrl: string = apiBase(),
): Promise<HealthResult> {
  try {
    const response = await fetch(`${baseUrl}/health`, { credentials: "include" });
    if (!response.ok) {
      return { status: "error" };
    }
    return { status: "ok" };
  } catch {
    return { status: "error" };
  }
}

// ---- Institution batch list (dashboard) ----

export type RosterBatchSummary = {
  batch_id: number;
  state: string;
  academic_year: string;
  /** NULL until a roster file has been uploaded for this batch. */
  source_filename: string | null;
  uploader_ref: string;
  created_at: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
};

export type RosterBatchListTotals = {
  batches: number;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
};

export type RosterBatchList = {
  batches: RosterBatchSummary[];
  totals: RosterBatchListTotals;
};

/**
 * Batches for the signed-in institution, newest first. The institution is
 * taken from the session server-side; there is no parameter to widen it.
 */
export async function fetchRosterBatches(): Promise<RosterBatchList> {
  const response = await request("/api/v1/batches");
  if (!response.ok) {
    throw await apiError(response, "The batch list could not be loaded");
  }
  const body = (await response.json()) as RosterBatchList;
  // Refuse an unexpected payload rather than rendering placeholder numbers.
  if (!Array.isArray(body?.batches) || !body?.totals) {
    throw new Error("Unexpected response from the batches endpoint.");
  }
  return body;
}

// ---- Reconciliation API ----

export type SnapshotInfo = {
  snapshot_id: number;
  version: number;
  status: string;
  source_ref: string;
  created_at: string;
  approved_at: string | null;
  approved_by: string | null;
  entry_count: number;
};

export type PolicyInfo = {
  policy_id: number;
  version: number;
  name: string;
  description: string | null;
  status: string;
  rules: Record<string, unknown>;
  rules_checksum: string;
  created_at: string;
  activated_at: string | null;
};

export type ReconciliationOutcome = {
  row_number: number;
  local_ref: string | null;
  outcome: string;
  reasons: string[];
};

export type ReconciliationRun = {
  run_id: number;
  batch_id: number;
  run_number: number;
  snapshot_id: number;
  snapshot_version: number;
  policy_id: number;
  policy_version: number;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  triggered_by: string;
  row_count: number;
  digest: string | null;
  totals: string | null;
  error_code: string | null;
  outcome_counts: Record<string, number>;
  source_filename: string | null;
  academic_year: string | null;
  batch_state: string | null;
};

export type ReconciliationRunDetail = ReconciliationRun & {
  outcomes: ReconciliationOutcome[];
};

export async function fetchSnapshots(): Promise<SnapshotInfo[]> {
  const response = await fetch(`${apiBase()}/api/v1/reconciliation/snapshots`, {
    credentials: "include",
  });
  if (!response.ok) throw await apiError(response, "Could not load intake snapshots");
  const body = (await response.json()) as { snapshots?: SnapshotInfo[] };
  if (!Array.isArray(body.snapshots)) {
    throw new Error("Unexpected response from the snapshots endpoint.");
  }
  return body.snapshots;
}

export async function fetchPolicies(): Promise<PolicyInfo[]> {
  const response = await fetch(`${apiBase()}/api/v1/reconciliation/policies`, {
    credentials: "include",
  });
  if (!response.ok) throw await apiError(response, "Could not load policy packages");
  const body = (await response.json()) as { policies?: PolicyInfo[] };
  if (!Array.isArray(body.policies)) {
    throw new Error("Unexpected response from the policies endpoint.");
  }
  return body.policies;
}

export async function runReconciliation(
  batchId: number,
  options: { snapshotId?: number; policyId?: number } = {},
): Promise<ReconciliationRunDetail> {
  const params = new URLSearchParams();
  if (options.snapshotId !== undefined) {
    params.set("snapshot_id", String(options.snapshotId));
  }
  if (options.policyId !== undefined) {
    params.set("policy_id", String(options.policyId));
  }
  const query = params.toString();
  const response = await fetch(
    `${apiBase()}/api/v1/batches/${batchId}/reconcile${query ? `?${query}` : ""}`,
    { method: "POST", credentials: "include" },
  );
  if (!response.ok) throw await apiError(response, "Reconciliation failed");
  return response.json();
}

export async function fetchReconciliationRuns(
  batchId?: number,
): Promise<ReconciliationRun[]> {
  const query = batchId !== undefined ? `?batch_id=${batchId}` : "";
  const response = await fetch(
    `${apiBase()}/api/v1/reconciliation/runs${query}`,
    { credentials: "include" },
  );
  if (!response.ok) throw await apiError(response, "Could not load reconciliation history");
  const body = (await response.json()) as { runs?: ReconciliationRun[] };
  if (!Array.isArray(body.runs)) {
    throw new Error("Unexpected response from the reconciliation runs endpoint.");
  }
  return body.runs;
}

export async function fetchReconciliationRun(
  runId: number,
): Promise<ReconciliationRunDetail> {
  const response = await fetch(
    `${apiBase()}/api/v1/reconciliation/runs/${runId}`,
    { credentials: "include" },
  );
  if (!response.ok) throw await apiError(response, "Could not load the reconciliation run");
  return response.json();
}

// ---- Roster intake API ----

export type BatchRowResult = {
  row_number: number;
  local_ref: string | null;
  valid: boolean;
  errors: string[];
};

export type BatchValidateResponse = {
  batch_id: number;
  state: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  rows: BatchRowResult[];
};

export type BatchConfirmResponse = {
  batch_id: number;
  state: string;
  persisted_count: number;
};

export type BatchCreateResponse = {
  batch_id: number;
  state: string;
  idempotency_key: string;
  created_at: string;
};

const apiBase = () => (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

/**
 * fetch() with an actionable message for a network-level failure.
 *
 * A refused connection used to surface as "Failed to fetch", which told the
 * operator nothing about the likely cause. The message stands on its own,
 * because callers show it verbatim.
 */
async function request(path: string, init: RequestInit = {}): Promise<Response> {
  try {
    return await fetch(`${apiBase()}${path}`, {
      credentials: "include",
      ...init,
    });
  } catch {
    throw new Error(
      "The server did not respond. Check that the backend is running, then try again.",
    );
  }
}

/**
 * Turn a failed response into an Error whose message is the server's own
 * explanation. Errors are never swallowed: the caller shows them.
 */

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response
    .json()
    .catch(() => null as { detail?: string } | null);
  const detail =
    typeof body?.detail === "string" && body.detail.trim()
      ? body.detail
      : `${fallback} (HTTP ${response.status}).`;
  const error = new Error(detail) as Error & { status?: number };
  error.status = response.status;
  return error;
}

export type BatchCreatePayload = {
  institution_id: number;
  academic_year: string;
  schema_version: string;
  /** Optional pre-declared SHA-256. The server always recomputes it from the
   * uploaded bytes, so the client does not need to send one. */
  checksum?: string;
  /** Optional client key so a retried create returns the original batch. */
  idempotency_key?: string;
};

export async function createIntakeBatch(
  payload: BatchCreatePayload,
): Promise<BatchCreateResponse> {
  const response = await fetch(`${apiBase()}/api/v1/batches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `Batch creation failed (${response.status})`);
  }
  return response.json();
}

export async function validateIntakeBatch(
  batchId: number,
  file: File,
): Promise<BatchValidateResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${apiBase()}/api/v1/batches/${batchId}/validate`, {
    method: "POST",
    body: formData,
    credentials: "include",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `Validation failed (${response.status})`);
  }
  return response.json();
}

export async function confirmIntakeBatch(
  batchId: number,
  idempotencyKey: string,
): Promise<BatchConfirmResponse> {
  const response = await fetch(
    `${apiBase()}/api/v1/batches/${batchId}/confirm`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ idempotency_key: idempotencyKey }),
    },
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `Confirmation failed (${response.status})`);
  }
  return response.json();
}

/** Auth context for pages that need role/identity info. */
export async function getAuthContext(): Promise<SessionUser & { cookie?: string; has_any_role?: Record<string, boolean> }> {
  const session = await fetchSession();
  const roles = session.roles || [];
  const has_any_role: Record<string, boolean> = {};
  for (const role of roles) {
    has_any_role[role] = true;
    // Also add some common role keys the UI might check
    if (role.includes("ADMIN")) has_any_role["_admin"] = true;
    if (role.includes("NODAL")) has_any_role["_nodal"] = true;
    if (role.includes("OPERATOR")) has_any_role["_operator"] = true;
    if (role.includes("IDENTITY")) has_any_role["_identity"] = true;
    if (role.includes("REVIEW")) has_any_role["_review"] = true;
  }
  // Also mark admin if user has NODAL or OPERATOR in some setups
  if (roles.includes("NODAL_OFFICER") || roles.includes("INSTITUTION_DATA_OPERATOR")) {
    has_any_role["_admin"] = true;
  }
  return { ...session, has_any_role };
}
