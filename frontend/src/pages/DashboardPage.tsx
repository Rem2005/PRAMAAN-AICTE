import { useCallback, useEffect, useMemo, useState } from "react";
import { Button, DemoTag, PageHeader, StatCard, StatusBadge } from "../components/ui";
import { RefreshIcon, SearchIcon, UploadIcon } from "../components/icons";
import {
  fetchRosterBatches,
  type RosterBatchList,
  type RosterBatchSummary,
  type SessionUser,
} from "../lib/api";
import { formatCount, formatDateIST, formatDateTimeIST, formatTimeIST } from "../lib/format";

const PAGE_SIZE = 6;
const OPERATOR_ROLE = "INSTITUTION_DATA_OPERATOR";

type TabId = "all" | "review" | "processing" | "ready";

const TABS: { id: TabId; label: string; matches: (batch: RosterBatchSummary) => boolean }[] = [
  { id: "all", label: "All batches", matches: () => true },
  {
    id: "review",
    label: "Needs review",
    matches: (batch) => batch.state === "VALIDATION_FAILED",
  },
  {
    id: "processing",
    label: "Processing",
    matches: (batch) => ["CREATED", "UPLOADED", "VALIDATING"].includes(batch.state),
  },
  {
    id: "ready",
    label: "Ready",
    matches: (batch) => ["VALIDATED", "SUBMITTED_FOR_REVIEW"].includes(batch.state),
  },
];

function pluralize(count: number, singular: string, plural: string): string {
  return count === 1 ? singular : plural;
}

