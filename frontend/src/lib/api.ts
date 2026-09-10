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
  last_update_at: string | null;
};

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

export async function listApplications(): Promise<Application[]> {
  const res = await fetch("/api/backend/applications", { headers: { accept: "application/json" } });
  if (!res.ok) return [];
  const data = (await res.json()) as { applications: Application[] };
  return data.applications;
}
