import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Button, PageHeader, StatCard } from "../components/ui";
import { RefreshIcon, SearchIcon } from "../components/icons";
import { outcomeLabel } from "../components/OutcomeTable";
import {
  fetchReconciliationRun,
  fetchReconciliationRuns,
  type ReconciliationRun,
} from "../lib/api";
import { formatCount, formatDateTimeIST } from "../lib/format";
import { downloadCsv } from "../lib/sampleRoster";

function csvField(value: unknown): string {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function runsToCsv(runs: ReconciliationRun[]): string {
  const header = [
    "run_id",
    "batch_id",
    "source_filename",
    "academic_year",
    "run_number",
    "status",
    "started_at",
    "snapshot_version",
    "policy_version",
    "row_count",
    "matched",
    "digest",
  ];
  const lines = [header.join(",")];
  runs.forEach((run) => {
    lines.push(
      [
        run.run_id,
        run.batch_id,
        run.source_filename,
        run.academic_year,
        run.run_number,
        run.status,
        run.started_at,
        run.snapshot_version,
        run.policy_version,
        run.row_count,
        run.outcome_counts.MATCHED ?? 0,
        run.digest,
      ]
        .map(csvField)
        .join(","),
    );
  });
  return `${lines.join("\n")}\n`;
}

/**
 * Reports / Audit.
 *
 * Everything on this page is derived from reconciliation runs the backend
 * actually recorded. There is no general audit-event log in this prototype
 * yet, and the page says so rather than presenting an empty table as complete.
 */
export function ReportsPage() {
  const [runs, setRuns] = useState<ReconciliationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [exporting, setExporting] = useState<number | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReconciliationRuns();
      setRuns(data);
    } catch (err) {
      setRuns([]);
      setError(
        err instanceof Error ? err.message : "Reconciliation reports could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return runs;
    return runs.filter((run) => {
      const haystack = [
        String(run.run_id),
        String(run.batch_id),
        String(run.run_number),
        run.source_filename ?? "",
        run.academic_year ?? "",
        run.triggered_by,
        run.status,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [query, runs]);

  const batchesCovered = new Set(runs.map((run) => run.batch_id)).size;
  const matchedAcrossRuns = runs.reduce(
    (total, run) => total + (run.outcome_counts.MATCHED ?? 0),
    0,
  );
  const lastRun = runs[0] ?? null;

  const exportRun = useCallback(async (runId: number) => {
    setExporting(runId);
    setExportError(null);
    try {
      const detail = await fetchReconciliationRun(runId);
      const header = ["row_number", "local_ref", "outcome", "reasons"];
      const lines = [header.join(",")];
      detail.outcomes.forEach((outcome) => {
        lines.push(
          [
            outcome.row_number,
            outcome.local_ref,
            outcomeLabel(outcome.outcome),
            outcome.reasons.join("; "),
          ]
            .map(csvField)
            .join(","),
        );
      });
      downloadCsv(
        `pramaan-reconciliation-batch${detail.batch_id}-run${detail.run_number}.csv`,
        `${lines.join("\n")}\n`,
      );
    } catch (err) {
      setExportError(
        err instanceof Error ? err.message : "The row outcomes could not be exported.",
      );
    } finally {
      setExporting(null);
    }
  }, []);

  return (
    <section id="reports-audit" aria-labelledby="reports-heading" className="space-y-5">
      <PageHeader
        title={<span id="reports-heading">Reports and audit trail</span>}
        description="Recorded reconciliation runs, their versions and output digests."
        action={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              onClick={() => void load()}
            >
              <RefreshIcon />
              Refresh
            </Button>
            <Button
              onClick={() => downloadCsv("pramaan-reconciliation-runs.csv", runsToCsv(filtered))}
              disabled={filtered.length === 0}
              disabledReason="There are no recorded runs to export"
            >
              Export run summary (CSV)
            </Button>
          </div>
        }
      />

      <p className="text-xs text-ink-soft">
        Reconciliation evidence only. A general audit-event log is not implemented.
      </p>

      {error ? (
        <Alert
          title="Reports could not be loaded"
          action={
            <Button variant="secondary" onClick={() => void load()}>
              Try again
            </Button>
          }
        >
          {error}
        </Alert>
      ) : null}

      {exportError ? (
        <Alert
          title="Export did not complete"
          action={
            <Button variant="secondary" onClick={() => setExportError(null)}>
              Dismiss
            </Button>
          }
        >
          {exportError}
        </Alert>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard
          label="Recorded runs"
          value={loading ? "—" : formatCount(runs.length)}
          hint={`Across ${formatCount(batchesCovered)} ${batchesCovered === 1 ? "batch" : "batches"}`}
        />
        <StatCard
          label="Matched rows (all runs)"
          value={loading ? "—" : formatCount(matchedAcrossRuns)}
          hint="Summed across every recorded run"
        />
        <StatCard
          label="Most recent run"
          value={
            loading
              ? "—"
              : lastRun?.started_at
                ? formatDateTimeIST(lastRun.started_at)
                : "None"
          }
          hint={lastRun ? `Batch #${lastRun.batch_id} · ${lastRun.status}` : "No runs yet"}
        />
      </div>

      <section className="rounded-md border border-line bg-surface">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
          <h2 className="text-base font-semibold text-ink">Reconciliation runs</h2>
          <div className="relative w-full sm:w-64">
            <label htmlFor="report-search" className="sr-only">
              Search runs by batch, file name or run number
            </label>
            <SearchIcon className="pointer-events-none absolute left-2.5 top-2.5 text-ink-mute" />
            <input
              id="report-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search batch, file or run"
              className="w-full rounded-md border border-line-strong bg-surface py-1.5 pl-9 pr-3 text-sm text-ink placeholder:text-ink-mute"
            />
          </div>
        </div>

        {loading ? (
          <p role="status" className="border-t border-line px-4 py-4 text-sm text-ink-soft">
            Loading recorded runs…
          </p>
        ) : filtered.length === 0 ? (
          <p className="border-t border-line px-4 py-6 text-sm text-ink-soft">
            {runs.length === 0 ? (
              <>
                No reconciliation has been recorded yet.{" "}
                <a
                  href="#reconciliation"
                  className="font-medium text-forest-700 underline underline-offset-2"
                >
                  Run one from Reconciliation.
                </a>
              </>
            ) : (
              "No runs match this search."
            )}
          </p>
        ) : (
          <div className="overflow-x-auto border-t border-line">
            <table className="min-w-full text-sm">
              <caption className="sr-only">
                Every recorded reconciliation run, newest first, with its input
                versions and a row-level export action.
              </caption>
              <thead>
                <tr className="text-left">
                  <th scope="col" className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute">
                    Batch
                  </th>
                  <th scope="col" className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute">
                    Run
                  </th>
                  <th scope="col" className="hidden px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute sm:table-cell">
                    Started (IST)
                  </th>
                  <th scope="col" className="hidden px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute md:table-cell">
                    Versions
                  </th>
                  <th scope="col" className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute">
                    Rows / matched
                  </th>
                  <th scope="col" className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute">
                    <span className="sr-only">Export</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((run) => (
                  <tr key={run.run_id} className="border-t border-line">
                    <td className="px-4 py-2">
                      <p className="text-ink">#{run.batch_id}</p>
                      <p className="text-xs text-ink-mute">
                        {run.source_filename ?? "no source file"}
                      </p>
                    </td>
                    <td className="px-4 py-2 text-ink">
                      #{run.run_number}
                      <span className="ml-1.5 text-xs text-ink-mute">{run.status}</span>
                    </td>
                    <td className="hidden px-4 py-2 text-ink-soft sm:table-cell">
                      {run.started_at ? formatDateTimeIST(run.started_at) : "—"}
                    </td>
                    <td className="hidden px-4 py-2 text-xs text-ink-soft md:table-cell">
                      snapshot v{run.snapshot_version} · policy v{run.policy_version}
                    </td>
                    <td className="px-4 py-2 tabular-nums text-ink">
                      {formatCount(run.row_count)}
                      <span className="text-xs text-ink-mute">
                        {" "}
                        / {formatCount(run.outcome_counts.MATCHED ?? 0)}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        type="button"
                        onClick={() => void exportRun(run.run_id)}
                        disabled={exporting === run.run_id}
                        className="rounded border border-line-strong bg-surface px-2 py-0.5 text-xs font-medium text-ink hover:bg-canvas disabled:cursor-not-allowed disabled:text-ink-mute"
                      >
                        {exporting === run.run_id ? "Preparing…" : "Outcomes CSV"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="rounded-md border border-line bg-surface px-4 py-3 text-xs text-ink-soft">
        <p className="font-medium text-ink">Not implemented</p>
        <ul className="mt-1 list-disc space-y-0.5 pl-4">
          <li>Audit-event log (actor, action, object, correlation ID).</li>
          <li>Signed or tamper-evident report packages.</li>
          <li>External or official reporting submission.</li>
        </ul>
      </div>
    </section>
  );
}
