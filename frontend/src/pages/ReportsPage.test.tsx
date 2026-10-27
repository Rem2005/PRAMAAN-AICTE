import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ReportsPage } from "./ReportsPage";

const RUNS = {
  runs: [
    {
      run_id: 3,
      batch_id: 42,
      run_number: 2,
      snapshot_id: 1,
      snapshot_version: 1,
      policy_id: 1,
      policy_version: 2,
      status: "SUCCEEDED",
      started_at: "2026-10-25T11:00:00",
      finished_at: "2026-10-25T11:00:00",
      triggered_by: "operator1",
      row_count: 3,
      digest: "b".repeat(64),
      totals: "Underfilled: 3; Matched: 2; Exceeded: 0",
      error_code: null,
      outcome_counts: { MATCHED: 2, UNMATCHED: 1 },
      source_filename: "roster-batch-42.csv",
      academic_year: "2026-2027",
      batch_state: "SUBMITTED_FOR_REVIEW",
    },
    {
      run_id: 2,
      batch_id: 41,
      run_number: 1,
      snapshot_id: 1,
      snapshot_version: 1,
      policy_id: 1,
      policy_version: 1,
      status: "SUCCEEDED",
      started_at: "2026-10-24T09:30:00",
      finished_at: "2026-10-24T09:30:00",
      triggered_by: "operator1",
      row_count: 2,
      digest: "c".repeat(64),
      totals: "Underfilled: 2; Matched: 0; Exceeded: 0",
      error_code: null,
      outcome_counts: { UNMATCHED: 2 },
      source_filename: "roster-batch-41.csv",
      academic_year: "2026-2027",
      batch_state: "VALIDATED",
    },
  ],
};

const DETAIL = {
  ...RUNS.runs[0],
  outcomes: [
    { row_number: 2, local_ref: "SYN-00001", outcome: "MATCHED", reasons: [] },
    {
      row_number: 3,
      local_ref: "SYN-00002",
      outcome: "UNMATCHED",
      reasons: ["no approved entry for course_code=EE-UG-FT-S1"],
    },
  ],
};

function response(body: unknown, ok = true, status = 200): Response {
  return { ok, status, json: async () => body } as Response;
}

function stubApi(runs: unknown = RUNS) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (/\/api\/v1\/reconciliation\/runs\/\d+/.test(url)) {
      return response(DETAIL);
    }
    if (url.includes("/api/v1/reconciliation/runs")) {
      return response(runs);
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

let downloadSpy: ReturnType<typeof vi.fn>;
let createdBlobs: Blob[];

/** jsdom's Blob has no .text(); FileReader is available. */
function blobText(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}

beforeEach(() => {
  createdBlobs = [];
  downloadSpy = vi.fn();
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(downloadSpy);
  vi.stubGlobal("URL", {
    ...URL,
    createObjectURL: (blob: Blob) => {
      createdBlobs.push(blob);
      return "blob:pramaan-test";
    },
    revokeObjectURL: () => undefined,
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ReportsPage", () => {
  it("lists recorded runs with their versions and real counts", async () => {
    stubApi();
    render(<ReportsPage />);

    await screen.findByRole("heading", { name: /reconciliation runs/i });

    expect(screen.getByText("roster-batch-42.csv")).toBeTruthy();
    expect(screen.getByText("snapshot v1 · policy v2")).toBeTruthy();
    expect(screen.getByText("Recorded runs")).toBeTruthy();
    // Two batches appear in the summary hint.
    expect(screen.getByText("Across 2 batches")).toBeTruthy();
  });

  it("filters runs by search text", async () => {
    stubApi();
    render(<ReportsPage />);
    await screen.findByText("roster-batch-42.csv");

    fireEvent.change(screen.getByLabelText(/search runs/i), {
      target: { value: "batch-41" },
    });

    expect(screen.queryByText("roster-batch-42.csv")).toBeNull();
    expect(screen.getByText("roster-batch-41.csv")).toBeTruthy();
  });

  it("shows an explicit empty state when nothing has been reconciled", async () => {
    stubApi({ runs: [] });
    render(<ReportsPage />);

    expect(await screen.findByText(/no reconciliation has been recorded yet/i)).toBeTruthy();
    const exportButton = screen.getByRole("button", {
      name: /export run summary/i,
    }) as HTMLButtonElement;
    expect(exportButton.disabled).toBe(true);
  });

  it("reports a load failure and retries", async () => {
    let failed = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/reconciliation/runs")) {
        if (!failed) {
          failed = true;
          return response({ detail: "Reports service unavailable." }, false, 503);
        }
        return response(RUNS);
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReportsPage />);
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/reports service unavailable/i);

    fireEvent.click(within(alert).getByRole("button", { name: /try again/i }));
    expect(await screen.findByText("roster-batch-42.csv")).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("exports the filtered run summary as CSV", async () => {
    stubApi();
    render(<ReportsPage />);
    await screen.findByText("roster-batch-42.csv");

    fireEvent.click(screen.getByRole("button", { name: /export run summary/i }));

    await waitFor(() => expect(createdBlobs).toHaveLength(1));
    const text = await blobText(createdBlobs[0]);
    const lines = text.trim().split("\n");
    expect(lines[0]).toContain("run_id,batch_id,source_filename");
    expect(lines).toHaveLength(3);
    expect(text).toContain("roster-batch-42.csv");
    expect(text).toContain("b".repeat(64));
    expect(downloadSpy).toHaveBeenCalled();
  });

  it("exports one run's row-level outcomes from the API", async () => {
    const fetchMock = stubApi();
    render(<ReportsPage />);
    await screen.findByText("roster-batch-42.csv");

    const buttons = screen.getAllByRole("button", { name: /outcomes csv/i });
    fireEvent.click(buttons[0]);

    await waitFor(() => expect(createdBlobs).toHaveLength(1));
    const text = await blobText(createdBlobs[0]);
    expect(text.split("\n")[0]).toBe("row_number,local_ref,outcome,reasons");
    expect(text).toContain("No approved entry");
    expect(text).toContain("no approved entry for course_code=EE-UG-FT-S1");
    expect(
      fetchMock.mock.calls.some(([url]) =>
        /\/api\/v1\/reconciliation\/runs\/3$/.test(String(url)),
      ),
    ).toBe(true);
  });
});
