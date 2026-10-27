import { EmptyState, PageHeader, StatusTag } from "../components/ui";
import { SearchIcon } from "../components/icons";

/**
 * Verification Requests.
 *
 * No request can be raised: there is no request API, no purpose-limitation
 * schema and no adapter to any external system (docs/TODO.md, Phase 5, and
 * AGENTS.md directive 13). The screen therefore offers no create action — a
 * button that pretended to send a request would be a fabricated success state.
 *
 * The flow below is a labelled preview of the proposed lifecycle from
 * `docs/data-model.md` (`VerificationRequest` and `DisclosureReceipt`) and
 * PRD FR-08. It records nothing.
 */

const REQUEST_COLUMNS = [
  { label: "Reference", className: "" },
  { label: "Purpose", className: "" },
  { label: "Claims requested", className: "hidden md:table-cell" },
  { label: "Consent / authority", className: "hidden sm:table-cell" },
  { label: "Status", className: "" },
];

const PROPOSED_FLOW = [
  {
    title: "Request raised",
    detail: "Requester, purpose, claims and expiry recorded.",
  },
  {
    title: "Authority checked",
    detail: "Consent and authority references verified before disclosure.",
  },
  {
    title: "Minimum claims",
    detail: "Only the requested claim set is disclosed.",
  },
  {
    title: "Receipt recorded",
    detail: "The disclosure is stored for audit.",
  },
];

export function VerificationRequestsPage() {
  return (
    <section
      id="verification-requests"
      aria-labelledby="verification-heading"
      className="space-y-5"
    >
      <PageHeader
        title={<span id="verification-heading">Verification Requests</span>}
        description="Purpose-limited requests for a minimum set of claims."
        action={<StatusTag>Not connected</StatusTag>}
      />

      <section
        aria-labelledby="requests-heading"
        className="rounded-md border border-line bg-surface"
      >
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-4 py-3">
          <div className="min-w-0">
            <h2 id="requests-heading" className="text-base font-semibold text-ink">
              Requests
            </h2>
            <p className="mt-0.5 text-xs text-ink-mute">0 requests</p>
          </div>

          <div className="flex flex-wrap items-end gap-2">
            <div>
              <label
                htmlFor="request-search"
                className="block text-xs font-medium text-ink"
              >
                Search
              </label>
              <div className="relative mt-1">
                <SearchIcon className="pointer-events-none absolute top-2 left-2.5 text-ink-mute" />
                <input
                  id="request-search"
                  type="search"
                  disabled
                  placeholder="Reference or purpose"
                  aria-describedby="requests-help"
                  className="w-full rounded-md border border-line-strong bg-canvas py-1.5 pr-3 pl-9 text-sm text-ink-mute placeholder:text-ink-mute disabled:cursor-not-allowed sm:w-52"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="request-status"
                className="block text-xs font-medium text-ink"
              >
                Status
              </label>
              <select
                id="request-status"
                disabled
                aria-describedby="requests-help"
                className="mt-1 rounded-md border border-line-strong bg-canvas px-2.5 py-1.5 text-sm text-ink-mute disabled:cursor-not-allowed"
              >
                <option>All statuses</option>
              </select>
            </div>
          </div>
        </div>

        <p
          id="requests-help"
          className="border-b border-line px-4 py-2 text-xs text-ink-soft"
        >
          Search and filters are disabled until a request API is connected.
        </p>

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <caption className="sr-only">
              Verification requests raised by this institution. The list is empty because
              no request API is connected.
            </caption>
            <thead>
              <tr className="text-left">
                {REQUEST_COLUMNS.map((column) => (
                  <th
                    key={column.label}
                    scope="col"
                    className={`px-4 py-2 text-[11px] font-semibold tracking-wider text-ink-mute uppercase ${column.className}`}
                  >
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-line">
                <td colSpan={REQUEST_COLUMNS.length} className="px-4 py-5">
                  <EmptyState title="No requests can be raised yet">
                    A request needs the request API, a purpose-limitation schema and
                    identity adapters. None of the three exists, so nothing is sent to any
                    external system.
                  </EmptyState>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section
        aria-labelledby="flow-heading"
        className="rounded-md border border-line bg-surface"
      >
        <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-3">
          <h2 id="flow-heading" className="text-base font-semibold text-ink">
            Proposed request flow
          </h2>
          <StatusTag>Preview</StatusTag>
        </div>

        <ol className="grid gap-4 px-4 py-4 md:grid-cols-4">
          {PROPOSED_FLOW.map((step, index) => (
            <li key={step.title} className="min-w-0">
              <p className="text-sm font-medium text-ink">
                {/* The arrow marks a step that follows another, so the first has none. */}
                {index > 0 ? (
                  <span
                    aria-hidden="true"
                    className="mr-1.5 hidden text-ink-mute md:inline"
                  >
                    →
                  </span>
                ) : null}
                {step.title}
              </p>
              <p className="mt-0.5 text-xs leading-relaxed text-ink-soft">{step.detail}</p>
            </li>
          ))}
        </ol>

        <p className="border-t border-line px-4 py-2 text-xs text-ink-mute">
          Preview only. No AICTE, APAAR/ABC or DigiLocker integration is connected, and
          this flow stores no records.
        </p>
      </section>
    </section>
  );
}
