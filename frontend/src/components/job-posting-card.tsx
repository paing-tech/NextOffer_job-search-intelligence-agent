import type { JobPosting } from "@/lib/api";

export function Chips({ label, items }: { label: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="jp-group">
      <span className="jp-group-label">{label}</span>
      <ul className="jp-chips">
        {items.map((item) => (
          <li key={item} className="jp-chip">{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function JobPostingCard({ posting }: { posting: JobPosting }) {
  // Trimmed to just the essentials for chat — title/company/location/type/
  // salary as a compact header, skills + experience chips, and a link to
  // the original posting. No summary paragraph or education chips here;
  // the full detail still lives in the Applications card's modal.
  const meta = [posting.location, posting.employment_type, posting.salary_text].filter(Boolean).join(" · ");

  return (
    <article className="jp-card">
      <header className="jp-head">
        <h3>{posting.title ?? "Job posting"}</h3>
        <p className="jp-company">{posting.company ?? "Unknown company"}</p>
        {meta && <p className="jp-meta">{meta}</p>}
      </header>
      <Chips label="Skills" items={posting.skills} />
      <Chips label="Experience" items={posting.experience_requirements} />
      {posting.source_url && (
        <a className="jp-source" href={posting.source_url} target="_blank" rel="noreferrer">
          View original ↗
        </a>
      )}
    </article>
  );
}
