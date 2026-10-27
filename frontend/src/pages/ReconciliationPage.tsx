import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  DemoTag,
  PageHeader,
  StatCard,
  StatusBadge,
} from "../components/ui";
import { OutcomeTable } from "../components/OutcomeTable";
import { RefreshIcon } from "../components/icons";
import {
  fetchPolicies,
  fetchReconciliationRun,
  fetchReconciliationRuns,
  fetchRosterBatches,
  fetchSnapshots,
  runReconciliation,
  type PolicyInfo,
  type ReconciliationRun,
  type ReconciliationRunDetail,
  type RosterBatchSummary,
  type SessionUser,
  type SnapshotInfo,
} from "../lib/api";
import { formatCount, formatDateTimeIST } from "../lib/format";

const RUN_ROLES = ["INSTITUTION_DATA_OPERATOR", "NODAL_OFFICER"];
const RECONCILABLE_STATES = ["VALIDATED", "SUBMITTED_FOR_REVIEW"];

const OUTCOME_CARDS: { key: string; label: string; hint: string; tone: "ok" | "warn" }[] = [
  { key: "MATCHED", label: "Matched", hint: "Agrees with approved intake", tone: "ok" },
  { key: "UNMATCHED", label: "No approved entry", hint: "No matching approved line", tone: "warn" },
  { key: "FIELD_MISMATCH", label: "Field mismatch", hint: "Compared field differs", tone: "warn" },
  { key: "DUPLICATE_CANDIDATE", label: "Duplicate candidate", hint: "Repeats an earlier row", tone: "warn" },
];

function countOf(run: ReconciliationRunDetail, key: string): number {
  return run.outcome_counts[key] ?? 0;
}

/**
 * Reconciliation: choose a validated batch plus the approved snapshot and
 * policy versions to compare against, run it, and inspect every outcome.
 *
 * Runs are produced by the backend from persisted rows. This screen never
 * fabricates a result, and a run is evidence for review — not a fraud finding.
 */
