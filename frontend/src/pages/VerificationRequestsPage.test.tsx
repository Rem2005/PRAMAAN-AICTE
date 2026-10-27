import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { VerificationRequestsPage } from "./VerificationRequestsPage";

function renderPage() {
  return render(<VerificationRequestsPage />);
}

describe("VerificationRequestsPage", () => {
  beforeEach(() => {
    // There is no request API; the screen must not call one.
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("names itself once and states the capability is not connected", () => {
    renderPage();

    expect(
      screen.getByRole("heading", { level: 1, name: /verification requests/i }),
    ).toBeTruthy();
    expect(screen.getAllByText(/not connected/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/0 requests/i)).toBeTruthy();
  });

  it("shows the request columns with an empty state and no create action", () => {
    renderPage();

    const table = screen.getByRole("table");
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((cell) => cell.textContent),
    ).toEqual([
      "Reference",
      "Purpose",
      "Claims requested",
      "Consent / authority",
      "Status",
    ]);
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    expect(within(table).getByText(/no requests/i)).toBeTruthy();

    // Nothing can be created, so no control may offer to create or send one.
    expect(
      screen.queryByRole("button", { name: /new request|raise request|send request/i }),
    ).toBeNull();
    const search = screen.getByLabelText(/search/i) as HTMLInputElement;
    expect(search.disabled).toBe(true);
    expect((screen.getByLabelText(/^status$/i) as HTMLSelectElement).disabled).toBe(true);
    expect(screen.getByText(/search and filters are disabled/i)).toBeTruthy();
  });

  it("labels the proposed flow as a preview and claims no integration", () => {
    renderPage();

    const flow = screen.getByRole("heading", { name: /proposed request flow/i })
      .parentElement as HTMLElement;
    expect(within(flow).getByText(/preview/i)).toBeTruthy();

    const steps = screen.getAllByRole("listitem");
    expect(steps.map((step) => step.textContent)).toEqual([
      expect.stringContaining("Request raised"),
      expect.stringContaining("Authority checked"),
      expect.stringContaining("Minimum claims"),
      expect.stringContaining("Receipt recorded"),
    ]);

    expect(screen.getByText(/no AICTE, APAAR\/ABC or DigiLocker integration/i)).toBeTruthy();
    expect(fetch).not.toHaveBeenCalled();
  });
});
