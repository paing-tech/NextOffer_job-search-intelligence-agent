export type JobPosting = {
  id: string;
  source_url: string | null;
  source_platform: string | null;
  company: string | null;
  title: string | null;
  location: string | null;
  employment_type: string | null;
  seniority: string | null;
  remote_policy: string | null;
  salary_text: string | null;
  skills: string[];
  experience_requirements: string[];
  education_requirements: string[];
  summary: string | null;
  created_at?: string | null;
  tracked_application_id?: string | null;
};

export type AgentEvent =
  | { type: "session"; chat_session_id: string }
  | { type: "tool"; name: string }
  | { type: "final"; text: string; chat_session_id: string; data: unknown }
  | { type: "error"; message: string };

export type Application = {
  id: string;
  company: string;
  job_title: string;
  status: string;
  next_action: string | null;
  salary: string | null;
  requirements: string | null;
  platform: string | null;
  first_seen_at: string | null;
  status_changed_at: string | null;
  last_update_at: string | null;
};

export type ApplicationDetail = Application & { job_posting?: JobPosting };

export type AnalyzeResult =
  | { status: "ok"; job_posting: JobPosting; fetch_source: string | null }
  | { status: "needs_paste"; platform: string; reason: string | null; message: string }
  | { status: "error"; message: string };

/** POST /api/backend/jobs/analyze — a job URL or pasted description text. */
export async function analyzeJob(payload: { url?: string; text?: string }): Promise<AnalyzeResult> {
  const res = await fetch("/api/backend/jobs/analyze", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    return { status: "error", message: detail.detail ?? `Request failed (${res.status}).` };
  }
  return (await res.json()) as AnalyzeResult;
}

/** POST /api/backend/applications — create or update a tracked application. */
export async function trackApplication(payload: {
  company: string;
  job_title: string;
  job_posting_id?: string;
}): Promise<{ created: boolean; application: Application } | { error: string }> {
  const res = await fetch("/api/backend/applications", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) return { error: `Request failed (${res.status}).` };
  return res.json();
}

/** POST /api/backend/chat and yield parsed SSE events. */
export async function* streamChat(
  message: string,
  chatSessionId: string | null,
): AsyncGenerator<AgentEvent> {
  const res = await fetch("/api/backend/chat", {
    method: "POST",
    headers: { "content-type": "application/json", accept: "text/event-stream" },
    body: JSON.stringify({ message, chat_session_id: chatSessionId }),
  });
  if (!res.ok || !res.body) {
    yield { type: "error", message: `Request failed (${res.status}).` };
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const line = chunk.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      try {
        yield JSON.parse(line.slice(5).trim()) as AgentEvent;
      } catch {
        // ignore malformed frame
      }
    }
  }
}

export type ChatSessionSummary = {
  id: string;
  title: string;
  updated_at: string | null;
  created_at: string | null;
};

export type ChatHistoryMessage = { role: "user" | "assistant"; content: string };

/** GET /api/backend/chat/sessions — past chat sessions, most recently updated first. */
export async function listChatSessions(): Promise<ChatSessionSummary[]> {
  const res = await fetch("/api/backend/chat/sessions", { headers: { accept: "application/json" } });
  if (!res.ok) return [];
  const data = (await res.json()) as { sessions: ChatSessionSummary[] };
  return data.sessions;
}

/** GET /api/backend/chat/sessions/{id} — a past session's displayable transcript. */
export async function getChatSession(id: string): Promise<ChatHistoryMessage[] | null> {
  const res = await fetch(`/api/backend/chat/sessions/${id}`, { headers: { accept: "application/json" } });
  if (!res.ok) return null;
  const data = (await res.json()) as { messages: ChatHistoryMessage[] };
  return data.messages;
}

export async function listApplications(status?: string): Promise<Application[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  const res = await fetch(`/api/backend/applications${qs}`, { headers: { accept: "application/json" } });
  if (!res.ok) return [];
  const data = (await res.json()) as { applications: Application[] };
  return data.applications;
}

/** GET /api/backend/jobs — every job posting the user has ever analyzed, newest first. */
export async function listJobPostings(): Promise<JobPosting[]> {
  const res = await fetch("/api/backend/jobs", { headers: { accept: "application/json" } });
  if (!res.ok) return [];
  const data = (await res.json()) as { job_postings: JobPosting[] };
  return data.job_postings;
}

export async function getApplication(id: string): Promise<ApplicationDetail | null> {
  const res = await fetch(`/api/backend/applications/${id}`, { headers: { accept: "application/json" } });
  if (!res.ok) return null;
  return (await res.json()) as ApplicationDetail;
}
