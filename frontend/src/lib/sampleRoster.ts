/**
 * Synthetic sample roster for the intake demonstration.
 *
 * Every value here is fabricated (`999…` identifier prefix, invented
 * references). It exists so the upload flow can be tried without any real
 * student data, and it is kept byte-for-byte in step with the files in
 * `docs/samples/` — `frontend/src/lib/sampleRoster.test.ts` fails if the two
 * drift. Column names must stay in sync with REQUIRED_COLUMNS in
 * backend/app/services/roster.py.
 */

export const ROSTER_COLUMNS = [
  "local_ref",
  "course_code",
  "academic_year",
  "seat_category",
  "entry_level",
  "identity_status",
  "apaar_id",
] as const;

type SampleRow = {
  ref: string;
  course: string;
  /** Empty or outside the vocabulary for the deliberately broken rows. */
  category: string;
  level: string;
  identity: string;
};

/** Ten rows that pass validation (`docs/samples/sample-roster.csv`). */
const VALID_ROWS: SampleRow[] = [
  { ref: "SYN-00001", course: "CE-UG-FT-S1", category: "CAP_GENERAL", level: "FIRST_YEAR", identity: "DOMESTIC_APAAR" },
  { ref: "SYN-00002", course: "CS-UG-FT-S1", category: "CAP_GENERAL", level: "FIRST_YEAR", identity: "DOMESTIC_APAAR" },
  { ref: "SYN-00003", course: "ME-UG-FT-S1", category: "CAP_OBC", level: "FIRST_YEAR", identity: "DOMESTIC_APAAR" },
  { ref: "SYN-00004", course: "CE-UG-FT-S1", category: "CAP_SC", level: "FIRST_YEAR", identity: "DOMESTIC_APAAR" },
  { ref: "SYN-00005", course: "CS-UG-FT-S1", category: "CAP_EWS", level: "FIRST_YEAR", identity: "DOMESTIC_APAAR" },
  { ref: "SYN-00006", course: "ME-UG-FT-S1", category: "CAP_ST", level: "FIRST_YEAR", identity: "DOMESTIC_APAAR" },
  { ref: "SYN-00007", course: "CE-UG-FT-S1", category: "CAP_GENERAL", level: "FIRST_YEAR", identity: "NRI" },
  { ref: "SYN-00008", course: "CS-UG-FT-S1", category: "CAP_OBC", level: "FIRST_YEAR", identity: "INTERNATIONAL" },
  { ref: "SYN-00009", course: "EC-UG-FT-S3", category: "CAP_GENERAL", level: "SECOND_YEAR", identity: "DOMESTIC_APAAR" },
  { ref: "SYN-00010", course: "ME-UG-FT-S5", category: "CAP_SC", level: "THIRD_YEAR", identity: "DOMESTIC_APAAR" },
];

/**
 * Three rows that keep the column contract but break a rule, so the row-level
 * validation report can be demonstrated: a missing seat category, a value
 * outside the documented vocabulary, and a repeated local reference.
 */
const INVALID_ROWS: SampleRow[] = [
  { ref: "SYN-00011", course: "CE-UG-FT-S1", category: "", level: "FIRST_YEAR", identity: "DOMESTIC_APAAR" },
  { ref: "SYN-00012", course: "CS-UG-FT-S1", category: "CAP_GENERAL", level: "YEAR_ONE", identity: "DOMESTIC_APAAR" },
  { ref: "SYN-00001", course: "ME-UG-FT-S1", category: "CAP_SC", level: "FIRST_YEAR", identity: "DOMESTIC_APAAR" },
];

/** Placeholder identifier, continuing across the valid and invalid rows. */
function placeholderApaarId(index: number): string {
  return `999${String(index).padStart(10, "0")}`;
}

function csvField(value: string): string {
  return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}

function csvLine(row: SampleRow, academicYear: string, apaarIndex: number): string {
  return [
    row.ref,
    row.course,
    academicYear,
    row.category,
    row.level,
    row.identity,
    placeholderApaarId(apaarIndex),
  ]
    .map(csvField)
    .join(",");
}

/**
 * Build the sample CSV.
 *
 * `academicYear` fills the `academic_year` column, which the backend requires
 * to match the batch's academic year exactly. `withErrors` appends the three
 * rows that the backend rejects.
 */
export function buildSampleRoster(
  academicYear: string,
  withErrors = false,
): string {
  const lines: string[] = [ROSTER_COLUMNS.join(",")];

  VALID_ROWS.forEach((row, index) => {
    lines.push(csvLine(row, academicYear, index + 1));
  });

  if (withErrors) {
    INVALID_ROWS.forEach((row, index) => {
      lines.push(csvLine(row, academicYear, VALID_ROWS.length + index + 1));
    });
  }

  return `${lines.join("\n")}\n`;
}

/** Trigger a browser download of generated CSV text (no server round trip). */
export function downloadCsv(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  // Revoke on the next tick so the click has consumed the URL.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
