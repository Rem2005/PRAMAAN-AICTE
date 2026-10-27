import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { SessionUser } from "./lib/api";

const OPERATOR: SessionUser = {
  authenticated: true,
  username: "operator1",
  institution_id: 1,
  institution_name: "Test Institution",
  roles: ["INSTITUTION_DATA_OPERATOR"],
};

const ANONYMOUS: SessionUser = {
  authenticated: false,
  username: "",
  institution_id: 0,
  institution_name: "",
  roles: [],
};

const EMPTY_BATCHES = {
  batches: [],
  totals: { batches: 0, total_rows: 0, valid_rows: 0, invalid_rows: 0 },
};

function stubFetch(session: SessionUser, roles?: string[]) {
  const resolved: SessionUser = roles ? { ...session, roles } : session;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/auth/me")) {
        return { ok: true, status: 200, json: async () => resolved } as Response;
      }
      if (url.includes("/api/v1/batches")) {
        return { ok: true, status: 200, json: async () => EMPTY_BATCHES } as Response;
      }
      if (url.includes("/api/v1/reconciliation/snapshots")) {
        return { ok: true, status: 200, json: async () => ({ snapshots: [] }) } as Response;
      }
      if (url.includes("/api/v1/reconciliation/policies")) {
        return { ok: true, status: 200, json: async () => ({ policies: [] }) } as Response;
      }
      if (url.includes("/api/v1/reconciliation/runs")) {
        return { ok: true, status: 200, json: async () => ({ runs: [] }) } as Response;
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: "ok" }),
      } as Response;
    }),
  );
}

describe("App", () => {
  beforeEach(() => {
    stubFetch(OPERATOR);
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  /** The desktop sidebar. The compact header mirrors the same navigation at
   * narrow widths; Tailwind's `hidden` is CSS that jsdom does not apply, so
   * tests scope to one region rather than matching both. */
  const sidebar = () => within(screen.getByRole("complementary"));

  const dashboardHeading = () =>
    screen.findByRole("heading", { name: /welcome back, operator1/i });

  it("renders the dashboard heading for a signed-in user", async () => {
    render(<App />);
    expect(await dashboardHeading()).toBeTruthy();
  });

  it("renders Roster Intake as an available navigation link", async () => {
    render(<App />);
    await dashboardHeading();
    const link = sidebar().getByText("Roster Intake").closest("a");
    expect(link).toBeTruthy();
    expect(link?.getAttribute("href")).toBe("#roster-intake");
    expect(link?.hasAttribute("disabled")).toBe(false);
  });

  it("renders every implemented screen as a real navigation link", async () => {
    render(<App />);
    await dashboardHeading();

    for (const [label, href] of [
      ["Reconciliation", "#reconciliation"],
      ["Identity Review", "#identity-review"],
      ["Verification Requests", "#verification-requests"],
      ["Reports / Audit", "#reports-audit"],
      ["Administration", "#administration"],
    ] as [string, string][]) {
      const link = sidebar().getByText(label).closest("a");
      expect(link, `${label} must be a link, not a disabled button`).toBeTruthy();
      expect(link?.getAttribute("href")).toBe(href);
    }
    // No navigation entry is left as a dead/disabled control.
    expect(sidebar().queryAllByRole("button")).toHaveLength(0);
  });

  it("shows the signed-in user, institution and sign-out control", async () => {
    render(<App />);
    await dashboardHeading();
    expect(screen.getByText("operator1")).toBeTruthy();
    expect(screen.getByText("Test Institution")).toBeTruthy();
    expect(screen.getByRole("button", { name: /sign out/i })).toBeTruthy();
  });

  it("hides Roster Intake from a role that cannot use it", async () => {
    cleanup();
    stubFetch(OPERATOR, ["AUDITOR"]);
    render(<App />);

    await dashboardHeading();
    const item = sidebar().getByText("Roster Intake");
    // Still listed, but clearly unavailable rather than silently removed.
    expect(item.closest("button")?.hasAttribute("disabled")).toBe(true);
    expect(item.closest("a")).toBeNull();
  });

  it("shows the sign-in page instead of the app when there is no session", async () => {
    cleanup();
    stubFetch(ANONYMOUS);
    render(<App />);

    expect(await screen.findByRole("heading", { name: /sign in/i })).toBeTruthy();
    expect(screen.getByLabelText(/username/i)).toBeTruthy();
    expect(screen.getByLabelText(/password/i)).toBeTruthy();
    expect(screen.queryByRole("heading", { name: /welcome back/i })).toBeNull();
    expect(screen.queryByText("Roster Intake")).toBeNull();
    // No application shell is exposed while signed out.
    expect(screen.queryByRole("complementary")).toBeNull();
  });

  it("keeps showing a loading state until the server answers", async () => {
    cleanup();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise(() => {
            /* never resolves */
          }),
      ),
    );
    render(<App />);
    expect(screen.getByRole("status").textContent).toMatch(/checking session/i);
    expect(screen.queryByRole("heading", { name: /sign in/i })).toBeNull();
  });

  it("treats an unreadable session as signed out", async () => {
    cleanup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      }),
    );
    render(<App />);
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /sign in/i })).toBeTruthy(),
    );
  });
});