export function ReconciliationPage({ session }: { session: SessionUser }) {
  const [batches, setBatches] = useState<RosterBatchSummary[]>([]);
  const [snapshots, setSnapshots] = useState<SnapshotInfo[]>([]);
  const [policies, setPolicies] = useState<PolicyInfo[]>([]);
  const [refsLoading, setRefsLoading] = useState(true);
  const [refsError, setRefsError] = useState<string | null>(null);

  const [batchId, setBatchId] = useState<number | null>(null);
  const [snapshotId, setSnapshotId] = useState<number | null>(null);
  const [policyId, setPolicyId] = useState<number | null>(null);

  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [run, setRun] = useState<ReconciliationRunDetail | null>(null);

  const [history, setHistory] = useState<ReconciliationRun[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  const canRun = session.roles.some((role) => RUN_ROLES.includes(role));

  const loadReferences = useCallback(async () => {
    setRefsLoading(true);
    setRefsError(null);
    try {
      const [batchData, snapshotData, policyData] = await Promise.all([
        fetchRosterBatches(),
        fetchSnapshots(),
        fetchPolicies(),
      ]);
      const reconcilable = batchData.batches.filter((batch) =>
        RECONCILABLE_STATES.includes(batch.state),
      );
      setBatches(reconcilable);
      setSnapshots(snapshotData);
      setPolicies(policyData);

      const approved = snapshotData.filter((snapshot) => snapshot.status === "APPROVED");
      const active = policyData.filter((policy) => policy.status === "ACTIVE");

      setBatchId((current) =>
        current !== null && reconcilable.some((batch) => batch.batch_id === current)
          ? current
          : (reconcilable[0]?.batch_id ?? null),
      );
      setSnapshotId((current) =>
        current !== null && approved.some((item) => item.snapshot_id === current)
          ? current
          : (approved[0]?.snapshot_id ?? null),
      );
      setPolicyId((current) =>
        current !== null && active.some((item) => item.policy_id === current)
          ? current
          : (active[0]?.policy_id ?? null),
      );
    } catch (err) {
      setRefsError(
        err instanceof Error ? err.message : "Reference data could not be loaded.",
      );
    } finally {
      setRefsLoading(false);
    }
  }, []);

  const loadHistory = useCallback(async (targetBatch: number) => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const runs = await fetchReconciliationRuns(targetBatch);
      setHistory(runs);
    } catch (err) {
      setHistory([]);
      setHistoryError(
        err instanceof Error ? err.message : "Reconciliation history could not be loaded.",
      );
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadReferences();
  }, [loadReferences]);

  useEffect(() => {
    if (batchId !== null) void loadHistory(batchId);
  }, [batchId, loadHistory]);

  const startRun = useCallback(async () => {
    if (batchId === null || snapshotId === null || policyId === null) return;
    setRunning(true);
    setRunError(null);
    try {
      const result = await runReconciliation(batchId, { snapshotId, policyId });
      setRun(result);
      await loadHistory(batchId);
    } catch (err) {
      setRun(null);
      setRunError(
        err instanceof Error ? err.message : "The reconciliation run did not complete.",
      );
    } finally {
      setRunning(false);
    }
  }, [batchId, loadHistory, policyId, snapshotId]);

  const viewRun = useCallback(async (runId: number) => {
    setRunError(null);
    try {
      const detail = await fetchReconciliationRun(runId);
      setRun(detail);
    } catch (err) {
      setRunError(
        err instanceof Error ? err.message : "That run could not be loaded.",
      );
    }
  }, []);

  const selectedBatch = useMemo(
    () => batches.find((batch) => batch.batch_id === batchId) ?? null,
    [batchId, batches],
  );
  const selectedSnapshot = useMemo(
    () => snapshots.find((snapshot) => snapshot.snapshot_id === snapshotId) ?? null,
    [snapshotId, snapshots],
  );
  const selectedPolicy = useMemo(
    () => policies.find((policy) => policy.policy_id === policyId) ?? null,
    [policies, policyId],
  );

  const canStart =
    canRun &&
    batchId !== null &&
    snapshotId !== null &&
    policyId !== null &&
    !running;

  const startDisabledReason = !canRun
    ? "Requires the Institution Data Operator or Nodal Officer role"
    : batchId === null
      ? "No validated batch is available"
      : snapshotId === null
        ? "No approved intake snapshot is available"
        : policyId === null
          ? "No active policy package is available"
          : "A run is already in progress";

  return (
    <section
      id="reconciliation"
      aria-labelledby="reconciliation-heading"
      className="space-y-5"
    >
      <PageHeader
        title={<span id="reconciliation-heading">Reconciliation</span>}
        description="Compare a validated batch against an approved intake snapshot and policy version. Each run is stored with its digest."
        action={
          <Button variant="secondary" onClick={() => void loadReferences()}>
            <RefreshIcon />
            Refresh
          </Button>
        }
      />

      {refsError ? (
        <Alert
          title="Reference data could not be loaded"
          action={
            <Button variant="secondary" onClick={() => void loadReferences()}>
              Try again
            </Button>
          }
        >
          {refsError}
        </Alert>
      ) : null}

      {refsLoading ? (
        <p role="status" className="text-sm text-ink-soft">
          Loading batches, snapshots and policies…
        </p>
      ) : null}

      {!refsLoading && !refsError ? (
        <>
          {batches.length === 0 ? (
            <Alert tone="info" title="No validated batch is ready">
              Upload and confirm a batch first.{" "}
              <a
                href="#roster-intake"
                className="font-medium underline underline-offset-2"
              >
                Go to Roster Intake
              </a>
              .
            </Alert>
          ) : null}

          {snapshots.length === 0 || policies.length === 0 ? (
            <Alert tone="warning" title="Reference data is missing">
              {snapshots.length === 0 ? "No intake snapshot" : "No policy package"}{" "}
              exists for this institution. For the demo, seed synthetic versions with:{" "}
              <code className="rounded-sm bg-surface px-1 py-0.5 text-[11px] text-ink">
                python -m app.cli seed-demo --institution {session.institution_id}
              </code>
            </Alert>
          ) : null}

          <div className="rounded-md border border-line bg-surface p-4">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-semibold text-ink">Run a reconciliation</h2>
              <DemoTag />
            </div>

            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <div>
                <label htmlFor="recon-batch" className="block text-xs font-medium text-ink">
                  Batch
                </label>
                <select
                  id="recon-batch"
                  value={batchId ?? ""}
                  onChange={(event) => {
                    const next = Number(event.target.value);
                    setBatchId(Number.isNaN(next) ? null : next);
                    setRun(null);
                  }}
                  disabled={batches.length === 0}
                  className="mt-1 w-full rounded-md border border-line-strong bg-surface px-2.5 py-1.5 text-sm text-ink disabled:bg-canvas disabled:text-ink-mute"
                >
                  {batches.length === 0 ? <option value="">None available</option> : null}
                  {batches.map((batch) => (
                    <option key={batch.batch_id} value={batch.batch_id}>
                      #{batch.batch_id} · {batch.source_filename ?? "no file"} ·{" "}
                      {batch.academic_year}
                    </option>
                  ))}
                </select>
                {selectedBatch ? (
                  <p className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-ink-mute">
                    {formatCount(selectedBatch.valid_rows)} valid rows ·{" "}
                    <StatusBadge state={selectedBatch.state} />
                  </p>
                ) : null}
              </div>

              <div>
                <label
                  htmlFor="recon-snapshot"
                  className="block text-xs font-medium text-ink"
                >
                  Approved intake snapshot
                </label>
                <select
                  id="recon-snapshot"
                  value={snapshotId ?? ""}
                  onChange={(event) => {
                    const next = Number(event.target.value);
                    setSnapshotId(Number.isNaN(next) ? null : next);
                    setRun(null);
                  }}
                  disabled={snapshots.length === 0}
                  className="mt-1 w-full rounded-md border border-line-strong bg-surface px-2.5 py-1.5 text-sm text-ink disabled:bg-canvas disabled:text-ink-mute"
                >
                  {snapshots.length === 0 ? <option value="">None available</option> : null}
                  {snapshots.map((snapshot) => (
                    <option key={snapshot.snapshot_id} value={snapshot.snapshot_id}>
                      v{snapshot.version} · {snapshot.status} · {snapshot.entry_count}{" "}
                      lines
                    </option>
                  ))}
                </select>
                {selectedSnapshot ? (
                  <p className="mt-1 break-words text-xs text-ink-mute">
                    Source: {selectedSnapshot.source_ref}
                  </p>
                ) : null}
              </div>

              <div>
                <label htmlFor="recon-policy" className="block text-xs font-medium text-ink">
                  Policy package
                </label>
                <select
                  id="recon-policy"
                  value={policyId ?? ""}
                  onChange={(event) => {
                    const next = Number(event.target.value);
                    setPolicyId(Number.isNaN(next) ? null : next);
                    setRun(null);
                  }}
                  disabled={policies.length === 0}
                  className="mt-1 w-full rounded-md border border-line-strong bg-surface px-2.5 py-1.5 text-sm text-ink disabled:bg-canvas disabled:text-ink-mute"
                >
                  {policies.length === 0 ? <option value="">None available</option> : null}
                  {policies.map((policy) => (
                    <option key={policy.policy_id} value={policy.policy_id}>
                      v{policy.version} · {policy.name} · {policy.status}
                    </option>
                  ))}
                </select>
                {selectedPolicy ? (
                  <p className="mt-1 break-words text-xs text-ink-mute">
                    Link:{" "}
                    {String(
                      (selectedPolicy.rules.link_fields as string[] | undefined)?.join(
                        ", ",
                      ) ?? "—",
                    )}
                  </p>
                ) : null}
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Button
                onClick={() => void startRun()}
                disabled={!canStart}
                disabledReason={startDisabledReason}
              >
                {running ? "Running…" : "Run reconciliation"}
              </Button>
              <p className="text-xs text-ink-mute">
                {canRun
                  ? "Each run is appended to history; earlier runs stay unchanged."
                  : "Your role can view runs but not start one."}
              </p>
            </div>
          </div>

          {runError ? (
            <Alert
              title="That run did not complete"
              action={
                <Button variant="secondary" onClick={() => void startRun()}>
                  Try again
                </Button>
              }
            >
              {runError}
            </Alert>
          ) : null}
        </>
      ) : null}

      {run ? (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Rows reconciled"
              value={formatCount(run.row_count)}
              hint={`Run ${run.run_number} · ${run.status}`}
            />
            {OUTCOME_CARDS.map((card) => (
              <StatCard
                key={card.key}
                label={card.label}
                value={formatCount(countOf(run, card.key))}
                hint={card.hint}
              />
            ))}
          </div>

          <section className="rounded-md border border-line bg-surface px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-ink">
                Run {run.run_number} summary
              </h2>
              <span className="text-xs text-ink-mute">
                Batch #{run.batch_id} ·{" "}
                {run.source_filename ?? "no source file"}
              </span>
            </div>
            <dl className="mt-2 grid gap-x-6 gap-y-1 text-xs sm:grid-cols-2">
              <div className="flex gap-2">
                <dt className="w-40 shrink-0 text-ink-mute">Snapshot</dt>
                <dd className="text-ink">
                  #{run.snapshot_id} (v{run.snapshot_version})
                </dd>
              </div>
              <div className="flex gap-2">
                <dt className="w-40 shrink-0 text-ink-mute">Policy</dt>
                <dd className="text-ink">#{run.policy_id} (v{run.policy_version})</dd>
              </div>
              <div className="flex gap-2">
                <dt className="w-40 shrink-0 text-ink-mute">Triggered by</dt>
                <dd className="text-ink">{run.triggered_by}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="w-40 shrink-0 text-ink-mute">Finished (IST)</dt>
                <dd className="text-ink">
                  {run.finished_at ? formatDateTimeIST(run.finished_at) : "—"}
                </dd>
              </div>
              <div className="flex gap-2 sm:col-span-2">
                <dt className="w-40 shrink-0 text-ink-mute">Capacity comparison</dt>
                <dd className="text-ink">{run.totals ?? "—"}</dd>
              </div>
              <div className="flex min-w-0 gap-2 sm:col-span-2">
                <dt className="w-40 shrink-0 text-ink-mute">Output digest</dt>
                <dd className="break-all font-mono text-[11px] text-ink-soft">
                  {run.digest ?? "—"}
                </dd>
              </div>
            </dl>
            <p className="mt-2 text-[11px] text-ink-mute">
              An outcome is a comparison result for review — not a penalty or a fraud
              finding.
            </p>
          </section>

          <section
            aria-labelledby="outcomes-heading"
            className="rounded-md border border-line bg-surface"
          >
            <h2
              id="outcomes-heading"
              className="px-4 py-3 text-base font-semibold text-ink"
            >
              Row-level outcomes
            </h2>
            <OutcomeTable
              outcomes={run.outcomes}
              caption={`Row-level reconciliation outcomes for run ${run.run_number} of batch ${run.batch_id}.`}
            />
          </section>
        </div>
      ) : null}

      <section
        aria-labelledby="history-heading"
        className="rounded-md border border-line bg-surface"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
          <h2 id="history-heading" className="text-base font-semibold text-ink">
            Run history
            {selectedBatch ? (
              <span className="ml-2 text-xs font-normal text-ink-mute">
                batch #{selectedBatch.batch_id}
              </span>
            ) : null}
          </h2>
          {batchId !== null ? (
            <Button variant="secondary" onClick={() => void loadHistory(batchId)}>
              <RefreshIcon />
              Reload
            </Button>
          ) : null}
        </div>

        {historyError ? (
          <div className="border-t border-line p-4">
            <Alert tone="error" title="History could not be loaded">
              {historyError}
            </Alert>
          </div>
        ) : historyLoading ? (
          <p role="status" className="border-t border-line px-4 py-4 text-sm text-ink-soft">
            Loading run history…
          </p>
        ) : history.length === 0 ? (
          <p className="border-t border-line px-4 py-4 text-sm text-ink-soft">
            No reconciliation has been run for this batch yet.
          </p>
        ) : (
          <div className="overflow-x-auto border-t border-line">
            <table className="min-w-full text-sm">
              <caption className="sr-only">
                Previous reconciliation runs for the selected batch.
              </caption>
              <thead>
                <tr className="text-left">
                  <th scope="col" className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute">
                    Run
                  </th>
                  <th scope="col" className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute">
                    Started (IST)
                  </th>
                  <th scope="col" className="hidden px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute sm:table-cell">
                    Versions
                  </th>
                  <th scope="col" className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute">
                    Matched
                  </th>
                  <th scope="col" className="hidden px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute lg:table-cell">
                    Digest
                  </th>
                  <th scope="col" className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {history.map((entry) => (
                  <tr key={entry.run_id} className="border-t border-line">
                    <td className="px-4 py-2 text-ink">
                      #{entry.run_number}
                      <span className="ml-1.5 text-xs text-ink-mute">
                        {entry.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-ink-soft">
                      {entry.started_at ? formatDateTimeIST(entry.started_at) : "—"}
                    </td>
                    <td className="hidden px-4 py-2 text-ink-soft sm:table-cell">
                      snapshot v{entry.snapshot_version} · policy v
                      {entry.policy_version}
                    </td>
                    <td className="px-4 py-2 tabular-nums text-ink">
                      {formatCount(
                        (entry.outcome_counts.MATCHED ?? 0) as number,
                      )}
                      <span className="text-xs text-ink-mute">
                        {" "}
                        / {formatCount(entry.row_count)}
                      </span>
                    </td>
                    <td className="hidden px-4 py-2 font-mono text-[11px] text-ink-mute lg:table-cell">
                      {entry.digest ? `${entry.digest.slice(0, 12)}…` : "—"}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        type="button"
                        onClick={() => void viewRun(entry.run_id)}
                        className="rounded border border-line-strong bg-surface px-2 py-0.5 text-xs font-medium text-ink hover:bg-canvas"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p className="text-[11px] text-ink-mute">
        Prototype demonstration — synthetic data only. Reconciliation runs inside this
        application; no external agency system is contacted.
      </p>
    </section>
  );
}
