"use client";

import { FormEvent, useEffect, useState } from "react";

type AutoScanConfig = {
  enabled: boolean;
  start_date: string | null;
  frequency_minutes: number;
  last_run_at: string | null;
  last_status: string | null;
};

const FREQUENCIES = [
  { value: 15, label: "Every 15 minutes" },
  { value: 30, label: "Every 30 minutes" },
  { value: 60, label: "Every hour" },
  { value: 120, label: "Every 2 hours" },
];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatLastRun(iso: string | null): string {
  if (!iso) return "Not run yet";
  const d = new Date(iso);
  return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

export function AutoScanCard() {
  const [loaded, setLoaded] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [frequency, setFrequency] = useState(30);
  const [lastRunAt, setLastRunAt] = useState<string | null>(null);
  const [lastStatus, setLastStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/backend/scans/auto")
      .then((res) => res.json())
      .then((data: { config: AutoScanConfig | null }) => {
        if (!active || !data.config) return;
        setEnabled(data.config.enabled);
        setStartDate(data.config.start_date ?? "");
        setFrequency(data.config.frequency_minutes);
        setLastRunAt(data.config.last_run_at);
        setLastStatus(data.config.last_status);
      })
      .finally(() => {
        if (active) setLoaded(true);
      });
    return () => {
      active = false;
    };
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (enabled && !startDate) {
      setError("Pick a start date first.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await fetch("/api/backend/scans/auto", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          enabled,
          start_date: startDate || today(),
          frequency_minutes: frequency,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail ?? "Could not save automatic scanning.");
        return;
      }
      setLastRunAt(data.config.last_run_at);
      setLastStatus(data.config.last_status);
    } catch {
      setError("Unable to connect. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="settings-card" aria-labelledby="auto-scan-title">
      <div className="card-title">
        <h3 id="auto-scan-title">
          04 <span>Automatic email scans</span>
        </h3>
        <span className="status">{enabled ? "Active" : "Not active"}</span>
      </div>
      <p>
        Run scans on a schedule on the server, from a fixed start date up through now, even when you close this
        app. Already-processed emails are never re-scanned.
      </p>
      <form className="scan-form" onSubmit={save}>
        <label className="scan-present" htmlFor="auto-enabled">
          <input
            id="auto-enabled"
            type="checkbox"
            checked={enabled}
            disabled={!loaded}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          Enable automatic scans
        </label>
        <label htmlFor="auto-start" data-disabled={!enabled}>
          From
          <input
            id="auto-start"
            type="date"
            required={enabled}
            disabled={!enabled}
            max={today()}
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </label>
        <label htmlFor="auto-frequency" data-disabled={!enabled}>
          Scan frequency
          <select
            id="auto-frequency"
            disabled={!enabled}
            value={frequency}
            onChange={(e) => setFrequency(Number(e.target.value))}
          >
            {FREQUENCIES.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
        </label>
        <button className="button primary" type="submit" disabled={saving || !loaded}>
          {saving ? "Saving…" : "Save"}
        </button>
      </form>

      {error && <p className="auth-message" role="status">{error}</p>}

      {loaded && (lastRunAt || lastStatus) && (
        <div className="sync-details">
          <span>Last automatic run</span>
          <strong>
            {formatLastRun(lastRunAt)}
            {lastStatus ? ` · ${lastStatus.replaceAll("_", " ")}` : ""}
          </strong>
        </div>
      )}
    </section>
  );
}
