"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

// Sign-in for the protected area. The form posts to /api/login and on success
// lands on /admin with a refresh so the server gate re-reads the new session.
export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [pending, setPending] = useState(false);
  const router = useRouter();

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(false);
    setPending(true);
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    setPending(false);
    if (response.ok) {
      router.push("/admin");
      router.refresh();
    } else {
      setError(true);
    }
  }

  return (
    <div className="quiet-enter w-full max-w-sm">
      <h1 className="text-[clamp(2rem,5vw,2.75rem)] font-medium leading-[1.05] tracking-[-0.02em] text-ink">
        Anmelden
      </h1>
      <p className="mt-3 leading-relaxed text-muted">
        Der geschützte Bereich liegt hinter diesem Login.
      </p>

      <form onSubmit={onSubmit} className="mt-10 space-y-5" noValidate>
        <div className="space-y-2">
          <label
            htmlFor="password"
            className="block text-xs uppercase tracking-[0.14em] text-muted"
          >
            Passwort
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            aria-invalid={error}
            aria-describedby={error ? "password-error" : undefined}
            className={`w-full rounded-md border bg-surface px-4 py-2.5 text-ink transition-colors placeholder:text-muted-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent/60 ${
              error ? "border-accent" : "border-line hover:border-muted-2"
            }`}
          />
          {error ? (
            <p
              id="password-error"
              role="alert"
              className="text-sm font-medium leading-relaxed text-ink"
            >
              Anmeldung fehlgeschlagen. Bitte prüfen Sie das Passwort.
            </p>
          ) : null}
        </div>

        <button
          type="submit"
          disabled={pending}
          aria-busy={pending}
          className="quiet-press w-full rounded-md border border-muted-2/50 px-6 py-2.5 text-sm uppercase tracking-[0.14em] text-ink transition-colors hover:border-accent hover:text-accent focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60 disabled:opacity-50"
        >
          {pending ? "Wird geprüft" : "Login"}
        </button>
      </form>
    </div>
  );
}
