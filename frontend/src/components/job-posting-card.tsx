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
  const meta = [posting.location, posting.employment_type, posting.remote_policy, posting.seniority]
    .filter(Boolean)
    .join(" · ");

  return (
    <article className="jp-card">
      <header className="jp-head">
        <h3>{posting.title ?? "Job posting"}</h3>
        <p className="jp-company">{posting.company ?? "Unknown company"}</p>
        {meta && <p className="jp-meta">{meta}</p>}
        {posting.salary_text && <p className="jp-meta">{posting.salary_text}</p>}
      </header>
      {posting.summary && <p className="jp-summary">{posting.summary}</p>}
      <Chips label="Skills" items={posting.skills} />
      <Chips label="Experience" items={posting.experience_requirements} />
      <Chips label="Education" items={posting.education_requirements} />
      {posting.source_url && (
        <a className="jp-source" href={posting.source_url} target="_blank" rel="noreferrer">
          View original ↗
        </a>
      )}
    </article>
  );
}
