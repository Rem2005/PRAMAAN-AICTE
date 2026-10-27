import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RosterIntakePage } from "./RosterIntakePage";
import type { SessionUser } from "../lib/api";

const OPERATOR: SessionUser = {
  authenticated: true,
  username: "operator1",
  institution_id: 7,
  institution_name: "Test Institution",
  roles: ["INSTITUTION_DATA_OPERATOR"],
};

const createResponse = {
  batch_id: 42,
  state: "CREATED",
  idempotency_key: "key-1",
  created_at: "2026-10-25T00:00:00+00:00",
};

const validValidateResponse = {
  batch_id: 42,
  state: "VALIDATED",
  total_rows: 2,
  valid_rows: 2,
  invalid_rows: 0,
  duplicate_rows: 0,
  rows: [
    { row_number: 2, local_ref: "SYN-00001", valid: true, errors: [] },
    { row_number: 3, local_ref: "SYN-00002", valid: true, errors: [] },
  ],
};

const invalidValidateResponse = {
  ...validValidateResponse,
  state: "VALIDATION_FAILED",
  valid_rows: 1,
  invalid_rows: 1,
  rows: [
    { row_number: 2, local_ref: "SYN-00001", valid: true, errors: [] },
    {
      row_number: 3,
      local_ref: null,
      valid: false,
      errors: ["row 3: local_ref is required"],
    },
  ],
};

function selectFile() {
  const input = document.getElementById("roster-file") as HTMLInputElement;
  const file = new File(["a,b\n1,2\n"], "roster.csv", { type: "text/csv" });
  fireEvent.change(input, { target: { files: [file] } });
}

function renderPage() {
  return render(<RosterIntakePage session={OPERATOR} />);
}

/** jsdom's Blob has no text() method; FileReader is implemented. */
function blobText(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}

