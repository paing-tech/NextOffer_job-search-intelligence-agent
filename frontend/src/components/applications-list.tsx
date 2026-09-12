"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listApplications, type Application } from "@/lib/api";
import { ApplicationCardBody } from "@/components/application-card";
import { ApplicationModal } from "@/components/application-modal";

export function ApplicationsList() {
  const [apps, setApps] = useState<Application[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);

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
    <>
      <ul className="apps-list">
        {apps.map((a) => (
          <li key={a.id}>
            <button type="button" className="app-card" onClick={() => setOpenId(a.id)}>
              <ApplicationCardBody a={a} />
            </button>
          </li>
        ))}
      </ul>
      {openId && <ApplicationModal applicationId={openId} onClose={() => setOpenId(null)} />}
    </>
  );
}
