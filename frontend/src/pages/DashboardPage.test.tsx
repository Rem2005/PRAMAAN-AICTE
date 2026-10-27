import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "./DashboardPage";
import type { RosterBatchList, SessionUser } from "../lib/api";

const OPERATOR: SessionUser = {
  authenticated: true,
  username: "operator1",
  institution_id: 1,
  institution_name: "Test Institution",
  roles: ["INSTITUTION_DATA_OPERATOR"],
};

const AUDITOR: SessionUser = { ...OPERATOR, roles: ["AUDITOR"] };

function makeBatch(overrides: Partial<RosterBatchList["batches"][number]> & { batch_id: number }) {
  return {
    state: "VALIDATED",
    academic_year: "2026-2027",
    source_filename: `roster-${overrides.batch_id}.csv`,
    uploader_ref: "operator1",
    created_at: "2026-10-24T10:42:00Z",
    total_rows: 10,
    valid_rows: 10,
    invalid_rows: 0,
    ...overrides,
  };
}

const BATCHES = [
  makeBatch({
    batch_id: 1,
    source_filename: "BTech_CSE_2026_Y1.csv",
    state: "VALIDATION_FAILED",
    total_rows: 10,
    valid_rows: 8,
    invalid_rows: 2,
  }),
  makeBatch({ batch_id: 2, source_filename: "BTech_ECE_2026_Y1.csv", total_rows: 480, valid_rows: 480 }),
  makeBatch({
    batch_id: 3,
    source_filename: "BTech_ME_2026_Y1.csv",
    state: "VALIDATING",
    total_rows: 120,
    valid_rows: 0,
  }),
  makeBatch({ batch_id: 4, source_filename: null, state: "CREATED", total_rows: 0, valid_rows: 0 }),
  makeBatch({
    batch_id: 5,
    source_filename: "MBA_2026_Y1.csv",
    state: "SUBMITTED_FOR_REVIEW",
    total_rows: 200,
    valid_rows: 200,
  }),
  makeBatch({ batch_id: 6, source_filename: "MCA_2026_Y1.csv", total_rows: 25, valid_rows: 25 }),
  makeBatch({
    batch_id: 7,
    source_filename: "BTech_CIVIL_2026_Y1.csv",
    state: "VALIDATION_FAILED",
    total_rows: 5,
    valid_rows: 0,
    invalid_rows: 3,
  }),
  makeBatch({ batch_id: 8, source_filename: "BTech_EEE_2026_Y1.csv", total_rows: 40, valid_rows: 40 }),
];

// Totals follow the same definition the API uses: sums over the listed batches.
const PAYLOAD: RosterBatchList = {
  batches: BATCHES,
  totals: {
    batches: BATCHES.length,
    total_rows: BATCHES.reduce((sum, b) => sum + b.total_rows, 0),
    valid_rows: BATCHES.reduce((sum, b) => sum + b.valid_rows, 0),
    invalid_rows: BATCHES.reduce((sum, b) => sum + b.invalid_rows, 0),
  },
};

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return { ok, status, json: async () => body } as Response;
}

