"use client";

import { FormEvent, useState } from "react";

type ScanResult = {
  status: string;
  messages_scanned: number;
  events_created: number;
  applications_updated: number;
  error?: string | null;
};

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function ScanCard() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [includePresent, setIncludePresent] = useState(true);
  const [force, setForce] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runScan(event: FormEvent) {
    event.preventDefault();
    if (!startDate) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/backend/scans/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          start_date: startDate,
          end_date: includePresent ? null : endDate || null,
          force,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail ?? "Could not start the scan.");
        return;
      }
      setResult(data);
    } catch {
      setError("Unable to connect. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="settings-card" aria-labelledby="scan-title">
      <div className="card-title"><h3 id="scan-title">03 <span>Scan Gmail</span></h3></div>
      <p>Scan a date range of your inbox for job-application emails. New updates sync straight to your tracker and spreadsheet.</p>

      <form className="scan-form" onSubmit={runScan}>
        <label htmlFor="scan-start">From
          <input
            id="scan-start"
            type="date"
            required
            max={today()}
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </label>
        <label htmlFor="scan-end" data-disabled={includePresent}>To
          <input
            id="scan-end"
            type="date"
            disabled={includePresent}
            max={today()}
            min={startDate || undefined}
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </label>
        <label className="scan-present" htmlFor="scan-present">
          <input
            id="scan-present"
            type="checkbox"
            checked={includePresent}
            onChange={(e) => setIncludePresent(e.target.checked)}
          />
          Include up to today
        </label>
        <label className="scan-present" htmlFor="scan-force">
          <input
            id="scan-force"
            type="checkbox"
            checked={force}
            onChange={(e) => setForce(e.target.checked)}
          />
          Rescan emails already seen in this range
        </label>
        <button className="button primary" type="submit" disabled={busy || !startDate}>
          {busy ? "Scanning…" : "Scan now"}
        </button>
      </form>

      {error && <p className="auth-message" role="status">{error}</p>}

      {result && (
        <div className="sync-details">
          <span>Last scan</span>
          <strong>
            {result.status === "failed"
              ? `Failed: ${result.error}`
              : `${result.messages_scanned} scanned · ${result.events_created} events · ${result.applications_updated} applications updated`}
          </strong>
        </div>
      )}
    </section>
  );
}
