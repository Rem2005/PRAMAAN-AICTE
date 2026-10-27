import type { ReactNode } from "react";
import type { SessionUser } from "../lib/api";
import {
  AdminIcon,
  DashboardIcon,
  IdentityIcon,
  IntakeIcon,
  ReconcileIcon,
  ReportIcon,
  VerificationIcon,
} from "./icons";

type NavItem = {
  label: string;
  href?: string;
  available: boolean;
  reason?: string;
  icon: ReactNode;
};

const INTAKE_ROLES = ["INSTITUTION_DATA_OPERATOR", "NODAL_OFFICER"];

const ROLE_LABELS: Record<string, string> = {
  INSTITUTION_DATA_OPERATOR: "Institution Data Operator",
  NODAL_OFFICER: "Nodal Officer",
  AUDITOR: "Auditor",
  ADMINISTRATOR: "Administrator",
};

const PAGE_TITLES: Record<string, string> = {
  dashboard: "Dashboard",
  "roster-intake": "Roster Intake",
  reconciliation: "Reconciliation",
  "identity-review": "Identity Review",
  "verification-requests": "Verification Requests",
  "reports-audit": "Reports / Audit",
  administration: "Administration",
};

function buildNav(session: SessionUser): NavItem[] {
  const canSeeIntake = session.roles.some((role) => INTAKE_ROLES.includes(role));
  return [
    { label: "Dashboard", href: "#dashboard", available: true, icon: <DashboardIcon /> },
    {
      label: "Roster Intake",
      href: "#roster-intake",
      available: canSeeIntake,
      reason: "Requires the Institution Data Operator or Nodal Officer role",
      icon: <IntakeIcon />,
    },
    {
      label: "Reconciliation",
      href: "#reconciliation",
      available: true,
      icon: <ReconcileIcon />,
    },
    {
      label: "Identity Review",
      href: "#identity-review",
      available: true,
      icon: <IdentityIcon />,
    },
    {
      label: "Verification Requests",
      href: "#verification-requests",
      available: true,
      icon: <VerificationIcon />,
    },
    {
      label: "Reports / Audit",
      href: "#reports-audit",
      available: true,
      icon: <ReportIcon />,
    },
    {
      label: "Administration",
      href: "#administration",
      available: true,
      icon: <AdminIcon />,
    },
  ];
}

const NAV_ITEM_BASE =
  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors";
const NAV_ITEM_ACTIVE = "bg-forest-50 font-semibold text-forest-800";
const NAV_ITEM_IDLE = "font-medium text-ink-soft hover:bg-forest-50 hover:text-forest-800";
const NAV_ITEM_DISABLED = "cursor-not-allowed font-medium text-ink-mute";

function renderNavItem(item: NavItem, activePage: string) {
  const isActive = item.href ? item.href === `#${activePage}` : false;

  if (item.available && item.href) {
    return (
      <a
        href={item.href}
        aria-current={isActive ? "page" : undefined}
        className={`${NAV_ITEM_BASE} ${isActive ? NAV_ITEM_ACTIVE : NAV_ITEM_IDLE}`}
      >
        {item.icon}
        <span>{item.label}</span>
      </a>
    );
  }

  return (
    <button
      type="button"
      disabled
      title={item.reason}
      className={`${NAV_ITEM_BASE} w-full ${NAV_ITEM_DISABLED}`}
    >
      {item.icon}
      <span>{item.label}</span>
      <span className="sr-only"> — unavailable: {item.reason}</span>
    </button>
  );
}

function initialsFor(name: string): string {
  const parts = name.split(/[^A-Za-z0-9]+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function roleLabel(roles: string[]): string {
  const known = roles.map((role) => ROLE_LABELS[role]).filter(Boolean);
  return known.length > 0 ? known[0] : "No assigned role";
}

type AppShellProps = {
  children: ReactNode;
  session: SessionUser;
  activePage: string;
  onSignOut: () => void;
};

export function AppShell({ children, session, activePage, onSignOut }: AppShellProps) {
  const nav = buildNav(session);
  const pageTitle = PAGE_TITLES[activePage] ?? "Dashboard";
  const institution =
    session.institution_name || `Institution ${session.institution_id}`;

  return (
    <div className="flex min-h-screen bg-canvas text-ink">
      {/* Persistent desktop sidebar */}
      <aside
        className="hidden w-56 shrink-0 flex-col border-r border-line bg-surface lg:flex"
        aria-label="Sidebar"
        role="complementary"
      >
        <div className="border-b border-line px-4 py-4">
          <div className="flex items-center gap-2.5">
            <span
              aria-hidden="true"
              className="flex h-7 w-7 items-center justify-center rounded-md bg-forest-700 text-xs font-semibold text-white"
            >
              PA
            </span>
            <span className="text-sm font-semibold tracking-tight text-ink">
              PRAMAAN–AICTE
            </span>
          </div>
          <p className="mt-2 text-[11px] leading-snug text-ink-mute">
            Roster intake and reconciliation
          </p>
        </div>

        <nav aria-label="Primary" className="flex-1 px-2 py-4">
          <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-ink-mute">
            Workspace
          </p>
          <ul className="space-y-0.5">
            {nav.map((item) => (
              <li key={item.label}>{renderNavItem(item, activePage)}</li>
            ))}
          </ul>
        </nav>

        <div className="space-y-2 border-t border-line px-4 py-3">
          <span className="inline-block rounded-sm border border-line-strong px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-ink-mute">
            Prototype
          </span>
          <p className="text-[11px] leading-snug text-ink-mute">
            Not an official government service.
          </p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-line bg-surface">
          <div className="flex items-center justify-between gap-3 px-4 py-3 lg:px-8">
            <p className="truncate text-sm font-medium text-ink">{pageTitle}</p>

            <div className="flex min-w-0 items-center gap-3">
              <p className="hidden max-w-[16rem] truncate text-xs text-ink-soft sm:block">
                {institution}
              </p>
              <div className="flex items-center gap-2.5 border-l border-line pl-3">
                <span
                  aria-hidden="true"
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-forest-50 text-[11px] font-semibold text-forest-800"
                >
                  {initialsFor(session.username)}
                </span>
                <div className="hidden min-w-0 sm:block">
                  <p className="truncate text-xs font-medium text-ink">{session.username}</p>
                  <p className="truncate text-[11px] text-ink-mute">
                    {roleLabel(session.roles)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={onSignOut}
                  className="rounded-md border border-line-strong bg-surface px-2.5 py-1 text-xs font-medium text-ink hover:bg-canvas"
                >
                  Sign out
                </button>
              </div>
            </div>
          </div>

          {/* Narrow screens: same navigation in a disclosure */}
          <details className="border-t border-line px-4 py-2 lg:hidden">
            <summary className="cursor-pointer rounded px-1 py-1 text-sm font-medium text-ink">
              Menu
            </summary>
            <nav aria-label="Menu" className="py-2">
              <ul className="space-y-0.5">
                {nav.map((item) => (
                  <li key={item.label}>{renderNavItem(item, activePage)}</li>
                ))}
              </ul>
            </nav>
          </details>
        </header>

        <main
          id="main-content"
          className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 lg:px-8"
        >
          {children}
        </main>

        <footer className="border-t border-line bg-surface px-4 py-3 text-[11px] text-ink-mute lg:px-8">
          Prototype with synthetic demonstration data only — no real student records,
          official identifiers, or live government integrations.
        </footer>
      </div>
    </div>
  );
}
