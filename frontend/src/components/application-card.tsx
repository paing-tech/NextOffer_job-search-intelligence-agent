import type { Application } from "@/lib/api";

const STATUS_LABEL: Record<string, string> = {
  saved: "Saved",
  applied: "Applied",
  in_progress: "In Progress",
  interview: "Interview",
  accepted: "Accepted",
  rejected: "Rejected",
};

const PLATFORM_ICON: Record<string, string> = {
  linkedin: "/linkedin.svg",
  jobstreet: "/jobstreet.png",
};

const PLATFORM_LABEL: Record<string, string> = {
  linkedin: "LinkedIn",
  jobstreet: "JobStreet",
  seek: "SEEK",
  indeed: "Indeed",
  glassdoor: "Glassdoor",
  lever: "Lever",
  greenhouse: "Greenhouse",
  ashby: "Ashby",
  generic: "Other",
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatAppliedDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${String(d.getDate()).padStart(2, "0")} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

// Shows the date the status last changed (falls back to last_update_at for
// older rows with no recorded status_changed_at), date only (no time), in a
// deliberately different (numeric) style from "Applied on" so the two dates
// read as distinct things.
function formatUpdatedDateOnly(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  return `${day}-${month}-${d.getFullYear()}`;
}

// Trims a verbose real-world title down to its essentials for the compact
// card — "x2 Software Engineer (Frontend React/.NET)[Fintech] - Hybrid"
// becomes "Software Engineer". The full, untouched title is shown when the
// card is opened.
function mainTitle(title: string): string {
  let t = title.trim();
  t = t.replace(/^x\d+\s+/i, "");
  let prev: string;
  do {
    prev = t;
    t = t.replace(/\s*\([^()]*\)\s*$/, "");
    t = t.replace(/\s*\[[^[\]]*\]\s*$/, "");
    t = t.replace(/\s+-\s+[^-]+$/, "");
  } while (t !== prev && t.length > 0);
  return t.trim() || title.trim();
}

function CheckCircleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <path d="m16 9-5.5 5.5L8 12" />
    </svg>
  );
}

/** The visual content of one application — reused by the list card and the detail modal's header. */
export function ApplicationCardBody({ a }: { a: Application }) {
  const icon = a.platform ? PLATFORM_ICON[a.platform] : undefined;
  const platformName = a.platform ? PLATFORM_LABEL[a.platform] ?? a.platform : null;
  const isSaved = a.status === "saved";

  return (
    <>
      {/* Grid, not two independently-stacked columns: title/status share a
          row and company/date share a row, guaranteed, regardless of each
          line's own height. */}
      <div className="app-card-top">
        <p className="app-card-title">{mainTitle(a.job_title)}</p>
        <span className="app-status" data-status={a.status}>{STATUS_LABEL[a.status] ?? a.status}</span>
        <p className="app-card-company">{a.company}</p>
        <span className="app-card-updated">{formatUpdatedDateOnly(a.status_changed_at ?? a.last_update_at)}</span>
      </div>

      {/* Always rendered, even when empty, so every card has the same
          structure and height regardless of status/platform. */}
      <div className="app-card-bottom">
        {!isSaved ? (
          <span className="app-card-applied">
            <CheckCircleIcon />
            Applied on {formatAppliedDate(a.first_seen_at)}
          </span>
        ) : (
          <span className="app-card-applied" aria-hidden="true">&nbsp;</span>
        )}
        {icon ? (
          // eslint-disable-next-line @next/next/no-img-element -- small static icon from /public, no optimization needed
          <img className="app-card-platform-icon" src={icon} alt={platformName ?? ""} />
        ) : platformName ? (
          <span className="app-card-platform">{platformName}</span>
        ) : null}
      </div>
    </>
  );
}
