import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { buildSampleRoster, ROSTER_COLUMNS } from "./sampleRoster";

/** The academic year both checked-in sample files and the screen default to. */
const DEFAULT_YEAR = "2026-2027";

// Resolved through node:path rather than `new URL`: the files live outside the
// Vite root, which the asset pipeline refuses to serve.
const SAMPLES_DIR = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../../../docs/samples",
);

function checkedInSample(filename: string): string {
  return readFileSync(resolve(SAMPLES_DIR, filename), "utf8").replace(
    /\r\n/g,
    "\n",
  );
}

function rows(csv: string): string[][] {
  return csv
    .trimEnd()
    .split("\n")
    .map((line) => line.split(","));
}

describe("sample roster generator", () => {
  // The download the intake screen offers must be the file the backend tests
  // validate. Comparing row for row keeps the two from drifting apart.
  it("reproduces docs/samples/sample-roster.csv row for row", () => {
    expect(rows(buildSampleRoster(DEFAULT_YEAR))).toEqual(
      rows(checkedInSample("sample-roster.csv")),
    );
  });

  it("reproduces docs/samples/sample-roster-with-errors.csv row for row", () => {
    expect(rows(buildSampleRoster(DEFAULT_YEAR, true))).toEqual(
      rows(checkedInSample("sample-roster-with-errors.csv")),
    );
  });

  it("uses the backend's required column names in order", () => {
    // Mirrors REQUIRED_COLUMNS in backend/app/services/roster.py.
    expect(ROSTER_COLUMNS.slice(0, 6)).toEqual([
      "local_ref",
      "course_code",
      "academic_year",
      "seat_category",
      "entry_level",
      "identity_status",
    ]);
    expect(rows(buildSampleRoster(DEFAULT_YEAR))[0]).toEqual([
      ...ROSTER_COLUMNS,
    ]);
  });

  it("keeps ten valid rows and only fake identifiers", () => {
    const valid = rows(buildSampleRoster(DEFAULT_YEAR)).slice(1);
    expect(valid).toHaveLength(10);

    const identifiers = rows(buildSampleRoster(DEFAULT_YEAR, true))
      .slice(1)
      .map((row) => row[6]);
    // No real APAAR ID is committed: every value is a 999… placeholder.
    expect(identifiers.every((value) => /^999\d{10}$/.test(value))).toBe(true);
    expect(new Set(identifiers).size).toBe(identifiers.length);
  });

  it("follows the batch's academic year so the file validates", () => {
    const csv = buildSampleRoster("2030-2031");
    expect(rows(csv).slice(1).every((row) => row[2] === "2030-2031")).toBe(true);
  });
});