function matchesQuery(batch: RosterBatchSummary, query: string): boolean {
  if (!query) return true;
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  const batchId = String(batch.batch_id);
  return (
    (batch.source_filename ?? "").toLowerCase().includes(needle) ||
    batchId.includes(needle.replace(/^#/, "")) ||
    batch.academic_year.toLowerCase().includes(needle)
  );
}

/**
 * Institution dashboard.
 *
 * Every number on this screen is derived from `GET /api/v1/batches`, which is
 * scoped server-side to the signed-in institution. There are no placeholder
 * metrics: an empty institution shows zeros and an explicit empty state.
 */
export function DashboardPage({ session }: { session: SessionUser }) {
  const [data, setData] = useState<RosterBatchList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabId>("all");
  const [query, setQuery] = useState("");
  const [pageIndex, setPageIndex] = useState(0);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchRosterBatches();
      setData(result);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      // Keep any previously loaded data visible; only the banner reports the
      // refresh failure. Clearing it would replace real counts with zeros.
      setError(err instanceof Error ? err.message : "The batch list could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setPageIndex(0);
  }, [tab, query]);

  const batches = data?.batches ?? [];
  const totals = data?.totals;
  // Both of these states can be reconciled (see backend RECONCILABLE_STATES),
  // so both count as "ready" here. Counting only VALIDATED would drop a batch
  // from the card the moment it was confirmed.
  const readyCount = batches.filter((batch) =>
    ["VALIDATED", "SUBMITTED_FOR_REVIEW"].includes(batch.state),
  ).length;
  const batchesWithErrors = batches.filter((batch) => batch.invalid_rows > 0).length;
  const canUpload = session.roles.includes(OPERATOR_ROLE);

  const visible = useMemo(() => {
    const activeTab = TABS.find((entry) => entry.id === tab) ?? TABS[0];
    return batches.filter(
      (batch) => activeTab.matches(batch) && matchesQuery(batch, query),
    );
  }, [batches, tab, query]);

  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const safePageIndex = Math.min(pageIndex, pageCount - 1);
  const pageStart = safePageIndex * PAGE_SIZE;
  const pageRows = visible.slice(pageStart, pageStart + PAGE_SIZE);
  const showingFrom = visible.length === 0 ? 0 : pageStart + 1;
  const showingTo = Math.min(pageStart + PAGE_SIZE, visible.length);

  return (
    <section id="dashboard" aria-labelledby="dashboard-heading" className="space-y-5">
      <PageHeader
        title={<span id="dashboard-heading">Welcome back, {session.username}</span>}
        description="Roster intake status for your institution."
        action={
          canUpload ? (
            <Button href="#roster-intake">
              <UploadIcon />
              Upload roster
            </Button>
          ) : (
            <Button disabled disabledReason="Requires the Institution Data Operator role">
              <UploadIcon />
              Upload roster
            </Button>
          )
        }
      />

      {error ? (
        <div
          role="alert"
          className="flex flex-wrap items-start justify-between gap-3 rounded-md border border-error-100 bg-error-50 px-4 py-3 text-sm text-error-600"
        >
          <div className="min-w-0">
            <p className="font-medium">Could not load batches</p>
            <p className="mt-0.5">{error}</p>
          </div>
          <button
            type="button"
            onClick={() => void load()}
            className="shrink-0 rounded-md border border-error-600 bg-surface px-2.5 py-1 text-xs font-medium text-error-600"
          >
            Try again
          </button>
        </div>
      ) : null}

      {loading && !data ? (
        <p role="status" className="text-sm text-ink-soft">
          Loading roster batches…
        </p>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard
          label="Validated rows"
          value={totals ? formatCount(totals.valid_rows) : "—"}
          hint={`Across ${formatCount(totals?.batches ?? 0)} ${pluralize(
            totals?.batches ?? 0,
            "batch",
            "batches",
          )}`}
        />
        <StatCard
          label="Batches ready"
          value={totals ? `${formatCount(readyCount)} of ${formatCount(totals.batches)}` : "—"}
          hint="Ready for reconciliation"
        />
        <StatCard
          label="Rows needing correction"
          value={totals ? formatCount(totals.invalid_rows) : "—"}
          hint={
            batchesWithErrors > 0
              ? `Across ${formatCount(batchesWithErrors)} ${pluralize(
                  batchesWithErrors,
                  "batch",
                  "batches",
                )}`
              : "No row errors recorded"
          }
        />
      </div>

      <section
        aria-labelledby="recent-batches-heading"
        className="rounded-md border border-line bg-surface"
      >
        <div className="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 id="recent-batches-heading" className="text-base font-semibold text-ink">
                Recent roster batches
              </h2>
              <DemoTag />
            </div>
            <p className="mt-0.5 text-xs text-ink-mute">
              {formatCount(totals?.batches ?? 0)}{" "}
              {pluralize(totals?.batches ?? 0, "batch", "batches")} ·{" "}
              {formatCount(totals?.total_rows ?? 0)} staged rows
            </p>
          </div>

          <div className="relative w-full sm:w-64">
            <label htmlFor="batch-search" className="sr-only">
              Search by file name or batch ID
            </label>
            <SearchIcon className="pointer-events-none absolute left-2.5 top-2.5 text-ink-mute" />
            <input
              id="batch-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by file name or batch ID"
              className="w-full rounded-md border border-line-strong bg-surface py-1.5 pl-9 pr-3 text-sm text-ink placeholder:text-ink-mute"
            />
          </div>
        </div>

        <div className="border-y border-line px-4">
          <div
            role="group"
            aria-label="Filter batches by status"
            className="flex flex-wrap gap-1 py-2"
          >
            {TABS.map((entry) => {
              const count = batches.filter(entry.matches).length;
              const isActive = entry.id === tab;
              return (
                <button
                  key={entry.id}
                  type="button"
                  aria-pressed={isActive}
                  onClick={() => setTab(entry.id)}
                  className={
                    "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors " +
                    (isActive ? "bg-forest-50 text-forest-800" : "text-ink-soft hover:bg-canvas")
                  }
                >
                  {entry.label}
                  <span className="rounded-sm bg-canvas px-1 text-[10px] tabular-nums text-ink-mute">
                    {formatCount(count)}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <caption className="sr-only">
              Roster batches for your institution, with uploaded date, record counts and
              current status.
            </caption>
            <thead>
              <tr className="text-left">
                <th
                  scope="col"
                  className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute"
                >
                  Roster file
                </th>
                <th
                  scope="col"
                  className="hidden px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute sm:table-cell"
                >
                  Uploaded
                </th>
                <th
                  scope="col"
                  className="hidden px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute sm:table-cell"
                >
                  Records
                </th>
                <th
                  scope="col"
                  className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute"
                >
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((batch) => (
                <tr key={batch.batch_id} className="border-t border-line">
                  <td className="px-4 py-3">
                    <p className="break-words font-medium text-ink">
                      {batch.source_filename ?? "No file uploaded yet"}
                    </p>
                    <p className="mt-0.5 text-xs text-ink-mute">
                      Batch #{batch.batch_id} · {batch.academic_year}
                    </p>
                    {/* Narrow screens keep the status column visible by
                        folding the uploaded/record detail into this cell. */}
                    <p className="mt-0.5 text-xs text-ink-mute sm:hidden">
                      {formatDateIST(batch.created_at)} · {formatCount(batch.total_rows)}{" "}
                      records
                      {batch.invalid_rows > 0
                        ? ` · ${formatCount(batch.invalid_rows)} invalid`
                        : ""}
                    </p>
                  </td>
                  <td className="hidden px-4 py-3 sm:table-cell">
                    <p className="text-ink">{formatDateIST(batch.created_at)}</p>
                    <p className="mt-0.5 text-xs text-ink-mute">
                      {formatTimeIST(batch.created_at)} IST · {batch.uploader_ref}
                    </p>
                  </td>
                  <td className="hidden px-4 py-3 sm:table-cell">
                    <p className="tabular-nums text-ink">{formatCount(batch.total_rows)}</p>
                    {batch.invalid_rows > 0 ? (
                      <p className="mt-0.5 text-xs text-warning-600">
                        {formatCount(batch.invalid_rows)} invalid
                      </p>
                    ) : null}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge state={batch.state} />
                  </td>
                </tr>
              ))}

              {!loading && pageRows.length === 0 ? (
                <tr className="border-t border-line">
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-ink-soft">
                    {batches.length === 0 ? (
                      <>
                        No batches yet.{" "}
                        {canUpload ? (
                          <a
                            href="#roster-intake"
                            className="font-medium text-forest-700 underline underline-offset-2"
                          >
                            Upload a roster to begin.
                          </a>
                        ) : (
                          "A roster uploader will need to add one."
                        )}
                      </>
                    ) : (
                      "No batches match this filter."
                    )}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-2.5 text-xs text-ink-mute">
          <div className="flex items-center gap-3">
            <p>
              Showing {showingFrom}–{showingTo} of {formatCount(visible.length)}{" "}
              {pluralize(visible.length, "batch", "batches")}
            </p>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setPageIndex((current) => Math.max(0, current - 1))}
                disabled={safePageIndex === 0}
                className="rounded border border-line-strong bg-surface px-2 py-0.5 font-medium text-ink disabled:cursor-not-allowed disabled:border-line disabled:bg-canvas disabled:text-ink-mute"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => setPageIndex((current) => Math.min(pageCount - 1, current + 1))}
                disabled={safePageIndex >= pageCount - 1}
                className="rounded border border-line-strong bg-surface px-2 py-0.5 font-medium text-ink disabled:cursor-not-allowed disabled:border-line disabled:bg-canvas disabled:text-ink-mute"
              >
                Next
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <p>
              {lastUpdated ? `Updated ${formatDateTimeIST(lastUpdated)} IST` : "Not updated yet"}
            </p>
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading}
              className="inline-flex items-center gap-1 rounded border border-line-strong bg-surface px-2 py-0.5 font-medium text-ink hover:bg-canvas disabled:cursor-not-allowed disabled:text-ink-mute"
            >
              <RefreshIcon className="h-3.5 w-3.5" />
              {loading ? "Refreshing…" : "Refresh"}
            </button>
          </div>
        </div>
      </section>

      <p className="text-[11px] text-ink-mute">
        Prototype demonstration — synthetic data only, not an official government
        service.
      </p>
    </section>
  );
}
