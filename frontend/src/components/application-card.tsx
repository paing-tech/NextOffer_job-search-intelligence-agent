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

function formatLastUpdated(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const hours24 = d.getHours();
  const hours = String(hours24 % 12 || 12).padStart(2, "0");
  const minutes = String(d.getMinutes()).padStart(2, "0");
  const ampm = hours24 >= 12 ? "PM" : "AM";
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  return `${hours}:${minutes} ${ampm} ${day}-${month}-${d.getFullYear()}`;
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

  return (
    <>
      <div className="app-card-top">
        <span className="app-card-company">{a.company}</span>
        <div className="app-card-status-block">
          <span className="app-status" data-status={a.status}>{STATUS_LABEL[a.status] ?? a.status}</span>
          <span className="app-card-updated">{formatLastUpdated(a.last_update_at)}</span>
        </div>
      </div>

      <p className="app-card-title">{a.job_title}</p>

      <div className="app-card-bottom">
        <span className="app-card-applied">
          <CheckCircleIcon />
          Applied on {formatAppliedDate(a.first_seen_at)}
        </span>
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
