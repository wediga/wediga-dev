"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

// Sign-in for the protected area. The password posts to /api/login; when the
// second factor is active the backend asks for a code, so the form switches to
// a code step that posts to /api/login/totp. On success it lands on /admin with
// a refresh so the server gate re-reads the new session.
type Step = "password" | "code";

export default function LoginPage() {
  const [step, setStep] = useState<Step>("password");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState(false);
  const [pending, setPending] = useState(false);
  const router = useRouter();

  function enterAdmin() {
    router.push("/admin");
    router.refresh();
  }

  async function onPasswordSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(false);
    setPending(true);
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    setPending(false);
    if (!response.ok) {
      setError(true);
      return;
    }
    const data = (await response.json()) as { totp_required?: boolean };
    if (data.totp_required) {
      setStep("code");
    } else {
      enterAdmin();
    }
  }

  async function onCodeSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(false);
    setPending(true);
    const response = await fetch("/api/login/totp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    setPending(false);
    if (response.ok) {
      enterAdmin();
    } else {
      setError(true);
    }
  }

  const inputClass = (invalid: boolean) =>
    `w-full rounded-md border bg-surface px-4 py-2.5 text-ink transition-colors placeholder:text-muted-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent/60 ${
      invalid ? "border-accent" : "border-line hover:border-muted-2"
    }`;

  return (
    <div className="quiet-enter w-full max-w-sm">
      <h1 className="text-[clamp(2rem,5vw,2.75rem)] font-medium leading-[1.05] tracking-[-0.02em] text-ink">
        Anmelden
      </h1>
      <p className="mt-3 leading-relaxed text-muted">
        {step === "password"
          ? "Der geschützte Bereich liegt hinter diesem Login."
          : "Geben Sie den Code aus Ihrer Authenticator-App ein."}
      </p>

      {step === "password" ? (
        <form onSubmit={onPasswordSubmit} className="mt-10 space-y-5" noValidate>
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
              aria-describedby={error ? "login-error" : undefined}
              className={inputClass(error)}
            />
            {error ? (
              <p
                id="login-error"
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
      ) : (
        <form onSubmit={onCodeSubmit} className="mt-10 space-y-5" noValidate>
          <div className="space-y-2">
            <label
              htmlFor="code"
              className="block text-xs uppercase tracking-[0.14em] text-muted"
            >
              Code
            </label>
            <input
              id="code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]*"
              maxLength={6}
              value={code}
              onChange={(event) =>
                setCode(event.target.value.replace(/\D/g, ""))
              }
              autoFocus
              aria-invalid={error}
              aria-describedby={error ? "login-error" : undefined}
              className={inputClass(error)}
            />
            {error ? (
              <p
                id="login-error"
                role="alert"
                className="text-sm font-medium leading-relaxed text-ink"
              >
                Der Code ist ungültig oder abgelaufen. Bitte erneut versuchen.
              </p>
            ) : null}
          </div>

          <button
            type="submit"
            disabled={pending}
            aria-busy={pending}
            className="quiet-press w-full rounded-md border border-muted-2/50 px-6 py-2.5 text-sm uppercase tracking-[0.14em] text-ink transition-colors hover:border-accent hover:text-accent focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60 disabled:opacity-50"
          >
            {pending ? "Wird geprüft" : "Bestätigen"}
          </button>
        </form>
      )}
    </div>
  );
}
