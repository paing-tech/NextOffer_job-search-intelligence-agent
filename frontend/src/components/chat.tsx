"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

const suggestions = ["Track a job opportunity", "Scan my application emails", "What can NextOffer do?"];
type Message = { role: "user" | "assistant"; content: string };

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => { if (messages.length) endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages]);

  function send(event: FormEvent) {
    event.preventDefault();
    const content = input.trim();
    if (!content) return;
    setMessages((previous) => [...previous, { role: "user", content }, { role: "assistant", content: "This is the local UI preview. I can’t read emails, extract job details, or update Sheets yet. Your NextOffer sign-in is working. Google authorization and the agent connection are our next steps. This conversation is temporary and clears when you leave or refresh this page." }]);
    setInput("");
    inputRef.current?.focus();
  }

  return (
    <main className="chat-page">
      <div className="page-heading"><h1>Chat</h1><span className="badge">LOCAL PREVIEW</span></div>
      <div className="conversation" role="log" aria-label="Conversation" aria-live="polite">
        {messages.length === 0 ? <section className="welcome">
          <div className="welcome-mark" aria-hidden="true">↗</div>
          <span className="eyebrow">LESS ADMIN. MORE OPPORTUNITY.</span>
          <h2>Make room for<br />your next offer.</h2>
          <p>A little help keeping your job search organized.<br className="desktop-break" /> Your conversations here. Your applications in Sheets.</p>
          <div className="suggestions">{suggestions.map((suggestion, i) => <button key={suggestion} onClick={() => { setInput(suggestion); inputRef.current?.focus(); }}><span className="suggestion-number">0{i + 1}</span><span>{suggestion}</span><span aria-hidden="true">↗</span></button>)}</div>
        </section> : <div className="messages">{messages.map((message, index) => <article key={index} className={`message ${message.role}`}><span className="message-label">{message.role === "user" ? "YOU" : "NEXTOFFER · PREVIEW"}</span><p>{message.content}</p></article>)}<div ref={endRef} /></div>}
      </div>
      <div className="composer-wrap">
        <form className="composer" onSubmit={send}>
          <label className="sr-only" htmlFor="message">Message NextOffer</label>
          <textarea ref={inputRef} id="message" rows={2} maxLength={8000} placeholder="Paste a job link or ask about your applications…" value={input} onChange={(event) => setInput(event.target.value)} />
          <div className="composer-actions"><span>Chat preview · No connected accounts</span><button className="send-button" type="submit" disabled={!input.trim()} aria-label="Send message">↑</button></div>
        </form>
        <p className="composer-note">Preview only. No messages are sent to an AI service.</p>
      </div>
    </main>
  );
}
