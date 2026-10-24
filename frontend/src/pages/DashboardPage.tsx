import { useEffect, useState } from "react";
import { checkHealth } from "../lib/api";

type Health = { status: "ok" } | { status: "error" };

export function DashboardPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    checkHealth().then((result) => {
      if (cancelled) return;
      setHealth(result);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section id="dashboard" aria-labelledby="dashboard-heading">
      <nav aria-label="Breadcrumb">
        <ol className="text-xs text-neutral-600">
          <li>
            <a
              href="#"
              className="underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy-900"
            >
              Home
            </a>
          </li>
          <li aria-current="page">Dashboard</li>
        </ol>
      </nav>
      <h1 id="dashboard-heading" className="text-2xl font-semibold text-navy-900">Dashboard</h1>
      <p className="mt-2 text-sm text-neutral-700">PRAMAAN–AICTE prototype dashboard.</p>
      {loading ? (
        <p className="mt-4" role="status">
          Checking service status…
        </p>
      ) : null}
      {health?.status === "ok" ? (
        <p className="mt-4">Service status: Operational</p>
      ) : null}
      {health?.status === "error" ? (
        <p className="mt-4" role="alert">
          Service status: Unreachable
        </p>
      ) : null}
      <div className="mt-6 rounded border border-neutral-200 bg-white p-4 text-sm text-neutral-800">
        <h2 className="text-base font-semibold text-navy-900">Current prototype scope</h2>
        <p className="mt-2">
          Backend foundation, synthetic fixtures, and migration baseline are implemented. Roster intake, reconciliation, identity
          matching, and verification workflows are not yet implemented in this milestone.
        </p>
      </div>
    </section>
  );
}
