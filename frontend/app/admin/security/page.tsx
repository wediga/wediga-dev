"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

import { apiWrite } from "@/lib/adminClient";
import { useCsrf } from "@/components/admin/useCsrf";
import {
  AdminButton,
  AdminField,
  Feedback,
  useActionFeedback,
} from "@/components/admin/ui";

type SetupData = {
  secret: string;
  otpauth_uri: string;
  qr_svg: string;
};

// Admin page to enable the TOTP second factor. Setup generates a secret and a
// QR code, the admin scans it once and confirms a code, and only that confirmed
// code switches the factor on. Both writes carry the CSRF token like every
// other admin write.
export default function AdminSecurityPage() {
  const csrf = useCsrf();
  const { run, get } = useActionFeedback();
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [setup, setSetup] = useState<SetupData | null>(null);
  const [code, setCode] = useState("");

  useEffect(() => {
    fetch("/api/totp/status", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((data: { enabled: boolean } | null) =>
        setEnabled(data ? data.enabled : false),
      )
      .catch(() => setEnabled(false));
  }, []);

  async function startSetup() {
    await run(
      "setup",
      async () => {
        const response = await apiWrite("/api/totp/setup", "POST", csrf);
        if (!response.ok) return false;
        setSetup((await response.json()) as SetupData);
        setCode("");
        return true;
      },
      {
        success: "Scannen Sie den Code und bestätigen Sie ihn.",
        error: "Einrichtung fehlgeschlagen. Bitte erneut versuchen.",
      },
    );
  }

  async function confirmCode() {
    const ok = await run(
      "confirm",
      async () => {
        const response = await apiWrite("/api/totp/confirm", "POST", csrf, {
          code,
        });
        return response.ok;
      },
      {
        success: "Der zweite Faktor ist aktiv.",
        error: "Der Code ist ungültig. Bitte erneut versuchen.",
      },
    );
    if (ok) {
      setEnabled(true);
      setSetup(null);
      setCode("");
    }
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-ink">Security</h1>
      <p className="mt-1 text-sm text-muted">
        Zweiter Faktor (TOTP) für den Admin-Login.
      </p>

      <div className="mt-7 rounded-lg border border-line bg-surface/40 p-5">
        <p className="text-sm text-ink">
          Status:{" "}
          <span className="font-medium">
            {enabled === null
              ? "wird geladen"
              : enabled
                ? "aktiv"
                : "nicht aktiv"}
          </span>
        </p>

        {enabled === false && !setup ? (
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <AdminButton
              variant="primary"
              pending={get("setup").state === "pending"}
              pendingLabel="Wird erzeugt"
              onClick={startSetup}
              disabled={!csrf}
            >
              Einrichten
            </AdminButton>
            <Feedback status={get("setup")} pendingLabel="Wird erzeugt" />
          </div>
        ) : null}

        {enabled ? (
          <p className="mt-3 text-sm text-muted">
            Zum Zurücksetzen den zweiten Faktor direkt auf dem Server abschalten.
          </p>
        ) : null}
      </div>

      {setup ? (
        <div className="mt-6 rounded-lg border border-line bg-surface/40 p-5">
          <h2 className="text-base font-medium text-ink">
            Authenticator einrichten
          </h2>
          <p className="mt-1 text-sm text-muted">
            Scannen Sie den Code mit Ihrer Authenticator-App oder geben Sie das
            Secret manuell ein, danach bestätigen Sie mit einem Code.
          </p>

          <div className="mt-4 inline-block rounded-md bg-white p-3">
            <Image
              src={setup.qr_svg}
              alt="QR-Code für die Authenticator-App"
              width={180}
              height={180}
              unoptimized
            />
          </div>

          <p className="mt-4 text-xs text-muted">Secret für die manuelle Eingabe:</p>
          <code className="mt-1 block break-all rounded-md border border-line bg-bg px-3 py-2 font-mono text-sm text-ink">
            {setup.secret}
          </code>

          <div className="mt-5 max-w-xs">
            <AdminField
              label="Code"
              value={code}
              onChange={(value) => setCode(value.replace(/\D/g, "").slice(0, 6))}
              mono
              placeholder="123456"
            />
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <AdminButton
              variant="primary"
              pending={get("confirm").state === "pending"}
              pendingLabel="Wird geprüft"
              onClick={confirmCode}
              disabled={!csrf || code.length < 6}
            >
              Bestätigen
            </AdminButton>
            <Feedback status={get("confirm")} pendingLabel="Wird geprüft" />
          </div>
        </div>
      ) : null}
    </div>
  );
}
