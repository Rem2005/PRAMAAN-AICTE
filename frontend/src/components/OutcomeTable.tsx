import { useMemo, useState } from "react";
import type { ReconciliationOutcome } from "../lib/api";
import { formatCount } from "../lib/format";

const PAGE_SIZE = 25;

/** Human labels for the reconciliation outcome vocabulary. */
export const OUTCOME_LABELS: Record<string, string> = {
  MATCHED: "Matched",
  UNMATCHED: "No approved entry",
  FIELD_MISMATCH: "Field mismatch",
  AMBIGUOUS: "Ambiguous",
  DUPLICATE_CANDIDATE: "Duplicate candidate",
  INVALID_INPUT: "Invalid input",
  EXCLUDED_BY_POLICY: "Excluded by policy",
};

export function outcomeLabel(outcome: string): string {
  return OUTCOME_LABELS[outcome] ?? outcome;
}

/** Outcome is always text plus colour; `MATCHED` is the only clean state. */
export function outcomeClass(outcome: string): string {
  if (outcome === "MATCHED") {
    return "border-forest-200 bg-forest-50 text-forest-800";
  }
  if (outcome === "UNMATCHED" || outcome === "FIELD_MISMATCH") {
    return "border-warning-100 bg-warning-50 text-warning-600";
  }
  return "border-line-strong bg-canvas text-ink-soft";
}

export function OutcomeTable({
  outcomes,
  caption,
}: {
  outcomes: ReconciliationOutcome[];
  caption: string;
}) {
  const [filter, setFilter] = useState<string>("ALL");
  const [pageIndex, setPageIndex] = useState(0);

  const present = useMemo(() => {
    const counts = new Map<string, number>();
    outcomes.forEach((row) => {
      counts.set(row.outcome, (counts.get(row.outcome) ?? 0) + 1);
    });
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [outcomes]);

  const filtered = useMemo(
    () =>
      filter === "ALL"
        ? outcomes
        : outcomes.filter((row) => row.outcome === filter),
    [filter, outcomes],
  );

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(pageIndex, pageCount - 1);
  const pageRows = filtered.slice(
    safePage * PAGE_SIZE,
    (safePage + 1) * PAGE_SIZE,
  );

  return (
    <div>
      <div
        role="group"
        aria-label="Filter row outcomes"
        className="flex flex-wrap gap-1 border-b border-line px-4 py-2"
      >
        <button
          type="button"
          aria-pressed={filter === "ALL"}
          onClick={() => {
            setFilter("ALL");
            setPageIndex(0);
          }}
          className={
            "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium " +
            (filter === "ALL"
              ? "bg-forest-50 text-forest-800"
              : "text-ink-soft hover:bg-canvas")
          }
        >
          All rows
          <span className="rounded-sm bg-canvas px-1 text-[10px] tabular-nums text-ink-mute">
            {formatCount(outcomes.length)}
          </span>
        </button>
        {present.map(([outcome, count]) => (
          <button
            key={outcome}
            type="button"
            aria-pressed={filter === outcome}
            onClick={() => {
              setFilter(outcome);
              setPageIndex(0);
            }}
            className={
              "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium " +
              (filter === outcome
                ? "bg-forest-50 text-forest-800"
                : "text-ink-soft hover:bg-canvas")
            }
          >
            {outcomeLabel(outcome)}
            <span className="rounded-sm bg-canvas px-1 text-[10px] tabular-nums text-ink-mute">
              {formatCount(count)}
            </span>
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <caption className="sr-only">{caption}</caption>
          <thead>
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
                Outcome
              </th>
              <th
                scope="col"
                className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-mute"
              >
                Reason
              </th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row) => (
              <tr key={row.row_number} className="border-t border-line align-top">
                <td className="px-4 py-2 tabular-nums text-ink-soft">
                  {row.row_number}
                </td>
                <td className="px-4 py-2 font-mono text-xs text-ink">
                  {row.local_ref ?? "—"}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`inline-block whitespace-nowrap rounded-sm border px-2 py-0.5 text-xs font-medium ${outcomeClass(
                      row.outcome,
                    )}`}
                  >
                    {outcomeLabel(row.outcome)}
                  </span>
                </td>
                <td className="px-4 py-2 text-xs text-ink-soft">
                  {row.reasons.length > 0 ? (
                    <ul className="list-disc space-y-0.5 pl-4">
                      {row.reasons.map((reason, index) => (
                        <li key={index}>{reason}</li>
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
                <td colSpan={4} className="px-4 py-6 text-center text-sm text-ink-soft">
                  No rows match this filter.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-2 text-xs text-ink-mute">
        <p>
          Showing {filtered.length === 0 ? 0 : safePage * PAGE_SIZE + 1}–
          {Math.min((safePage + 1) * PAGE_SIZE, filtered.length)} of{" "}
          {formatCount(filtered.length)} rows
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
    </div>
  );
}
