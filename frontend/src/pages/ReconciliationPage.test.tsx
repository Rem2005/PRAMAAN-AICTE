import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ReconciliationPage } from "./ReconciliationPage";
import type { SessionUser } from "../lib/api";

const OPERATOR: SessionUser = {
  authenticated: true,
  username: "operator1",
  institution_id: 1,
  institution_name: "Test Institution",
  roles: ["INSTITUTION_DATA_OPERATOR"],
};

const AUDITOR: SessionUser = { ...OPERATOR, roles: ["AUDITOR"] };

const BATCHES = {
  batches: [
    {
      batch_id: 42,
      state: "SUBMITTED_FOR_REVIEW",
      academic_year: "2026-2027",
      source_filename: "roster-batch-42.csv",
      uploader_ref: "operator1",
      created_at: "2026-10-25T10:00:00",
      total_rows: 3,
      valid_rows: 3,
      invalid_rows: 0,
    },
    {
      batch_id: 41,
      state: "VALIDATION_FAILED",
      academic_year: "2026-2027",
      source_filename: "roster-batch-41.csv",
      uploader_ref: "operator1",
      created_at: "2026-10-24T10:00:00",
      total_rows: 2,
      valid_rows: 1,
      invalid_rows: 1,
    },
  ],
  totals: { batches: 2, total_rows: 5, valid_rows: 4, invalid_rows: 1 },
};

const SNAPSHOTS = {
  snapshots: [
    {
      snapshot_id: 1,
      version: 1,
      status: "APPROVED",
      source_ref: "SYNTHETIC-DEMO-SNAPSHOT-2026-2027",
      created_at: "2026-10-25T09:00:00",
      approved_at: "2026-10-25T09:00:00",
      approved_by: "seed-demo (synthetic)",
      entry_count: 15,
    },
  ],
};

const POLICIES = {
  policies: [
    {
      policy_id: 1,
      version: 1,
      name: "Synthetic demo policy v1",
      description: null,
      status: "ACTIVE",
      rules: { link_fields: ["course_code", "academic_year", "seat_category"] },
      rules_checksum: "abc",
      created_at: "2026-10-25T09:00:00",
      activated_at: "2026-10-25T09:00:00",
    },
  ],
};

const RUNS = {
  runs: [
    {
      run_id: 3,
      batch_id: 42,
      run_number: 1,
      snapshot_id: 1,
      snapshot_version: 1,
      policy_id: 1,
      policy_version: 1,
      status: "SUCCEEDED",
      started_at: "2026-10-25T11:00:00",
      finished_at: "2026-10-25T11:00:00",
      triggered_by: "operator1",
      row_count: 3,
      digest: "a".repeat(64),
      totals: "Underfilled: 3; Matched: 2; Exceeded: 0",
      error_code: null,
      outcome_counts: { MATCHED: 2, UNMATCHED: 1 },
      source_filename: "roster-batch-42.csv",
      academic_year: "2026-2027",
      batch_state: "SUBMITTED_FOR_REVIEW",
    },
  ],
};

const RUN_DETAIL = {
  ...RUNS.runs[0],
  run_id: 4,
  run_number: 2,
  outcomes: [
    { row_number: 2, local_ref: "SYN-00001", outcome: "MATCHED", reasons: [] },
    { row_number: 3, local_ref: "SYN-00002", outcome: "MATCHED", reasons: [] },
    {
      row_number: 4,
      local_ref: "SYN-00003",
      outcome: "UNMATCHED",
      reasons: ["no approved entry for course_code=EE-UG-FT-S1"],
    },
  ],
};

function response(body: unknown, ok = true, status = 200): Response {
  return { ok, status, json: async () => body } as Response;
}

