"use client";

import { useEffect, useState } from "react";
import { listJobPostings, trackApplication, type JobPosting } from "@/lib/api";
import { JobPostingCard } from "@/components/job-posting-card";

export function LibraryList() {
  const [postings, setPostings] = useState<JobPosting[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [trackingId, setTrackingId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    listJobPostings().then(
      (result) => {
        if (active) setPostings(result);
      },
      () => {
        if (active) setFailed(true);
      },
    );
    return () => {
      active = false;
    };
  }, []);

  async function handleTrack(posting: JobPosting) {
    if (!posting.company || !posting.title) return;
    setTrackingId(posting.id);
    const result = await trackApplication({
      company: posting.company,
      job_title: posting.title,
      job_posting_id: posting.id,
    });
    setTrackingId(null);
    if ("application" in result) {
      const applicationId = result.application.id;
      setPostings((prev) =>
        prev ? prev.map((p) => (p.id === posting.id ? { ...p, tracked_application_id: applicationId } : p)) : prev,
      );
    }
  }

  if (failed) return <p className="apps-empty">Couldn’t load your library. Try again in a moment.</p>;
  if (postings === null) return <p className="apps-empty">Loading…</p>;

  if (postings.length === 0) {
    return (
      <p className="apps-empty">
        Nothing here yet. Paste a job link in Agent (or share one to NextOffer) and it will show up here
        automatically.
      </p>
    );
  }

  return (
    <ul className="library-list">
      {postings.map((posting) => (
        <li key={posting.id} className="library-item">
          <JobPostingCard posting={posting} />
          {posting.company && posting.title && (
            <div className="library-item-footer">
              {posting.tracked_application_id ? (
                <span className="status">✓ Tracked</span>
              ) : (
                <button
                  type="button"
                  className="button primary"
                  disabled={trackingId === posting.id}
                  onClick={() => handleTrack(posting)}
                >
                  {trackingId === posting.id ? "Tracking…" : "Track this application"}
                </button>
              )}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}
