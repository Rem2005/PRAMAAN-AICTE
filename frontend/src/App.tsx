import { useCallback, useEffect, useState } from "react";
import { AppShell } from "./components/AppShell";
import { Alert, PageHeader } from "./components/ui";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { RosterIntakePage } from "./pages/RosterIntakePage";
import { ReconciliationPage } from "./pages/ReconciliationPage";
import { ReportsPage } from "./pages/ReportsPage";
import { AdministrationPage } from "./pages/AdministrationPage";
import { IdentityReviewPage } from "./pages/IdentityReviewPage";
import { VerificationRequestsPage } from "./pages/VerificationRequestsPage";
import { ANONYMOUS_SESSION, fetchSession, logout, type SessionUser } from "./lib/api";

const PAGES = [
  "dashboard",
  "roster-intake",
  "reconciliation",
  "identity-review",
  "verification-requests",
  "reports-audit",
  "administration",
] as const;

type Page = (typeof PAGES)[number];

const INTAKE_ROLES = ["INSTITUTION_DATA_OPERATOR", "NODAL_OFFICER"];

function pageFromHash(): Page {
  const hash = window.location.hash.replace("#", "");
  return (PAGES as readonly string[]).includes(hash) ? (hash as Page) : "dashboard";
}

function RestrictedPage({ reason }: { reason: string }) {
  return (
    <section className="space-y-4">
      <PageHeader title="Not available for your role" />
      <Alert tone="warning" title="This screen requires another role">
        {reason}
      </Alert>
    </section>
  );
}

export default function App() {
  // null means "still asking the server"; the distinction matters so we do
  // not flash the sign-in page to an already-authenticated user.
  const [session, setSession] = useState<SessionUser | null>(null);
  const [page, setPage] = useState<Page>(pageFromHash);

  useEffect(() => {
    let cancelled = false;
    fetchSession().then((result) => {
      if (!cancelled) setSession(result);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const handleHashChange = () => setPage(pageFromHash());
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const handleSignOut = useCallback(async () => {
    await logout();
    setSession(ANONYMOUS_SESSION);
  }, []);

  if (session === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas">
        <p role="status" className="text-sm text-ink-soft">
          Checking session…
        </p>
      </div>
    );
  }

  if (!session.authenticated) {
    return <LoginPage onSignedIn={setSession} />;
  }

  const canIntake = session.roles.some((role) => INTAKE_ROLES.includes(role));

  return (
    <AppShell session={session} activePage={page} onSignOut={handleSignOut}>
      {page === "dashboard" ? <DashboardPage session={session} /> : null}
      {page === "roster-intake" ? (
        canIntake ? (
          <RosterIntakePage session={session} />
        ) : (
          <RestrictedPage reason="Roster Intake requires the Institution Data Operator or Nodal Officer role. Your session does not include either." />
        )
      ) : null}
      {page === "reconciliation" ? (
        <ReconciliationPage session={session} />
      ) : null}
      {page === "identity-review" ? <IdentityReviewPage /> : null}
      {page === "verification-requests" ? <VerificationRequestsPage /> : null}
      {page === "reports-audit" ? <ReportsPage /> : null}
      {page === "administration" ? (
        <AdministrationPage session={session} />
      ) : null}
    </AppShell>
  );
}
