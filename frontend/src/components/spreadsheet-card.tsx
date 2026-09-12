"use client";

import { useEffect, useState } from "react";

type Status = { connected: boolean; spreadsheet_id?: string | null; spreadsheet_url?: string | null };

export function SpreadsheetCard() {
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/backend/google/status")
      .then((r) => (r.ok ? r.json() : { connected: false }))
      .then(setStatus)
      .catch(() => setStatus({ connected: false }));
  }, []);

  async function create(replacing: boolean) {
    if (replacing && !window.confirm(
      "This creates a brand-new spreadsheet and re-syncs all your applications into it. " +
      "The old spreadsheet stays in your Drive but stops receiving updates. Continue?"
    )) return;

    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const res = await fetch("/api/backend/google/spreadsheet", { method: "POST" });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? "Could not create the spreadsheet.");
        return;
      }
      const data = (await res.json()) as { spreadsheet_id: string; url: string; resynced: number };
      setStatus((s) => (s ? { ...s, spreadsheet_id: data.spreadsheet_id, spreadsheet_url: data.url } : s));
      if (data.resynced > 0) setNote(`${data.resynced} existing application(s) copied into the new sheet.`);
    } finally {
      setBusy(false);
    }
  }

  const connected = status?.connected ?? false;
  const hasSheet = Boolean(status?.spreadsheet_id);

  return (
    <section className="settings-card" aria-labelledby="sheet-title">
      <div className="card-title"><h3 id="sheet-title">02 <span>Tracking spreadsheet</span></h3></div>
      <p>Your applications live in a Google Sheet — one row per application, kept in sync as status changes.</p>
      {!connected && <small>Connect Google above first.</small>}

      {connected && !hasSheet && (
        <button className="button primary" disabled={busy} onClick={() => create(false)}>
          {busy ? "Creating…" : "Create tracking spreadsheet"}
        </button>
      )}

      {connected && hasSheet && status?.spreadsheet_url && (
        <div className="sheet-actions">
          <a className="button primary" href={status.spreadsheet_url} target="_blank" rel="noreferrer">Open spreadsheet ↗</a>
          <button className="button" disabled={busy} onClick={() => create(true)}>
            {busy ? "Creating…" : "Create new spreadsheet"}
          </button>
        </div>
      )}

      {note && <p className="auth-message" role="status">{note}</p>}
      {error && <p className="auth-message" role="status">{error}</p>}
    </section>
  );
}
