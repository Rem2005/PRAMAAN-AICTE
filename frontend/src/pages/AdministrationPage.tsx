import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Button,
  Dash,
  DemoTag,
  MetaList,
  PageHeader,
  StatusTag,
  type StatusTone,
} from "../components/ui";
import { RefreshIcon } from "../components/icons";
import {
  fetchPolicies,
  fetchSnapshots,
  type PolicyInfo,
  type SessionUser,
  type SnapshotInfo,
} from "../lib/api";
import { formatCount, formatDateTimeIST } from "../lib/format";

/**
 * Administration.
 *
 * Everything here is real: the session comes from the server, and the versioned
 * configuration is read from the existing reconciliation endpoints
 * (`/reconciliation/policies`, `/reconciliation/snapshots`). There is no
 * user-management API, so the account section states that plainly instead of
 * offering create/edit controls that cannot work.
 */

const ROLE_LABELS: Record<string, string> = {
  INSTITUTION_DATA_OPERATOR: "Institution Data Operator",
  NODAL_OFFICER: "Nodal Officer",
  IDENTITY_REVIEW_OFFICER: "Identity Review Officer",
  POLICY_AUTHOR: "Policy Author",
  POLICY_APPROVER: "Policy Approver",
  VERIFICATION_REQUESTER: "Verification Requester",
  AUDITOR: "Auditor",
  PLATFORM_ADMIN: "Platform Administrator",
};

const SNAPSHOT_TONES: Record<string, StatusTone> = {
  APPROVED: "success",
  DRAFT: "neutral",
  SUPERSEDED: "neutral",
};

const POLICY_TONES: Record<string, StatusTone> = {
  ACTIVE: "success",
  DRAFT: "warning",
};

const CAPABILITIES: { label: string; detail: string; tag: string; tone: StatusTone }[] = [
  {
    label: "Create an account",
    detail: "Provisioned from the command line; no user-management API exists.",
    tag: "CLI only",
    tone: "neutral",
  },
  {
    label: "Edit roles or deactivate an account",
    detail: "Not implemented in this prototype.",
    tag: "Not available",
    tone: "neutral",
  },
  {
    label: "Reset another user's password",
    detail: "Not implemented. Passwords are hashed and never returned by any endpoint.",
    tag: "Not available",
    tone: "neutral",
  },
  {
    label: "Session and device management",
    detail: "Only the current session can be ended, by signing out.",
    tag: "Not available",
    tone: "neutral",
  },
];

function roleLabel(role: string): string {
  return ROLE_LABELS[role] ?? role;
}

/** Join a string array stored inside a policy's rule JSON. */
function joinList(value: unknown): string {
  return Array.isArray(value)
    ? value.filter((entry) => typeof entry === "string").join(", ")
    : "";
}

