import { useCallback, useMemo, useRef, useState } from "react";
import {
  Alert,
  Button,
  DemoTag,
  PageHeader,
  StatCard,
  StatusBadge,
  batchStatus,
} from "../components/ui";
import { DownloadIcon, RefreshIcon, UploadIcon } from "../components/icons";
import {
  confirmIntakeBatch,
  createIntakeBatch,
  validateIntakeBatch,
  type BatchConfirmResponse,
  type BatchValidateResponse,
  type SessionUser,
} from "../lib/api";
import { formatCount } from "../lib/format";
import { buildSampleRoster, downloadCsv } from "../lib/sampleRoster";

const MAX_SIZE_MB = 5;
const PAGE_SIZE = 25;
const SCHEMA_VERSION = "v1";

type Stage = "select" | "review" | "done";
type RowFilter = "all" | "valid" | "invalid";

const STEPS: { id: Stage; label: string }[] = [
  { id: "select", label: "Upload roster" },
  { id: "review", label: "Review rows" },
  { id: "done", label: "Confirmed" },
];

function newKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `upload-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function plural(count: number, singular: string, pluralForm = `${singular}s`) {
  return count === 1 ? singular : pluralForm;
}

/**
 * Roster intake: upload, validate, review and explicitly confirm a CSV.
 *
 * Every number and row shown here comes from the API response for the batch
 * that was actually created; nothing is simulated in the client.
 */
export function RosterIntakePage({ session }: { session: SessionUser }) {
  const [academicYear, setAcademicYear] = useState("2026-2027");
  const [file, setFile] = useState<File | null>(null);
  const [stage, setStage] = useState<Stage>("select");
  const [busy, setBusy] = useState<"validating" | "confirming" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [batchId, setBatchId] = useState<number | null>(null);
  const [batchKey, setBatchKey] = useState<string | null>(null);
  const [validation, setValidation] = useState<BatchValidateResponse | null>(null);
  const [confirmation, setConfirmation] =
    useState<BatchConfirmResponse | null>(null);
  const [rowFilter, setRowFilter] = useState<RowFilter>("all");
  const [pageIndex, setPageIndex] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [uploadKey, setUploadKey] = useState(newKey);
  const fileInput = useRef<HTMLInputElement>(null);

  const acceptFile = useCallback(
    (selected: File) => {
      if (!selected.name.toLowerCase().endsWith(".csv")) {
        setError(`"${selected.name}" is not a CSV file. Upload a .csv file.`);
        return;
      }
      if (selected.size > MAX_SIZE_MB * 1024 * 1024) {
        setError(
          `"${selected.name}" is ${(selected.size / (1024 * 1024)).toFixed(1)} MB. ` +
            `The maximum is ${MAX_SIZE_MB} MB.`,
        );
        return;
      }
      setError(null);
      setFile(selected);
      // A new file is a new request: a fresh create key prevents this upload
      // from being replayed onto the previous batch.
      setUploadKey(newKey());
      if (stage !== "select") {
        setStage("select");
        setValidation(null);
        setBatchId(null);
        setBatchKey(null);
        setConfirmation(null);
        setRowFilter("all");
        setPageIndex(0);
      }
    },
    [stage],
  );

  const runValidation = useCallback(
    async (reuseBatch: boolean) => {
      if (!file) return;
      setBusy("validating");
      setError(null);
      try {
        let targetBatch = batchId;
        if (!reuseBatch || targetBatch === null) {
          const created = await createIntakeBatch({
            institution_id: session.institution_id,
            academic_year: academicYear,
            schema_version: SCHEMA_VERSION,
            idempotency_key: uploadKey,
          });
          targetBatch = created.batch_id;
          setBatchId(created.batch_id);
          setBatchKey(created.idempotency_key);
        }
        const result = await validateIntakeBatch(targetBatch, file);
        setValidation(result);
        setRowFilter("all");
        setPageIndex(0);
        setStage("review");
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "The roster could not be validated.",
        );
      } finally {
        setBusy(null);
      }
    },
    [academicYear, batchId, file, session.institution_id, uploadKey],
  );

  const confirm = useCallback(async () => {
    if (batchId === null || !batchKey) return;
    setBusy("confirming");
    setError(null);
    try {
      const result = await confirmIntakeBatch(batchId, batchKey);
      setConfirmation(result);
      setStage("done");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "The batch could not be confirmed.",
      );
    } finally {
      setBusy(null);
    }
  }, [batchId, batchKey]);

  const startOver = useCallback(() => {
    setFile(null);
    setStage("select");
    setBusy(null);
    setError(null);
    setBatchId(null);
    setBatchKey(null);
    setValidation(null);
    setConfirmation(null);
    setRowFilter("all");
    setPageIndex(0);
    setUploadKey(newKey());
    if (fileInput.current) fileInput.current.value = "";
  }, []);

  const invalidRows = validation?.invalid_rows ?? 0;
  const canConfirm =
    validation !== null && invalidRows === 0 && validation.valid_rows > 0;

  const filteredRows = useMemo(() => {
    const rows = validation?.rows ?? [];
    if (rowFilter === "valid") return rows.filter((row) => row.valid);
    if (rowFilter === "invalid") return rows.filter((row) => !row.valid);
    return rows;
  }, [rowFilter, validation]);

  const pageCount = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  const safePage = Math.min(pageIndex, pageCount - 1);
  const pageRows = filteredRows.slice(
    safePage * PAGE_SIZE,
    (safePage + 1) * PAGE_SIZE,
  );

  const download = (withErrors: boolean) => {
    downloadCsv(
      withErrors
        ? "pramaan-sample-roster-with-errors.csv"
        : "pramaan-sample-roster.csv",
      buildSampleRoster(academicYear, withErrors),
    );
  };

  const filterCounts: [RowFilter, string, number][] = validation
    ? [
        ["all", "All", validation.rows.length],
        ["valid", "Valid", validation.valid_rows],
        ["invalid", "Needs correction", validation.invalid_rows],
      ]
    : [];

  return (
    <section
      id="roster-intake"
      aria-labelledby="roster-intake-heading"
      className="space-y-5"
    >
      <PageHeader
        title={<span id="roster-intake-heading">Roster Intake</span>}
        description="Upload a roster CSV, review every row, then confirm it explicitly."
        action={
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => download(false)}>
              <DownloadIcon />
              Download sample CSV
            </Button>
            <Button variant="secondary" onClick={() => download(true)}>
              Download sample with errors
            </Button>
          </div>
        }
      />

      <p className="text-xs text-ink-soft">
        Signed in as <span className="font-medium text-ink">{session.username}</span> for{" "}
        <span className="font-medium text-ink">
          {session.institution_name || `institution ${session.institution_id}`}
        </span>
        . The institution comes from your session.
      </p>

      <ol className="flex flex-wrap gap-x-4 gap-y-1 text-xs" aria-label="Intake steps">
        {STEPS.map((step, index) => {
          const currentIndex = STEPS.findIndex((entry) => entry.id === stage);
          const isCurrent = step.id === stage;
          const isDone = currentIndex > index;
          return (
            <li
              key={step.id}
              aria-current={isCurrent ? "step" : undefined}
              className={
                "inline-flex items-center gap-1.5 " +
                (isCurrent
                  ? "font-semibold text-forest-800"
                  : isDone
                    ? "text-ink-soft"
                    : "text-ink-mute")
              }
            >
              <span
                aria-hidden="true"
                className={
                  "flex h-4 w-4 items-center justify-center rounded-full border text-[10px] " +
                  (isCurrent
                    ? "border-forest-700 bg-forest-700 text-white"
                    : "border-line-strong")
                }
              >
                {index + 1}
              </span>
              {step.label}
            </li>
          );
        })}
      </ol>

      {error ? (
        <Alert
          title="That step did not complete"
          action={
            <Button variant="secondary" onClick={() => setError(null)}>
              Dismiss
            </Button>
          }
        >
          {error}
        </Alert>
      ) : null}

      {stage === "select" ? (
        <div className="rounded-md border border-line bg-surface p-4">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-base font-semibold text-ink">Upload roster CSV</h2>
            <DemoTag label="Synthetic data only" />
          </div>
          <p className="mt-1 text-sm text-ink-soft">
            Required columns: <code>local_ref</code>, <code>course_code</code>,{" "}
            <code>academic_year</code>, <code>seat_category</code>,{" "}
            <code>entry_level</code>, <code>identity_status</code>. Optional{" "}
            <code>apaar_id</code> is never stored.
          </p>

          <div className="mt-4 max-w-xs">
            <label
              htmlFor="academic-year"
              className="block text-xs font-medium text-ink"
            >
              Academic year for this batch
            </label>
            <input
              id="academic-year"
              type="text"
              value={academicYear}
              onChange={(event) => setAcademicYear(event.target.value)}
              disabled={batchId !== null}
              aria-describedby="academic-year-help"
              className="mt-1 w-full rounded-md border border-line-strong bg-surface px-2.5 py-1.5 text-sm text-ink disabled:bg-canvas disabled:text-ink-mute"
            />
            <p id="academic-year-help" className="mt-1 text-xs text-ink-mute">
              Every row&apos;s <code>academic_year</code> must match this value.
              {batchId !== null ? " Fixed once a batch exists." : ""}
            </p>
          </div>

          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              const dropped = event.dataTransfer.files?.[0];
              if (dropped) acceptFile(dropped);
            }}
            className={
              "mt-4 rounded-md border border-dashed px-4 py-6 text-center " +
              (dragging
                ? "border-forest-500 bg-forest-50"
                : "border-line-strong bg-canvas")
            }
          >
            <label
              htmlFor="roster-file"
              className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-line-strong bg-surface px-3 py-2 text-sm font-medium text-ink hover:bg-canvas"
            >
              <UploadIcon />
              Choose a CSV file
            </label>
            <input
              ref={fileInput}
              id="roster-file"
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => {
                const selected = event.target.files?.[0];
                if (selected) acceptFile(selected);
              }}
              className="sr-only"
            />
            <p className="mt-2 text-xs text-ink-mute">
              CSV, UTF-8, up to {MAX_SIZE_MB} MB. Drag and drop supported.
            </p>
          </div>

          {file ? (
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-md border border-line bg-canvas px-3 py-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-ink">{file.name}</p>
                <p className="text-xs text-ink-mute">
                  {Math.max(1, Math.round(file.size / 1024))} KB · batch year{" "}
                  {academicYear}
                </p>
              </div>
              <Button variant="secondary" onClick={startOver}>
                Clear
              </Button>
            </div>
          ) : null}

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button
              onClick={() => void runValidation(batchId !== null)}
              disabled={!file || busy !== null}
              disabledReason={
                !file ? "Choose a CSV file first" : "A request is in progress"
              }
            >
              <UploadIcon />
              {busy === "validating"
                ? "Validating…"
                : batchId !== null
                  ? "Validate this batch again"
                  : "Upload and validate"}
            </Button>
            {batchId !== null ? (
              <p className="text-xs text-ink-mute">
                Reusing batch #{batchId}; uploading again replaces its staged rows.
              </p>
            ) : null}
          </div>
        </div>
      ) : null}

      {stage === "review" && validation ? (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <StatCard
              label="Rows in file"
              value={formatCount(validation.total_rows)}
              hint={`Batch #${validation.batch_id}`}
            />
            <StatCard
              label="Valid rows"
              value={formatCount(validation.valid_rows)}
            />
            <StatCard
              label="Rows to correct"
              value={formatCount(validation.invalid_rows)}
              hint={
                validation.invalid_rows > 0 ? "Blocks confirmation" : "None"
              }
            />
            <StatCard
              label="Duplicate rows"
              value={formatCount(validation.duplicate_rows)}
              hint="Repeated reference or identical row"
            />
          </div>

          <section
            aria-labelledby="review-heading"
            className="rounded-md border border-line bg-surface"
          >
            <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div>
                <h2
                  id="review-heading"
                  className="text-base font-semibold text-ink"
                >
                  Row-level validation
                </h2>
                <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-ink-mute">
                  Batch #{validation.batch_id}
                  <StatusBadge state={validation.state} />
                </p>
              </div>
              <div role="group" aria-label="Filter rows" className="flex flex-wrap gap-1">
                {filterCounts.map(([id, label, count]) => (
                  <button
                    key={id}
                    type="button"
                    aria-pressed={rowFilter === id}
                    onClick={() => {
                      setRowFilter(id);
                      setPageIndex(0);
                    }}
                    className={
                      "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium " +
                      (rowFilter === id
                        ? "bg-forest-50 text-forest-800"
                        : "text-ink-soft hover:bg-canvas")
                    }
                  >
                    {label}
                    <span className="rounded-sm bg-canvas px-1 text-[10px] tabular-nums text-ink-mute">
                      {formatCount(count)}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="max-h-96 overflow-auto border-t border-line">
              <table className="min-w-full text-sm">
                <caption className="sr-only">
                  Every row of the uploaded roster with its validation state and the
                  reasons a row was rejected.
                </caption>
                <thead className="sticky top-0 bg-surface">
                  <tr className="text-left">
                    <th
                      scope="col"
                      className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute"
                    >
                      Row
                    </th>
                    <th
                      scope="col"
                      className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute"
                    >
                      Local reference
                    </th>
                    <th
                      scope="col"
                      className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute"
                    >
                      Result
                    </th>
                    <th
                      scope="col"
                      className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute"
                    >
                      What needs fixing
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {pageRows.map((row) => (
                    <tr
                      key={row.row_number}
                      className="border-t border-line align-top"
                    >
                      <td className="px-4 py-2 tabular-nums text-ink-soft">
                        {row.row_number}
                      </td>
                      <td className="px-4 py-2 font-mono text-xs text-ink">
                        {row.local_ref ?? "—"}
                      </td>
                      <td className="px-4 py-2">
                        <span
                          className={
                            "inline-block rounded-sm border px-2 py-0.5 text-xs font-medium " +
                            (row.valid
                              ? "border-forest-200 bg-forest-50 text-forest-800"
                              : "border-warning-100 bg-warning-50 text-warning-600")
                          }
                        >
                          {row.valid ? "Valid" : "Needs correction"}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-xs text-ink-soft">
                        {row.errors.length > 0 ? (
                          <ul className="list-disc space-y-0.5 pl-4">
                            {row.errors.map((message, index) => (
                              <li key={index}>{message}</li>
                            ))}
                          </ul>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                  {pageRows.length === 0 ? (
                    <tr className="border-t border-line">
                      <td
                        colSpan={4}
                        className="px-4 py-6 text-center text-sm text-ink-soft"
                      >
                        No rows match this filter.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-2 text-xs text-ink-mute">
              <p>
                Showing {filteredRows.length === 0 ? 0 : safePage * PAGE_SIZE + 1}–
                {Math.min((safePage + 1) * PAGE_SIZE, filteredRows.length)} of{" "}
                {formatCount(filteredRows.length)}{" "}
                {plural(filteredRows.length, "row")}
              </p>
              <div className="flex gap-1">
                <button
                  type="button"
                  onClick={() => setPageIndex(Math.max(0, safePage - 1))}
                  disabled={safePage === 0}
                  className="rounded border border-line-strong bg-surface px-2 py-0.5 font-medium text-ink disabled:cursor-not-allowed disabled:border-line disabled:bg-canvas disabled:text-ink-mute"
                >
                  Previous
                </button>
                <button
                  type="button"
                  onClick={() => setPageIndex(Math.min(pageCount - 1, safePage + 1))}
                  disabled={safePage >= pageCount - 1}
                  className="rounded border border-line-strong bg-surface px-2 py-0.5 font-medium text-ink disabled:cursor-not-allowed disabled:border-line disabled:bg-canvas disabled:text-ink-mute"
                >
                  Next
                </button>
              </div>
            </div>
          </section>

          {invalidRows > 0 ? (
            <Alert
              tone="warning"
              title={`${invalidRows} ${plural(
                invalidRows,
                "row needs",
                "rows need",
              )} correction`}
            >
              Correct the rows listed above and upload the file to this same batch.
              Nothing is submitted until every row validates.
            </Alert>
          ) : null}

          <div className="flex flex-wrap items-center gap-2">
            <Button
              onClick={() => void confirm()}
              disabled={!canConfirm || busy !== null}
              disabledReason={
                !canConfirm
                  ? "Every row must be valid before the batch can be confirmed"
                  : "A request is in progress"
              }
            >
              {busy === "confirming" ? "Confirming…" : "Confirm and submit"}
            </Button>
            <Button
              variant="secondary"
              onClick={() => void runValidation(true)}
              disabled={busy !== null}
              disabledReason="A request is in progress"
            >
              <RefreshIcon />
              Re-validate this batch
            </Button>
            <Button variant="secondary" onClick={startOver}>
              Choose another file
            </Button>
          </div>
          <p className="text-[11px] text-ink-mute">
            Prototype demonstration — synthetic data only. The validation rules are
            this repository&apos;s own column contract, not an official AICTE rule set.
          </p>
        </div>
      ) : null}

      {stage === "done" && confirmation ? (
        <div className="space-y-4">
          <Alert tone="success" title="Batch confirmed">
            Batch #{confirmation.batch_id} is{" "}
            <span className="font-medium">
              {batchStatus(confirmation.state).label}
            </span>{" "}
            with {formatCount(confirmation.persisted_count)} persisted{" "}
            {plural(confirmation.persisted_count, "row")}. Ready for reconciliation.
          </Alert>
          <div className="grid gap-3 sm:grid-cols-3">
            <StatCard
              label="Persisted rows"
              value={formatCount(confirmation.persisted_count)}
              hint="Committed by the confirmation step"
            />
            <StatCard
              label="Batch"
              value={`#${confirmation.batch_id}`}
              hint={academicYear}
            />
            <StatCard
              label="Next step"
              value="Reconciliation"
              hint="Compare against approved intake"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button href="#reconciliation">Go to Reconciliation</Button>
            <Button variant="secondary" onClick={startOver}>
              Intake another roster
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
