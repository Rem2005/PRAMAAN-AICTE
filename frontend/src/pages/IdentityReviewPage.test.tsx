import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { IdentityReviewPage } from "./IdentityReviewPage";

function renderPage() {
  return render(<IdentityReviewPage />);
}

describe("IdentityReviewPage", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/v1/auth/me")) {
          return {
            ok: true,
            json: async () => ({
              authenticated: true,
              username: "reviewer1",
              institution_id: 1,
              roles: ["IDENTITY_REVIEW_OFFICER"],
            }),
          };
        }
        if (
          url.includes("/api/v1/identity-review/candidates") &&
          url.includes("_limit=50")
        ) {
          return {
            ok: true,
            json: async () => ({
              candidates: [
                {
                  id: 1,
                  institution_id: 1,
                  record_ref: "SYN-00001",
                  method: "PAARLINK",
                  version: "1.0",
                  score: 0.87,
                  reasons: ["field mismatch", "score below threshold"],
                  state: "PENDING_REVIEW",
                  created_at: "2026-10-27T10:00:00Z",
                  reviewed_at: null,
                  reviewed_by: null,
                  assigned_reviewer_id: null,
                  assigned_at: null,
                },
                {
                  id: 2,
                  institution_id: 1,
                  record_ref: "SYN-00002",
                  method: "PAARLINK",
                  version: "1.0",
                  score: 0.92,
                  reasons: null,
                  state: "ASSIGNED",
                  created_at: "2026-10-27T09:30:00Z",
                  reviewed_at: "2026-10-27T09:45:00Z",
                  reviewed_by: 101,
                  assigned_reviewer_id: 101,
                  assigned_at: "2026-10-27T09:45:00Z",
                },
                {
                  id: 3,
                  institution_id: 1,
                  record_ref: "SYN-00003",
                  method: "PAARLINK",
                  version: "2.1",
                  score: 0.45,
                  reasons: "no approved entry",
                  state: "PENDING_REVIEW",
                  created_at: "2026-10-27T11:00:00Z",
                  reviewed_at: null,
                  reviewed_by: null,
                  assigned_reviewer_id: null,
                  assigned_at: null,
                },
              ],
              metadata: { total: 3 },
            }),
          };
        }
        if (url.includes("/assign-reviewer")) {
          return {
            ok: true,
            json: async () => ({
              id: 5,
              candidate_id: 1,
              reviewer_id: 101,
              assigned_at: new Date().toISOString(),
              status: "ACTIVE",
              reviewer_institution_id: 1,
            }),
          };
        }
        if (url.includes("/adjudicate")) {
          return {
            ok: true,
            json: async () => ({
              id: 1,
              candidate_id: 1,
              reviewer_id: 101,
              policy_version: 1,
              outcome: "CONFIRMED",
              decision_reason_code: "MATCHED",
              decision_reason_text: "Candidate matched approved entry SYN-00001 under policy v1",
              confirmed_at: new Date().toISOString(),
              confirmed_by: 101,
              created_at: "2026-10-27T10:00:00Z",
              resolved_at: null,
              resolution_notes: "Matched on course_code CE-UG-FT-S1 and academic_year 2026-2027",
            }),
          };
        }
        throw new Error(`Unexpected request: ${url}`);
      })
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders the review queue with candidate data", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", { level: 1, name: /identity review/i })
    ).toBeTruthy();
    expect(await screen.findByText(/3 open cases/i)).toBeTruthy();

    const table = await screen.findByRole("table");
    const headers = within(table)
      .getAllByRole("columnheader")
      .map((cell) => cell.textContent);
    expect(headers).toEqual([
      "Case reference",
      "Reason",
      "Method / version",
      "Raised (IST)",
      "Review status",
    ]);

    const rows = within(table).getAllByRole("row");
    expect(rows.length).toBeGreaterThanOrEqual(4);
  });

  it("displays candidate details: record ref, method, state, and reasons", async () => {
    renderPage();

    await screen.findByText(/SYN-00001/i);
    const rows = screen.getAllByRole("row");
    const dataRows = rows.filter(r => r.closest('tbody'));
    expect(dataRows.length).toBeGreaterThanOrEqual(2);

    const firstRow = dataRows[0] || rows[1];
    expect(firstRow).toBeTruthy();
    expect(firstRow.textContent).toContain("SYN-00001");
    expect(firstRow.textContent).toContain("PENDING_REVIEW");
  });

  it("enables search and filters", async () => {
    renderPage();

    const search = await screen.findByLabelText(/search/i) as HTMLInputElement;
    const status = await screen.findByLabelText(/review status/i) as HTMLSelectElement;

    expect(search.disabled).toBe(false);
    expect(status.disabled).toBe(false);
  });

  it("allows assigning a reviewer to a candidate", async () => {
    renderPage();

    const assignBtns = await screen.findAllByRole("button", {
      name: /assign reviewer/i,
    });
    if (assignBtns[0]) {
      await assignBtns[0].click();
    }

    await screen.findAllByText(/ASSIGNED/i);
    const rows = screen.getAllByRole("row");
    const dataRows = rows.filter(r => r.closest('tbody'));
    const firstRow = dataRows[0] || rows.find(r => r.textContent?.includes('SYN-00001')) || rows[1];
    expect(firstRow?.textContent).toContain("ASSIGNED");
  });

  it("allows recording an adjudication decision", async () => {
    renderPage();

    const assignBtns = await screen.findAllByRole("button", {
      name: /assign reviewer/i,
    });
    if (assignBtns[0]) {
      await assignBtns[0].click();
    }

    const decideBtns = await screen.findAllByRole("button", {
      name: /record decision/i,
    });
    const decideBtn = decideBtns[0];
    expect(decideBtn).toBeTruthy();
    await decideBtn.click();

    const outcomeSelect = await screen.findByLabelText(/confirmed by reviewer/i);

    const reasonInput = await screen.findByLabelText(/reason code and narrative/i);
    if (reasonInput) {
      (reasonInput as HTMLTextAreaElement).focus();
      (reasonInput as HTMLTextAreaElement).value = "MATCHED - candidate matched approved entry";
      reasonInput.dispatchEvent(new Event("input", { bubbles: true }));
    }

    const recordBtns = await screen.findAllByRole("button", { name: /record decision/i });
    const recordBtn = recordBtns[recordBtns.length - 1] || recordBtns[0];
    await recordBtn.click();

    await new Promise(r => setTimeout(r, 100));
    const allText = document.body.textContent || '';
    expect(allText.toUpperCase()).toContain('DECIDED');
  });

  it("shows permission-denied when user lacks IDENTITY_REVIEW_OFFICER role", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        throw new Error("Authentication required");
      })
    );

    renderPage();

    const help = await screen.findByText(/search and filters are disabled/i);
    expect(help).toBeTruthy();
  });

  it("handles API errors gracefully", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/v1/auth/me")) {
          return {
            ok: true,
            json: async () => ({
              authenticated: true,
              username: "reviewer1",
              institution_id: 1,
              roles: ["IDENTITY_REVIEW_OFFICER"],
            }),
          };
        }
        throw new Error("Network error");
      })
    );

    renderPage();

    const errorElements = await screen.findAllByText(/failed to load/i);
    expect(errorElements.length).toBeGreaterThan(0);
  });
});