export function AdministrationPage({ session }: { session: SessionUser }) {
  const [snapshots, setSnapshots] = useState<SnapshotInfo[]>([]);
  const [policies, setPolicies] = useState<PolicyInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [copied, setCopied] = useState<"idle" | "done" | "failed">("idle");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setForbidden(false);
    try {
      const [snapshotData, policyData] = await Promise.all([
        fetchSnapshots(),
        fetchPolicies(),
      ]);
      setSnapshots(snapshotData);
      setPolicies(policyData);
    } catch (err) {
      const status = (err as { status?: number }).status;
      // A role without batch read access is a permission state, not a failure.
      if (status === 403) {
        setForbidden(true);
      } else {
        setError(
          err instanceof Error
            ? err.message
            : "The versioned configuration could not be loaded.",
        );
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const activePolicy =
    policies.find((policy) => policy.status === "ACTIVE") ?? null;
  const approvedSnapshot =
    snapshots.find((snapshot) => snapshot.status === "APPROVED") ?? null;

  const provisioningCommand =
    `NEW_USER_PASSWORD='…' python -m app.cli create-user \\\n` +
    `  --username operator1 --institution ${session.institution_id} \\\n` +
    `  --role INSTITUTION_DATA_OPERATOR`;

  const copyCommand = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(provisioningCommand);
      setCopied("done");
    } catch {
      setCopied("failed");
    }
  }, [provisioningCommand]);

  return (
    <section
      id="administration"
      aria-labelledby="administration-heading"
      className="space-y-5"
    >
      <PageHeader
        title={<span id="administration-heading">Administration</span>}
        description="Your session, this institution's versioned configuration and account setup."
      />

      <section
        aria-labelledby="session-heading"
        className="rounded-md border border-line bg-surface"
      >
        <h2
          id="session-heading"
          className="border-b border-line px-4 py-3 text-base font-semibold text-ink"
        >
          Signed-in account
        </h2>
        <dl className="grid grid-cols-1 divide-y divide-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          <div className="px-4 py-3">
            <dt className="text-xs text-ink-mute">Username</dt>
            <dd className="mt-0.5 text-sm text-ink">{session.username || <Dash />}</dd>
          </div>
          <div className="min-w-0 px-4 py-3">
            <dt className="text-xs text-ink-mute">Roles</dt>
            <dd className="mt-0.5 flex flex-wrap gap-1">
              {session.roles.length === 0 ? (
                <Dash />
              ) : (
                session.roles.map((role) => (
                  <StatusTag key={role}>{roleLabel(role)}</StatusTag>
                ))
              )}
            </dd>
          </div>
          <div className="min-w-0 px-4 py-3">
            <dt className="text-xs text-ink-mute">Institution</dt>
            <dd className="mt-0.5 text-sm text-ink">
              {session.institution_name || <Dash />}
              <span className="ml-1.5 text-xs text-ink-mute">
                (id {session.institution_id})
              </span>
            </dd>
          </div>
        </dl>
        <p className="border-t border-line px-4 py-2 text-xs text-ink-mute">
          Roles and institution scope are read from the server-side session on every
          request.
        </p>
      </section>

      <section
        aria-labelledby="config-heading"
        className="rounded-md border border-line bg-surface"
      >
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 id="config-heading" className="text-base font-semibold text-ink">
              Versioned configuration
            </h2>
            <DemoTag label="Synthetic seed" />
          </div>
          <Button variant="secondary" onClick={() => void load()} disabled={loading}>
            <RefreshIcon />
            {loading ? "Refreshing…" : "Refresh"}
          </Button>
        </div>

        <div className="px-4 py-3">
          {loading ? (
            <div aria-hidden="true" className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {[0, 1].map((column) => (
                <div key={column} className="space-y-2">
                  <div className="h-3 w-24 rounded-sm bg-canvas" />
                  <div className="h-4 w-full rounded-sm bg-canvas" />
                  <div className="h-4 w-full rounded-sm bg-canvas" />
                  <div className="h-4 w-2/3 rounded-sm bg-canvas" />
                </div>
              ))}
              <p role="status" className="sr-only">
                Loading versioned configuration…
              </p>
            </div>
          ) : forbidden ? (
            <p className="text-sm text-ink-soft">
              Your role cannot read policy or intake-snapshot versions.
            </p>
          ) : error ? (
            <Alert
              title="Versioned configuration could not be loaded"
              action={
                <Button variant="secondary" onClick={() => void load()}>
                  Try again
                </Button>
              }
            >
              {error}
            </Alert>
          ) : !activePolicy && !approvedSnapshot ? (
            <EmptyConfiguration institutionId={session.institution_id} />
          ) : (
            <div className="grid grid-cols-1 gap-x-8 gap-y-4 md:grid-cols-2">
              <div className="min-w-0">
                <h3 className="text-xs font-medium text-ink-mute">Active policy</h3>
                {activePolicy ? (
                  <MetaList
                    items={[
                      {
                        label: "Version",
                        value: (
                          <>
                            v{activePolicy.version}
                            <span className="ml-1.5">
                              <StatusTag tone={POLICY_TONES[activePolicy.status] ?? "neutral"}>
                                {activePolicy.status}
                              </StatusTag>
                            </span>
                          </>
                        ),
                      },
                      { label: "Name", value: activePolicy.name },
                      {
                        label: "Activated",
                        value: activePolicy.activated_at ? (
                          `${formatDateTimeIST(activePolicy.activated_at)} IST`
                        ) : (
                          <Dash />
                        ),
                      },
                      {
                        label: "Compared fields",
                        value: joinList(activePolicy.rules.compare_fields) || <Dash />,
                      },
                      {
                        label: "Capacity check",
                        value: activePolicy.rules.check_capacity === true ? "On" : "Off",
                      },
                    ]}
                  />
                ) : (
                  <p className="mt-2 text-xs text-ink-soft">
                    No active policy package exists.
                  </p>
                )}
              </div>

              <div className="min-w-0">
                <h3 className="text-xs font-medium text-ink-mute">
                  Approved intake snapshot
                </h3>
                {approvedSnapshot ? (
                  <MetaList
                    items={[
                      {
                        label: "Version",
                        value: (
                          <>
                            v{approvedSnapshot.version}
                            <span className="ml-1.5">
                              <StatusTag
                                tone={SNAPSHOT_TONES[approvedSnapshot.status] ?? "neutral"}
                              >
                                {approvedSnapshot.status}
                              </StatusTag>
                            </span>
                          </>
                        ),
                      },
                      {
                        label: "Approved lines",
                        value: formatCount(approvedSnapshot.entry_count),
                      },
                      {
                        label: "Source",
                        value: approvedSnapshot.source_ref,
                      },
                      {
                        label: "Approved by",
                        value: approvedSnapshot.approved_by ?? <Dash />,
                      },
                      {
                        label: "Approved at",
                        value: approvedSnapshot.approved_at ? (
                          `${formatDateTimeIST(approvedSnapshot.approved_at)} IST`
                        ) : (
                          <Dash />
                        ),
                      },
                    ]}
                  />
                ) : (
                  <p className="mt-2 text-xs text-ink-soft">
                    No approved intake snapshot exists.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        <p className="border-t border-line px-4 py-2 text-xs text-ink-mute">
          These versions are the inputs reconciliation compares against. Seeded demo
          figures are synthetic, not an official intake record.
        </p>
      </section>

      <section
        aria-labelledby="accounts-heading"
        className="rounded-md border border-line bg-surface"
      >
        <h2
          id="accounts-heading"
          className="border-b border-line px-4 py-3 text-base font-semibold text-ink"
        >
          Accounts and roles
        </h2>

        <ul className="divide-y divide-line">
          {CAPABILITIES.map((capability) => (
            <li
              key={capability.label}
              className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5"
            >
              <div className="min-w-0">
                <p className="text-sm text-ink">{capability.label}</p>
                <p className="mt-0.5 text-xs text-ink-soft">{capability.detail}</p>
              </div>
              <StatusTag tone={capability.tone}>{capability.tag}</StatusTag>
            </li>
          ))}
        </ul>

        <div className="border-t border-line px-4 py-3">
          <p className="text-xs font-medium text-ink">Provisioning command</p>
          <div className="mt-1 flex items-stretch">
            <code className="min-w-0 flex-1 overflow-x-auto rounded-l-md border border-r-0 border-line-strong bg-canvas px-2.5 py-2 text-[11px] leading-relaxed whitespace-pre text-ink-soft">
              {provisioningCommand}
            </code>
            <button
              type="button"
              onClick={() => void copyCommand()}
              className="shrink-0 rounded-r-md border border-line-strong bg-surface px-3 text-xs font-medium text-ink hover:bg-canvas"
            >
              Copy
            </button>
          </div>
          <p aria-live="polite" className="mt-1 text-xs text-ink-mute">
            {copied === "done"
              ? "Copied to clipboard."
              : copied === "failed"
                ? "Copy is unavailable in this browser — select the command and copy it manually."
                : "The password is read from the environment; it is never passed on the command line or stored."}
          </p>
        </div>
      </section>

      <p className="text-[11px] text-ink-mute">
        Prototype — synthetic data only, and not an official government service.
      </p>
    </section>
  );
}

/** First run for an institution that has no snapshot or policy package yet. */
function EmptyConfiguration({ institutionId }: { institutionId: number }) {
  return (
    <div className="rounded-md border border-dashed border-line-strong px-4 py-5">
      <p className="text-sm font-medium text-ink">Nothing is configured yet</p>
      <p className="mt-1 max-w-2xl text-xs leading-relaxed text-ink-soft">
        This institution has no approved intake snapshot and no active policy package, so
        reconciliation has nothing to compare against. A platform administrator supplies
        both; for the demo, seed synthetic versions with:
      </p>
      <code className="mt-2 inline-block rounded-sm border border-line bg-canvas px-2 py-1 text-[11px] text-ink-soft">
        python -m app.cli seed-demo --institution {institutionId}
      </code>
    </div>
  );
}
