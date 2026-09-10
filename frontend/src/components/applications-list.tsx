"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listApplications, type Application } from "@/lib/api";

const STATUS_LABEL: Record<string, string> = {
  discovered: "Discovered",
  applied: "Applied",
  assessment: "Assessment",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  ghosted: "Ghosted",
};

export function ApplicationsList() {
  const [apps, setApps] = useState<Application[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    listApplications()
      .then(setApps)
      .catch(() => setFailed(true));
  }, []);

  if (failed) return <p className="apps-empty">Couldn’t load your applications. Try again in a moment.</p>;
  if (apps === null) return <p className="apps-empty">Loading…</p>;

  if (apps.length === 0) {
    return (
      <div className="apps-empty">
        <p>No tracked applications yet.</p>
        <p>
          Paste a job link in <Link href="/">Chat</Link> and say “track this”, or share a job to NextOffer.
        </p>
      </div>
    );
  }

  return (
    <ul className="apps-list">
      {apps.map((a) => (
        <li key={a.id} className="app-row">
          <div className="app-row-main">
            <p className="app-title">{a.job_title}</p>
            <p className="app-company">{a.company}</p>
            {a.next_action && <p className="app-next">Next: {a.next_action}</p>}
          </div>
          <span className="app-status" data-status={a.status}>
            {STATUS_LABEL[a.status] ?? a.status}
          </span>
        </li>
      ))}
    </ul>
  );
}
