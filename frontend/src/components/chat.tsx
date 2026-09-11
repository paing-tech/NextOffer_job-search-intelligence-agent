"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { JobPostingCard } from "@/components/job-posting-card";
import { streamChat, type JobPosting } from "@/lib/api";

type Message = {
  role: "user" | "assistant";
  content: string;
  posting?: JobPosting;
  pending?: boolean;
};

// Quick-message pills shown above the composer; tapping one fills the input.
const QUICK_MESSAGES = [{ label: "Analyze Job", fill: "Analyze this job link: " }];

export default function Chat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const sessionId = useRef<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messages.length) endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  async function send(event: FormEvent) {
    event.preventDefault();
    const content = input.trim();
    if (!content || busy) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content },
      { role: "assistant", content: "", pending: true },
    ]);
    setInput("");
    setBusy(true);
    setStatus(null);
    inputRef.current?.focus();

    try {
      for await (const evt of streamChat(content, sessionId.current)) {
        if (evt.type === "session") {
          sessionId.current = evt.chat_session_id;
        } else if (evt.type === "tool") {
          setStatus(`Running ${evt.name.replaceAll("_", " ")}…`);
        } else if (evt.type === "error") {
          setMessages((prev) => replaceLast(prev, { role: "assistant", content: `Something went wrong: ${evt.message}` }));
        } else if (evt.type === "final") {
          const data = evt.data as { status?: string; job_posting?: JobPosting } | null;
          setMessages((prev) =>
            replaceLast(prev, {
              role: "assistant",
              content: evt.text,
              posting: data?.status === "ok" ? data.job_posting : undefined,
            }),
          );
        }
      }
    } finally {
      setBusy(false);
      setStatus(null);
    }
  }

  return (
    <main className="chat-page">
      <div className="conversation" role="log" aria-label="Conversation" aria-live="polite">
        {messages.length > 0 && (
          <div className="messages">
            {messages.map((m, index) => (
              <article key={index} className={`message ${m.role}`}>
                <span className="message-label">{m.role === "user" ? "YOU" : "NEXTOFFER"}</span>
                {m.pending ? <p>{status ?? "Thinking…"}</p> : <p>{m.content}</p>}
                {m.posting && <JobPostingCard posting={m.posting} />}
              </article>
            ))}
            <div ref={endRef} />
          </div>
        )}
      </div>
      <div className="composer-wrap">
        <div className="quick-actions">
          {QUICK_MESSAGES.map((q) => (
            <button
              key={q.label}
              type="button"
              className="quick-pill"
              onClick={() => {
                setInput(q.fill);
                inputRef.current?.focus();
              }}
            >
              {q.label}
            </button>
          ))}
        </div>
        <form className="composer composer-dark composer-pill" onSubmit={send}>
          <div className="composer-body">
            <label className="sr-only" htmlFor="message">Message NextOffer</label>
            <input
              ref={inputRef}
              id="message"
              type="text"
              maxLength={8000}
              placeholder="Ask Agent"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button className="send-button" type="submit" disabled={!input.trim() || busy} aria-label="Send message">↑</button>
          </div>
        </form>
      </div>
    </main>
  );
}

function replaceLast(list: Message[], message: Message): Message[] {
  const copy = [...list];
  for (let i = copy.length - 1; i >= 0; i--) {
    if (copy[i].role === "assistant") {
      copy[i] = message;
      return copy;
    }
  }
  return [...copy, message];
}
