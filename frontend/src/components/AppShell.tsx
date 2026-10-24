import type { ReactNode } from "react";

type NavItem = {
  label: string;
  href?: string;
  available: boolean;
};

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "#dashboard", available: true },
  { label: "Roster Intake", available: false },
  { label: "Reconciliation", available: false },
  { label: "Identity Review", available: false },
  { label: "Verification Requests", available: false },
  { label: "Reports / Audit", available: false },
  { label: "Administration", available: false },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-neutral-50 font-sans text-navy-900">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-3">
          <div>
            <p className="text-lg font-semibold tracking-tight text-navy-900">PRAMAAN–AICTE</p>
            <p className="text-xs text-neutral-600">Prototype demonstration — not an official government service.</p>
          </div>
          <span className="rounded-sm border border-neutral-300 px-2 py-1 text-xs text-navy-900">Prototype</span>
        </div>
      </header>
      <nav aria-label="Primary" className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap gap-1 px-4 py-2">
          {NAV_ITEMS.map((item) =>
            item.available && item.href ? (
              <a
                key={item.label}
                href={item.href}
                className="rounded px-3 py-1.5 text-sm font-medium text-navy-900 hover:bg-neutral-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy-900"
              >
                {item.label}
              </a>
            ) : (
              <button
                key={item.label}
                type="button"
                disabled
                title="Not available in this milestone"
                className="rounded px-3 py-1.5 text-sm font-medium text-neutral-400"
              >
                {item.label}
              </button>
            ),
          )}
        </div>
      </nav>
      <main id="main-content" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        {children}
      </main>
    </div>
  );
}
