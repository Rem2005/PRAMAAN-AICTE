import { useState } from "react";
import { login, type SessionUser } from "../lib/api";

type LoginPageProps = {
  onSignedIn: (session: SessionUser) => void;
};

export function LoginPage({ onSignedIn }: LoginPageProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!username || !password) {
      setError("Enter a username and password.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const session = await login(username, password);
      onSignedIn(session);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Sign-in failed."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6">
          <p className="text-2xl font-semibold tracking-tight text-ink">
            PRAMAAN–AICTE
          </p>
          <p className="mt-1 text-xs leading-snug text-ink-mute">
            Prototype demonstration — not an official government service.
          </p>
        </div>        <div className="rounded-md border border-line bg-surface p-6">
          <h1 className="text-xl font-semibold tracking-tight text-ink">Sign in</h1>
          <p className="mt-1 text-sm text-ink-soft">
            Accounts are institution-scoped. Your role decides what you can do.
          </p>

          {error ? (
            <div
              role="alert"
              className="mt-4 rounded-md border border-error-100 bg-error-50 px-3 py-2.5 text-sm text-error-600"
            >
              {error}
            </div>
          ) : null}

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <div>
              <label
                htmlFor="username"
                className="block text-xs font-medium text-ink"
              >
                Username
              </label>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                aria-required="true"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="mt-1 w-full rounded-md border border-line-strong bg-surface px-3 py-2 text-sm text-ink"
                placeholder="operator1"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-xs font-medium text-ink"
              >
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                aria-required="true"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="mt-1 w-full rounded-md border border-line-strong bg-surface px-3 py-2 text-sm text-ink"
                placeholder="••••••••••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-md bg-forest-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-forest-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forest-700"
            >
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <p className="mt-4 text-xs text-ink-mute">
            No account? Provision one with{" "}
            <code className="font-medium text-ink-soft">
              python -m app.cli create-user
            </code>
            . Authentication is local to this prototype.
          </p>
        </div>
      </div>
    </div>
  );
}