describe("RosterIntakePage upload", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("creates the batch without an invented checksum and with a retryable key", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => createResponse,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => validValidateResponse,
      } as Response);

    renderPage();
    selectFile();
    fireEvent.click(screen.getByRole("button", { name: /upload and validate/i }));

    expect(
      await screen.findByRole("heading", { name: /row-level validation/i }),
    ).toBeTruthy();

    expect(fetchMock).toHaveBeenCalledTimes(2);

    const [createUrl, createInit] = fetchMock.mock.calls[0];
    expect(String(createUrl)).toBe("/api/v1/batches");

    const body = JSON.parse((createInit as RequestInit).body as string);
    // Regression: an invented checksum was previously required and rejected
    // the real payload with 422.
    expect(body).not.toHaveProperty("checksum");
    expect(body.idempotency_key).toBeTruthy();
    // The institution comes from the session, never from a form field.
    expect(body.institution_id).toBe(7);
    expect(body.academic_year).toBe("2026-2027");
    expect(body.schema_version).toBe("v1");

    const [validateUrl] = fetchMock.mock.calls[1];
    expect(String(validateUrl)).toContain("/api/v1/batches/42/validate");

    for (const [, init] of fetchMock.mock.calls) {
      expect((init as RequestInit | undefined)?.credentials).toBe("include");
    }
  });

  it("reuses the same create key when the upload is retried for the same file", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: "The server rejected the request." }),
    } as Response);

    renderPage();
    selectFile();
    fireEvent.click(screen.getByRole("button", { name: /upload and validate/i }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/server rejected the request/i);

    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => createResponse,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => validValidateResponse,
      } as Response);

    fireEvent.click(screen.getByRole("button", { name: /upload and validate/i }));

    await waitFor(() => expect(fetchMock.mock.calls.length).toBe(3));

    const bodies = fetchMock.mock.calls
      .map(([, init]) => init as RequestInit | undefined)
      .filter((init) => init && typeof init.body === "string")
      .map((init) => JSON.parse(init!.body as string));

    expect(bodies).toHaveLength(2);
    expect(bodies[0].idempotency_key).toBeTruthy();
    expect(bodies[0].idempotency_key).toBe(bodies[1].idempotency_key);
  });

  it("blocks confirmation while any row is invalid and explains the correction", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => createResponse,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => invalidValidateResponse,
      } as Response);

    renderPage();
    selectFile();
    fireEvent.click(screen.getByRole("button", { name: /upload and validate/i }));

    await screen.findByRole("heading", { name: /row-level validation/i });

    const confirm = screen.getByRole("button", {
      name: /confirm and submit/i,
    }) as HTMLButtonElement;
    expect(confirm.disabled).toBe(true);
    expect(screen.getByText(/1 row needs correction/i)).toBeTruthy();
    expect(screen.getByText(/row 3: local_ref is required/i)).toBeTruthy();

    // Only create + validate were called; nothing was submitted.
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("re-validates the same batch when a corrected file is uploaded", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => createResponse,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => invalidValidateResponse,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ ...validValidateResponse, state: "VALIDATED" }),
      } as Response);

    renderPage();
    selectFile();
    fireEvent.click(screen.getByRole("button", { name: /upload and validate/i }));
    await screen.findByRole("heading", { name: /row-level validation/i });

    fireEvent.click(screen.getByRole("button", { name: /re-validate this batch/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));

    // No second batch is created: the corrected file re-validates batch 42.
    const [url] = fetchMock.mock.calls[2];
    expect(String(url)).toContain("/api/v1/batches/42/validate");
    const confirm = screen.getByRole("button", {
      name: /confirm and submit/i,
    }) as HTMLButtonElement;
    await waitFor(() => expect(confirm.disabled).toBe(false));
  });

  it("confirms a clean batch and reports the persisted count from the server", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => createResponse,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => validValidateResponse,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          batch_id: 42,
          state: "SUBMITTED_FOR_REVIEW",
          persisted_count: 2,
        }),
      } as Response);

    renderPage();
    selectFile();
    fireEvent.click(screen.getByRole("button", { name: /upload and validate/i }));
    await screen.findByRole("heading", { name: /row-level validation/i });

    fireEvent.click(screen.getByRole("button", { name: /confirm and submit/i }));

    const alert = await screen.findByRole("status");
    expect(alert.textContent).toMatch(/batch #42/i);
    expect(alert.textContent).toMatch(/2 persisted rows/i);
    expect(alert.textContent).toMatch(/submitted for review/i);

    const [confirmUrl, confirmInit] = fetchMock.mock.calls[2];
    expect(String(confirmUrl)).toContain("/api/v1/batches/42/confirm");
    expect(JSON.parse((confirmInit as RequestInit).body as string)).toEqual({
      idempotency_key: "key-1",
    });
  });

  it("offers a sample CSV download that matches the intake contract", async () => {
    // jsdom implements neither method; capture the Blob instead of the URL.
    let downloaded: Blob | null = null;
    const createObjectURL = vi.fn((blob: Blob) => {
      downloaded = blob;
      return "blob:sample";
    });
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});

    renderPage();
    fireEvent.click(
      screen.getByRole("button", { name: /download sample CSV/i }),
    );

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    const anchor = clickSpy.mock.instances[0] as unknown as HTMLAnchorElement;
    expect(anchor.download).toBe("pramaan-sample-roster.csv");

    const csv = await blobText(downloaded as unknown as Blob);
    const [header, ...rows] = csv.trimEnd().split("\n");
    expect(header).toBe(
      "local_ref,course_code,academic_year,seat_category,entry_level,identity_status,apaar_id",
    );
    expect(rows).toHaveLength(10);
    // The batch's academic year, so the file validates against this batch.
    expect(rows.every((row) => row.split(",")[2] === "2026-2027")).toBe(true);

    clickSpy.mockRestore();
  });

  it("reports validation failures from the server verbatim", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => createResponse,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ ...invalidValidateResponse, rows: [] }),
      } as Response);

    renderPage();
    selectFile();
    fireEvent.click(screen.getByRole("button", { name: /upload and validate/i }));
    await screen.findByRole("heading", { name: /row-level validation/i });
    // A batch with invalid rows can never be confirmed, even with no row list.
    expect(
      (screen.getByRole("button", { name: /confirm and submit/i }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });
});
