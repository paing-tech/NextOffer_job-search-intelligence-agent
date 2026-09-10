"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { JobPostingCard } from "@/components/job-posting-card";
import { analyzeJob, trackApplication, type JobPosting } from "@/lib/api";

type State =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "needs_paste"; message: string; url: string | null }
  | { phase: "done"; posting: JobPosting; source: string | null }
  | { phase: "error"; message: string };

export function ShareIntake({
  initialUrl,
  initialText,
  sharedTitle,
}: {
  initialUrl: string | null;
  initialText: string;
  sharedTitle: string | null;
}) {
  const hasInput = Boolean(initialUrl || initialText);
  const [state, setState] = useState<State>(hasInput ? { phase: "loading" } : { phase: "idle" });
  const [pasted, setPasted] = useState(initialText);
  const [tracked, setTracked] = useState<string | null>(null);
  const started = useRef(false);

  const analyze = useCallback(async (payload: { url?: string; text?: string }) => {
    const result = await analyzeJob(payload);
    if (result.status === "ok") {
      setState({ phase: "done", posting: result.job_posting, source: result.fetch_source });
    } else if (result.status === "needs_paste") {
      setState({ phase: "needs_paste", message: result.message, url: payload.url ?? null });
    } else {
      setState({ phase: "error", message: result.message });
    }
  }, []);

  useEffect(() => {
    if (started.current || !hasInput) return;
    started.current = true;
    void analyze(initialUrl ? { url: initialUrl } : { text: initialText });
  }, [hasInput, initialUrl, initialText, analyze]);

  function submitPaste(event: FormEvent) {
    event.preventDefault();
    if (pasted.trim().length < 40) return;
    setState({ phase: "loading" });
    void analyze({ text: pasted.trim() });
  }

  async function track(posting: JobPosting) {
    if (!posting.company || !posting.title) return;
    const res = await trackApplication({
      company: posting.company,
      job_title: posting.title,
      job_posting_id: posting.id,
    });
    setTracked("error" in res ? "Could not add to tracker." : "Added to your tracker.");
  }

  return (
    <main className="share-page">
      <div className="page-heading"><h1>Shared job</h1></div>

      {sharedTitle && state.phase !== "done" && <p className="share-title">{sharedTitle}</p>}

      {state.phase === "idle" && (
        <p className="share-status">
          Nothing was shared. <Link href="/">Go to chat</Link> and paste a job link instead.
        </p>
      )}

      {state.phase === "loading" && <p className="share-status">Reading the posting…</p>}

      {(state.phase === "error" || state.phase === "needs_paste") && (
        <div className="share-status">
          <p>{state.message}</p>
          {state.phase === "needs_paste" && state.url && (
            <a className="jp-source" href={state.url} target="_blank" rel="noreferrer">Open the posting ↗</a>
          )}
          <PasteForm value={pasted} onChange={setPasted} onSubmit={submitPaste} />
        </div>
      )}

      {state.phase === "done" && (
        <div className="share-result">
          <JobPostingCard posting={state.posting} />
          <div className="share-actions">
            <button
              className="button primary"
              disabled={!state.posting.company || !state.posting.title || tracked !== null}
              onClick={() => track(state.posting)}
            >
              Track this job
            </button>
            <Link className="button secondary" href="/">Open chat</Link>
          </div>
          {tracked && <p className="share-status" role="status">{tracked}</p>}
        </div>
      )}
    </main>
  );
}

function PasteForm({
  value,
  onChange,
  onSubmit,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: (e: FormEvent) => void;
}) {
  return (
    <form className="composer" onSubmit={onSubmit} style={{ marginTop: 14 }}>
      <label className="sr-only" htmlFor="jd">Job description</label>
      <textarea
        id="jd"
        rows={8}
        maxLength={20000}
        placeholder="Paste the job description text here…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="composer-actions">
        <span>Paste the full description for the best summary</span>
        <button className="button primary" type="submit" disabled={value.trim().length < 40}>Summarize</button>
      </div>
    </form>
  );
}
