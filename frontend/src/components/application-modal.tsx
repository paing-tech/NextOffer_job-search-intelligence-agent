"use client";

import { useEffect, useState } from "react";
import { getApplication, type ApplicationDetail } from "@/lib/api";
import { ApplicationCardBody } from "@/components/application-card";
import { Chips } from "@/components/job-posting-card";

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}

export function ApplicationModal({ applicationId, onClose }: { applicationId: string; onClose: () => void }) {
  const [detail, setDetail] = useState<ApplicationDetail | null>(null);

  useEffect(() => {
    let active = true;
    getApplication(applicationId).then((d) => {
      if (active) setDetail(d);
    });
    return () => {
      active = false;
    };
  }, [applicationId]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const posting = detail?.job_posting;
  const hasRequirementChips = Boolean(
    posting?.skills?.length || posting?.experience_requirements?.length || posting?.education_requirements?.length,
  );

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-sheet" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <div className="modal-handle" aria-hidden="true" />
        <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
          <CloseIcon />
        </button>

        {!detail ? (
          <p className="apps-empty">Loading…</p>
        ) : (
          <>
            <div className="app-card modal-card-static">
              <ApplicationCardBody a={detail} />
            </div>

            <section className="modal-section">
              <h4>Job title</h4>
              <p className="modal-summary">{detail.job_title}</p>
            </section>

            {posting?.summary && (
              <section className="modal-section">
                <h4>Summary</h4>
                <p className="modal-summary">{posting.summary}</p>
              </section>
            )}

            {hasRequirementChips ? (
              <section className="modal-section">
                <h4>Skills &amp; requirements</h4>
                <Chips label="Skills" items={posting?.skills ?? []} />
                <Chips label="Experience" items={posting?.experience_requirements ?? []} />
                <Chips label="Education" items={posting?.education_requirements ?? []} />
              </section>
            ) : detail.requirements ? (
              <section className="modal-section">
                <h4>Requirements</h4>
                <p className="modal-summary">{detail.requirements}</p>
              </section>
            ) : null}

            {!posting && !detail.requirements && (
              <p className="apps-empty">No job posting linked to this application yet.</p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
