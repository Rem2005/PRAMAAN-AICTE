import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdministrationPage } from "./AdministrationPage";
import type { SessionUser } from "../lib/api";

const OPERATOR: SessionUser = {
  authenticated: true,
  username: "operator1",
  institution_id: 4,
  institution_name: "Synthetic Verification Institute",
  roles: ["INSTITUTION_DATA_OPERATOR"],
};

const POLICY = {
  policy_id: 1,
  version: 1,
  name: "Synthetic demo policy v1",
  description: null,
  status: "ACTIVE",
  rules: {
    compare_fields: ["course_code", "academic_year"],
    check_capacity: true,
  },
  rules_checksum: "a".repeat(64),
  created_at: "2026-10-25T09:00:00",
  activated_at: "2026-10-25T09:00:00",
};

const SNAPSHOT = {
  snapshot_id: 1,
  version: 1,
  status: "APPROVED",
  source_ref: "SYNTHETIC-DEMO-SNAPSHOT-2026-2027",
  created_at: "2026-10-25T09:00:00",
  approved_at: "2026-10-25T09:00:00",
  approved_by: "seed-demo (synthetic)",
  entry_count: 15,
};

function response(body: unknown, ok = true, status = 200): Response {
  return { ok, status, json: async () => body } as Response;
}

function stubApi(options: {
  snapshots?: unknown;
  policies?: unknown;
  status?: number;
} = {}) {
  const failing = options.status !== undefined;
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (failing) {
      return response({ detail: "You do not have the required role." }, false, options.status);
    }
    if (url.includes("/api/v1/reconciliation/snapshots")) {
      return response(options.snapshots ?? { snapshots: [SNAPSHOT] });
    }
    if (url.includes("/api/v1/reconciliation/policies")) {
      return response(options.policies ?? { policies: [POLICY] });
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function renderPage(session: SessionUser = OPERATOR) {
  render(<AdministrationPage session={session} />);
  // The page issues both reads on mount.
  await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
}

describe("AdministrationPage", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows the signed-in account from the session, not from a request", async () => {
    const fetchMock = stubApi();
    await renderPage();

    const account = screen.getByRole("heading", { name: /signed-in account/i })
      .parentElement as HTMLElement;
    expect(within(account).getByText("operator1")).toBeTruthy();
    expect(within(account).getByText("Institution Data Operator")).toBeTruthy();
    expect(within(account).getByText(/Synthetic Verification Institute/)).toBeTruthy();
    expect(within(account).getByText(/id 4/)).toBeTruthy();
    expect(within(account).getByText(/read from the server-side session/i)).toBeTruthy();

    // Only the two versioned-configuration reads are made.
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("renders the versioned configuration from the API", async () => {
    stubApi();
    render(<AdministrationPage session={OPERATOR} />);

    expect(await screen.findByText("Synthetic demo policy v1")).toBeTruthy();
    expect(screen.getAllByText("ACTIVE").length).toBeGreaterThan(0);
    expect(screen.getByText("APPROVED")).toBeTruthy();
    expect(screen.getByText("course_code, academic_year")).toBeTruthy();
    expect(screen.getByText("SYNTHETIC-DEMO-SNAPSHOT-2026-2027")).toBeTruthy();
    expect(screen.getByText("seed-demo (synthetic)")).toBeTruthy();
    // Approved lines come from the API, not a placeholder.
    expect(screen.getByText("15")).toBeTruthy();
    // Seeded demo records stay labelled.
    expect(screen.getByText(/synthetic seed/i)).toBeTruthy();
  });

  it("explains a role that cannot read the configuration instead of failing", async () => {
    stubApi({ status: 403 });
    await renderPage();

    expect(
      await screen.findByText(/your role cannot read policy or intake-snapshot versions/i),
    ).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
    // The rest of the screen still works.
    expect(screen.getByRole("button", { name: /^copy$/i })).toBeTruthy();
  });

  it("reports a real load failure and retries", async () => {
    // Both reads fail once; the retry is served normally.
    let attempt = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      attempt += 1;
      if (attempt <= 2) {
        return response({ detail: "Service unavailable." }, false, 503);
      }
      return url.includes("/snapshots")
        ? response({ snapshots: [SNAPSHOT] })
        : response({ policies: [POLICY] });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<AdministrationPage session={OPERATOR} />);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/service unavailable/i);
    // Other screens' data is never invented to fill the gap.
    expect(screen.queryByText("Synthetic demo policy v1")).toBeNull();

    fireEvent.click(within(alert).getByRole("button", { name: /try again/i }));

    expect(await screen.findByText("Synthetic demo policy v1")).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("offers the seed command when nothing is configured", async () => {
    stubApi({ snapshots: { snapshots: [] }, policies: { policies: [] } });
    await renderPage();

    expect(await screen.findByText(/nothing is configured yet/i)).toBeTruthy();
    expect(
      screen.getByText(/python -m app.cli seed-demo --institution 4/),
    ).toBeTruthy();
  });

  it("labels unavailable account capabilities and copies the provisioning command", async () => {
    stubApi();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    await renderPage();

    const accounts = screen.getByRole("heading", { name: /accounts and roles/i })
      .parentElement as HTMLElement;
    // Ten capabilities are stated honestly: one CLI-only, the rest unavailable.
    expect(within(accounts).getAllByText(/not available/i)).toHaveLength(3);
    expect(within(accounts).getByText(/CLI only/i)).toBeTruthy();
    // No control pretends account management exists.
    expect(within(accounts).queryAllByRole("button")).toHaveLength(1);

    fireEvent.click(within(accounts).getByRole("button", { name: /^copy$/i }));

    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    const copied = writeText.mock.calls[0][0] as string;
    expect(copied).toContain("python -m app.cli create-user");
    expect(copied).toContain("--institution 4");
    // A password placeholder, never a real secret.
    expect(copied).toContain("NEW_USER_PASSWORD='…'");
    expect(await screen.findByText(/copied to clipboard/i)).toBeTruthy();
  });

  it("says so when the clipboard is unavailable", async () => {
    stubApi();
    Object.assign(navigator, { clipboard: undefined });

    await renderPage();
    fireEvent.click(screen.getByRole("button", { name: /^copy$/i }));

    expect(
      await screen.findByText(/copy is unavailable in this browser/i),
    ).toBeTruthy();
  });
});
