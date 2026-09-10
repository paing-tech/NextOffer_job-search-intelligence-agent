"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { JobPostingCard } from "@/components/job-posting-card";
import { streamChat, type JobPosting } from "@/lib/api";

const suggestions = ["Analyze a job link", "Show my applications", "What can NextOffer do?"];

type Message = {
  role: "user" | "assistant";
  content: string;
  posting?: JobPosting;
  pending?: boolean;
};

export default function Chat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const sessionId = useRef<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
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
      <div className="page-heading"><h1>Chat</h1></div>
      <div className="conversation" role="log" aria-label="Conversation" aria-live="polite">
        {messages.length === 0 ? (
          <section className="welcome">
            <div className="welcome-mark" aria-hidden="true">↗</div>
            <span className="eyebrow">LESS ADMIN. MORE OPPORTUNITY.</span>
            <h2>Make room for<br />your next offer.</h2>
            <p>Paste a job link and I&apos;ll break it down, or ask about the roles you&apos;re tracking.</p>
            <div className="suggestions">
              {suggestions.map((s, i) => (
                <button key={s} onClick={() => { setInput(s); inputRef.current?.focus(); }}>
                  <span className="suggestion-number">0{i + 1}</span><span>{s}</span><span aria-hidden="true">↗</span>
                </button>
              ))}
            </div>
          </section>
        ) : (
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
        <form className="composer" onSubmit={send}>
          <label className="sr-only" htmlFor="message">Message NextOffer</label>
          <textarea
            ref={inputRef}
            id="message"
            rows={2}
            maxLength={8000}
            placeholder="Paste a job link or ask about your applications…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send(e);
              }
            }}
          />
          <div className="composer-actions">
            <span>{busy ? status ?? "Working…" : "Connected to your NextOffer agent"}</span>
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
