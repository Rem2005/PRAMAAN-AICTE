import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LoginPage } from "./LoginPage";
import type { SessionUser } from "../lib/api";

const SESSION: SessionUser = {
  authenticated: true,
  username: "operator1",
  institution_id: 1,
  institution_name: "Test Institution",
  roles: ["INSTITUTION_DATA_OPERATOR"],
};

describe("LoginPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("requires both fields before calling the API", async () => {
    const onSignedIn = vi.fn();
    render(<LoginPage onSignedIn={onSignedIn} />);

    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByText(/enter a username and password/i)).toBeTruthy();
    expect(fetch).not.toHaveBeenCalled();
    expect(onSignedIn).not.toHaveBeenCalled();
  });

  it("posts the credentials and hands the session back", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => SESSION,
    } as Response);

    const onSignedIn = vi.fn();
    render(<LoginPage onSignedIn={onSignedIn} />);

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: "operator1" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(onSignedIn).toHaveBeenCalledWith(SESSION));

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toContain("/api/v1/auth/login");
    expect((init as RequestInit).credentials).toBe("include");
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({
      username: "operator1",
      password: "secret",
    });
  });

  it("surfaces the server's rejection without leaking the password", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Incorrect username or password." }),
    } as Response);

    const onSignedIn = vi.fn();
    render(<LoginPage onSignedIn={onSignedIn} />);

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: "operator1" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "hunter2" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toMatch(
        /incorrect username or password/i,
      ),
    );
    expect(screen.queryByRole("alert")?.textContent).not.toContain("hunter2");
    expect(onSignedIn).not.toHaveBeenCalled();
  });
});
