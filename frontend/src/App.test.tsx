import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: "ok" }) }));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders the dashboard heading", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: /dashboard/i })).toBeTruthy();
  });

  it("renders planned navigation areas that are not yet available as disabled", () => {
    render(<App />);
    expect(screen.getByText("Roster Intake").closest("button")).toBeTruthy();
    expect(screen.getByText("Roster Intake").closest("button")?.hasAttribute("disabled")).toBe(true);
  });
});
