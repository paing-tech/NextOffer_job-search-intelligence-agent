"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

type Status = { connected: boolean; connected_at?: string | null; spreadsheet_id?: string | null };

export function GoogleConnectionCard() {
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false);
  const params = useSearchParams();
  const redirectResult = params.get("google"); // "connected" | "error" | null
  const reason = params.get("reason");

  useEffect(() => {
    fetch("/api/backend/google/status")
      .then((r) => (r.ok ? r.json() : { connected: false }))
      .then(setStatus)
      .catch(() => setStatus({ connected: false }));
  }, [redirectResult]);

  async function disconnect() {
    setBusy(true);
    try {
      await fetch("/api/backend/google/connection", { method: "DELETE" });
      setStatus({ connected: false });
    } finally {
      setBusy(false);
    }
  }

  const connected = status?.connected ?? false;

  return (
    <section className="settings-card" aria-labelledby="google-title">
      <div className="card-title">
        <h3 id="google-title">01 <span>Google account</span></h3>
        <span className="status">{status === null ? "Checking…" : connected ? "Connected" : "Not connected"}</span>
      </div>
      <p>Your Google connection lets NextOffer read application emails and update your selected spreadsheet.</p>

      {redirectResult === "connected" && <p className="auth-message" role="status">Google account connected.</p>}
      {redirectResult === "error" && (
        <p className="auth-message" role="status">
          Couldn’t connect Google{reason ? `: ${decodeURIComponent(reason)}` : "."} Try again.
        </p>
      )}

      {connected ? (
        <button className="button" disabled={busy} onClick={disconnect}>
          {busy ? "Disconnecting…" : "Disconnect Google"}
        </button>
      ) : (
        <a className="button primary" href="/api/google/authorize">Connect Google</a>
      )}
      {connected && status?.connected_at && (
        <small>Connected {new Date(status.connected_at).toLocaleString()}.</small>
      )}
      {!connected && <small>Gmail read-only + Sheets access. You&apos;ll see Google&apos;s consent screen next.</small>}
    </section>
  );
}