function stubBatches(payload: RosterBatchList = PAYLOAD) {
  const fetchMock = vi.fn(async () => jsonResponse(payload));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function renderDashboard(session: SessionUser = OPERATOR) {
  render(<DashboardPage session={session} />);
  await screen.findByRole("heading", { name: /welcome back, operator1/i });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("DashboardPage", () => {
  it("shows counts computed from the API response", async () => {
    stubBatches();
    await renderDashboard();

    expect(await screen.findByText("753")).toBeTruthy(); // valid rows
    // VALIDATED plus SUBMITTED_FOR_REVIEW are both reconcilable.
    expect(screen.getByText("4 of 8")).toBeTruthy();
    expect(screen.getByText("Across 2 batches")).toBeTruthy(); // batches with row errors
  });

  it("labels synthetic data persistently", async () => {
    stubBatches();
    await renderDashboard();

    // Three summary cards plus the batches panel.
    expect(screen.getAllByText(/synthetic data/i).length).toBeGreaterThanOrEqual(4);
    expect(screen.getByText(/not an official government service/i)).toBeTruthy();
  });

  it("lists the newest six batches with filenames and IST timestamps", async () => {
    stubBatches();
    await renderDashboard();

    expect(await screen.findByText("BTech_CSE_2026_Y1.csv")).toBeTruthy();
    expect(screen.getByText("MCA_2026_Y1.csv")).toBeTruthy();
    // Page size 6: the seventh and eighth rows are on the next page.
    expect(screen.queryByText("BTech_CIVIL_2026_Y1.csv")).toBeNull();
    expect(screen.queryByText("BTech_EEE_2026_Y1.csv")).toBeNull();

    // Timestamps are rendered in IST (10:42 UTC is 16:12 IST).
    expect(screen.getAllByText(/16:12 IST/).length).toBeGreaterThan(0);
    expect(screen.getByText(/^Showing 1–6 of 8 batches$/)).toBeTruthy();
  });

  it("filters by status and by search text", async () => {
    stubBatches();
    await renderDashboard();
    await screen.findByText("BTech_CSE_2026_Y1.csv");

    fireEvent.click(screen.getByRole("button", { name: /needs review/i }));
    expect(screen.getByText(/Showing 1–2 of 2 batches/)).toBeTruthy();
    expect(screen.queryByText("BTech_ECE_2026_Y1.csv")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /all batches/i }));
    fireEvent.change(screen.getByLabelText(/search by file name or batch id/i), {
      target: { value: "ECE" },
    });
    expect(screen.getByText("BTech_ECE_2026_Y1.csv")).toBeTruthy();
    expect(screen.queryByText("BTech_CSE_2026_Y1.csv")).toBeNull();
  });

  it("paginates the batch list", async () => {
    stubBatches();
    await renderDashboard();
    await screen.findByText("BTech_CSE_2026_Y1.csv");

    fireEvent.click(screen.getByRole("button", { name: /^next$/i }));
    expect(await screen.findByText(/Showing 7–8 of 8 batches/)).toBeTruthy();
    expect(screen.getByText("BTech_CIVIL_2026_Y1.csv")).toBeTruthy();
    expect(screen.getByText("BTech_EEE_2026_Y1.csv")).toBeTruthy();
  });

  it("shows explicit empty state and zero counts when the institution has no batches", async () => {
    stubBatches({
      batches: [],
      totals: { batches: 0, total_rows: 0, valid_rows: 0, invalid_rows: 0 },
    });
    await renderDashboard();

    expect(await screen.findByText(/no batches yet/i)).toBeTruthy();
    expect(screen.getByText("0 of 0")).toBeTruthy();
    expect(screen.getByText("No row errors recorded")).toBeTruthy();
  });

  it("reports a load failure without inventing numbers, and retries", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValueOnce(jsonResponse(PAYLOAD));
    vi.stubGlobal("fetch", fetchMock);

    await renderDashboard();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/could not load batches/i);
    // The message names the likely cause instead of "Failed to fetch", and the
    // banner no longer repeats itself (it used to read "Could not load batch
    // data. Could not load batch data: …").
    expect(alert.textContent).toMatch(/server did not respond/i);
    expect(alert.textContent).toMatch(/check that the backend is running/i);
    expect(alert.textContent?.match(/could not load/gi)).toHaveLength(1);
    // No metric is rendered until the server answers.
    expect(screen.getAllByText("—").length).toBe(3);

    fireEvent.click(within(alert).getByRole("button", { name: /try again/i }));
    expect(await screen.findByText("753")).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("offers the upload action only to a role that can create batches", async () => {
    stubBatches();
    await renderDashboard(AUDITOR);

    const upload = screen.getByRole("button", { name: /upload roster/i });
    expect(upload.hasAttribute("disabled")).toBe(true);
    expect(upload.getAttribute("title")).toMatch(/institution data operator/i);
    expect(screen.queryByRole("link", { name: /upload roster/i })).toBeNull();
  });

  it("links the upload action to roster intake for an operator", async () => {
    stubBatches();
    await renderDashboard();

    const upload = screen.getByRole("link", { name: /upload roster/i });
    expect(upload.getAttribute("href")).toBe("#roster-intake");
  });

  it("refetches when refresh is pressed", async () => {
    const fetchMock = stubBatches();
    await renderDashboard();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: /refresh/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });
});