function stubApi(handlers: Partial<Record<string, () => Response>> = {}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    for (const [needle, handler] of Object.entries(handlers)) {
      if (url.includes(needle)) return handler!();
    }
    if (url.includes("/reconcile")) {
      return response(RUN_DETAIL);
    }
    if (url.includes("/api/v1/reconciliation/runs")) {
      return response(RUNS);
    }
    if (url.includes("/api/v1/reconciliation/snapshots")) {
      return response(SNAPSHOTS);
    }
    if (url.includes("/api/v1/reconciliation/policies")) {
      return response(POLICIES);
    }
    if (url.includes("/api/v1/batches")) {
      return response(BATCHES);
    }
    throw new Error(`Unexpected request: ${url} ${init?.method ?? "GET"}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function renderPage(session: SessionUser = OPERATOR) {
  render(<ReconciliationPage session={session} />);
  await screen.findByRole("heading", { name: /reconciliation/i, level: 1 });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("ReconciliationPage", () => {
  it("offers only reconcilable batches with real snapshots and policies", async () => {
    stubApi();
    await renderPage();

    await waitFor(() =>
      expect(screen.getByLabelText(/^Batch$/)).toBeTruthy(),
    );

    const batchSelect = screen.getByLabelText(/^Batch$/) as HTMLSelectElement;
    const optionLabels = [...batchSelect.options].map((option) => option.textContent);
    expect(optionLabels).toHaveLength(1);
    expect(optionLabels[0]).toContain("#42");
    expect(optionLabels[0]).toContain("roster-batch-42.csv");

    const snapshotSelect = screen.getByLabelText(
      /approved intake snapshot/i,
    ) as HTMLSelectElement;
    expect([...snapshotSelect.options].map((option) => option.textContent)).toEqual([
      "v1 · APPROVED · 15 lines",
    ]);

    const policySelect = screen.getByLabelText(
      /policy package/i,
    ) as HTMLSelectElement;
    expect([...policySelect.options].map((option) => option.textContent)).toEqual([
      "v1 · Synthetic demo policy v1 · ACTIVE",
    ]);

    expect(
      (screen.getByRole("button", { name: /run reconciliation/i }) as HTMLButtonElement)
        .disabled,
    ).toBe(false);
  });

  it("runs reconciliation and renders the persisted outcomes", async () => {
    const fetchMock = stubApi();
    await renderPage();
    await screen.findByLabelText(/^Batch$/);

    fireEvent.click(screen.getByRole("button", { name: /run reconciliation/i }));

    expect(
      await screen.findByRole("heading", { name: /run 2 summary/i }),
    ).toBeTruthy();

    const runCall = fetchMock.mock.calls.find(([url]) =>
      String(url).includes("/reconcile"),
    );
    expect(runCall).toBeTruthy();
    const runUrl = String(runCall![0]);
    expect(runUrl).toContain("/api/v1/batches/42/reconcile");
    expect(runUrl).toContain("snapshot_id=1");
    expect(runUrl).toContain("policy_id=1");
    expect((runCall![1] as RequestInit).method).toBe("POST");

    // The outcomes table is built from the server's row-level results.
    const outcomesSection = screen
      .getByRole("heading", { name: /row-level outcomes/i })
      .closest("section") as HTMLElement;
    expect(
      within(outcomesSection).getAllByText("No approved entry").length,
    ).toBeGreaterThan(0);
    expect(
      within(outcomesSection).getByText(
        "no approved entry for course_code=EE-UG-FT-S1",
      ),
    ).toBeTruthy();
    expect(within(outcomesSection).getByText("SYN-00003")).toBeTruthy();
    expect(screen.getByText("a".repeat(64))).toBeTruthy();
  });

  it("explains the missing references instead of offering a run", async () => {
    stubApi({
      "/api/v1/reconciliation/snapshots": () => response({ snapshots: [] }),
      "/api/v1/reconciliation/policies": () => response({ policies: [] }),
    });
    await renderPage();

    expect(await screen.findByText(/reference data is missing/i)).toBeTruthy();
    expect(screen.getByText(/python -m app\.cli seed-demo/i)).toBeTruthy();

    const runButton = screen.getByRole("button", {
      name: /run reconciliation/i,
    }) as HTMLButtonElement;
    expect(runButton.disabled).toBe(true);
    expect(runButton.getAttribute("title")).toMatch(/no approved intake snapshot/i);
  });

  it("keeps reconciliation read-only for a role that cannot run it", async () => {
    stubApi();
    await renderPage(AUDITOR);
    await screen.findByLabelText(/^Batch$/);

    const runButton = screen.getByRole("button", {
      name: /run reconciliation/i,
    }) as HTMLButtonElement;
    expect(runButton.disabled).toBe(true);
    expect(runButton.getAttribute("title")).toMatch(/nodal officer/i);
    expect(screen.getByText(/your role can view runs but not start one/i)).toBeTruthy();

    // History is still readable.
    expect(await screen.findByRole("table")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /^view$/i })).not.toBeNull();
  });

  it("shows the server's error when a run is refused, and retries", async () => {
    let attempts = 0;
    stubApi({
      "/api/v1/batches/42/reconcile": () => {
        attempts += 1;
        return attempts === 1
          ? response(
              { detail: "No active reconciliation policy is available." },
              false,
              400,
            )
          : response(RUN_DETAIL);
      },
    });
    await renderPage();
    await screen.findByLabelText(/^Batch$/);

    fireEvent.click(screen.getByRole("button", { name: /run reconciliation/i }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/no active reconciliation policy/i);

    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(
      await screen.findByRole("heading", { name: /run 2 summary/i }),
    ).toBeTruthy();
  });

  it("reports a failure to load references and retries", async () => {
    let failed = false;
    stubApi({
      "/api/v1/batches": () => {
        if (!failed) {
          failed = true;
          return response({ detail: "The batches endpoint is unavailable." }, false, 500);
        }
        return response(BATCHES);
      },
    });
    await renderPage();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/batches endpoint is unavailable/i);

    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
    expect(screen.getByLabelText(/^Batch$/)).toBeTruthy();
  });
});
