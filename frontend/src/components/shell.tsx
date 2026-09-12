"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { FilterAltIcon } from "@/components/icons/filter-alt-icon";
import { BlocksIcon, type BlocksIconHandle } from "@/components/icons/blocks-icon";
import { UserRoundIcon, type UserRoundIconHandle } from "@/components/icons/user-round-icon";
import { AtomIcon, type AtomIconHandle } from "@/components/icons/atom-icon";
import { listChatSessions, type ChatSessionSummary } from "@/lib/api";

function BriefcaseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="7.5" width="18" height="12.5" rx="1.6" />
      <path d="M9 7.5V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v1.5" />
      <path d="M3 12h18" />
    </svg>
  );
}

function HistoryIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 3v5h5" />
      <path d="M3.05 13A9 9 0 1 0 6 5.3L3 8" />
      <path d="M12 7v5l4 2" />
    </svg>
  );
}

const STATUS_FILTERS: { value: string | null; label: string }[] = [
  { value: null, label: "All" },
  { value: "saved", label: "Saved" },
  { value: "applied", label: "Applied" },
  { value: "in_progress", label: "In Progress" },
  { value: "interview", label: "Interview" },
  { value: "accepted", label: "Accepted" },
  { value: "rejected", label: "Rejected" },
];

// Isolated so only this piece needs `useSearchParams()` — wrapping just it
// (not the whole Shell) in Suspense keeps every other route statically
// prerenderable instead of forcing a client-side bailout app-wide.
function ApplicationsFilter() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [filterOpen, setFilterOpen] = useState(false);
  // SMIL <animate> only plays once per mount, so bump this on every click to
  // force FilterAltIcon to remount and replay its draw-in animation.
  const [animKey, setAnimKey] = useState(0);
  const activeStatus = searchParams.get("status");

  function selectStatus(value: string | null) {
    setFilterOpen(false);
    router.push(value ? `/applications?status=${value}` : "/applications");
  }

  return (
    <div className="topbar-filter-wrap">
      <button
        type="button"
        className={activeStatus ? "topbar-filter active" : "topbar-filter"}
        aria-label="Filter applications"
        aria-expanded={filterOpen}
        onClick={() => {
          setFilterOpen((o) => !o);
          setAnimKey((k) => k + 1);
        }}
      >
        <FilterAltIcon key={animKey} size={24} />
      </button>
      {filterOpen && (
        <>
          <div className="topbar-filter-backdrop" onClick={() => setFilterOpen(false)} />
          <ul className="topbar-filter-menu" role="menu">
            {STATUS_FILTERS.map(({ value, label }) => (
              <li key={label}>
                <button
                  type="button"
                  role="menuitemradio"
                  aria-checked={activeStatus === value || (!activeStatus && value === null)}
                  onClick={() => selectStatus(value)}
                >
                  {label}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

// Isolated for the same reason as ApplicationsFilter — only this piece needs
// `useSearchParams()`.
function AgentHistory() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [open, setOpen] = useState(false);
  const [sessions, setSessions] = useState<ChatSessionSummary[] | null>(null);
  const [loading, setLoading] = useState(false);
  const currentSessionId = searchParams.get("session");

  async function togglePanel() {
    const next = !open;
    setOpen(next);
    if (next) {
      // Refetch every time it opens rather than caching — the list changes
      // as soon as the user sends a message in a new chat.
      setLoading(true);
      setSessions(await listChatSessions());
      setLoading(false);
    }
  }

  function selectSession(id: string) {
    setOpen(false);
    router.push(`/?session=${id}`);
  }

  function startNewChat() {
    setOpen(false);
    router.push("/");
  }

  return (
    <div className="topbar-filter-wrap">
      <button
        type="button"
        className={currentSessionId ? "topbar-filter active" : "topbar-filter"}
        aria-label="Chat history"
        aria-expanded={open}
        onClick={togglePanel}
      >
        <HistoryIcon />
      </button>
      {open && (
        <>
          <div className="topbar-filter-backdrop" onClick={() => setOpen(false)} />
          <ul className="topbar-filter-menu topbar-history-menu" role="menu">
            <li>
              <button type="button" onClick={startNewChat}>+ New chat</button>
            </li>
            {loading && <li className="topbar-history-empty">Loading…</li>}
            {!loading && sessions?.length === 0 && <li className="topbar-history-empty">No past chats yet</li>}
            {!loading &&
              sessions?.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    role="menuitemradio"
                    aria-checked={currentSessionId === s.id}
                    onClick={() => selectSession(s.id)}
                  >
                    {s.title}
                  </button>
                </li>
              ))}
          </ul>
        </>
      )}
    </div>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const libraryIconRef = useRef<BlocksIconHandle>(null);
  const agentIconRef = useRef<AtomIconHandle>(null);
  const profileIconRef = useRef<UserRoundIconHandle>(null);

  // Shrinks the tab bar on scroll-down (like Instagram's), restores it on
  // scroll-up — regardless of which page is scrolling underneath, since
  // Shell wraps every page.
  const [navCompact, setNavCompact] = useState(false);
  // Held continuously (not a one-shot animation) for as long as the bar is
  // hovered or pressed/touched; scales up while true, eases back to whatever
  // navCompact says once released.
  const [navActive, setNavActive] = useState(false);
  // Which tab (by href) is currently hovered/pressed — the selected tab's
  // glass pill only bulges past the bar's edges while it is the one being
  // interacted with; otherwise it sits flush, matching its old flat size.
  const [hoveredTab, setHoveredTab] = useState<string | null>(null);
  const lastScrollY = useRef(0);

  useEffect(() => {
    lastScrollY.current = window.scrollY;
    function onScroll() {
      const y = window.scrollY;
      const delta = y - lastScrollY.current;
      if (y < 40) setNavCompact(false);
      else if (delta > 4) setNavCompact(true);
      else if (delta < -4) setNavCompact(false);
      lastScrollY.current = y;
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (pathname === "/login" || pathname.startsWith("/auth/")) return <>{children}</>;

  function tabClassName(href: string, isActive: boolean) {
    if (!isActive) return "navtab";
    return hoveredTab === href ? "navtab active enlarged" : "navtab active";
  }

  function tabHoverHandlers(href: string) {
    const clear = () => setHoveredTab((h) => (h === href ? null : h));
    return {
      onMouseEnter: () => setHoveredTab(href),
      onMouseLeave: clear,
      onPointerDown: () => setHoveredTab(href),
      onPointerUp: clear,
      onPointerCancel: clear,
      onPointerLeave: clear,
    };
  }

  const isApplications = pathname.startsWith("/applications");
  const isLibrary = pathname.startsWith("/library");
  const isAgent = pathname === "/";
  const isProfile = pathname.startsWith("/settings");

  return (
    <div className="shell">
      {isApplications ? (
        <header className="topbar topbar-frozen">
          <span className="topbar-spacer" aria-hidden="true" />
          <h1 className="topbar-title">Applications</h1>
          <Suspense fallback={<span className="topbar-spacer" aria-hidden="true" />}>
            <ApplicationsFilter />
          </Suspense>
        </header>
      ) : isAgent ? (
        <header className="topbar topbar-frozen">
          <span className="topbar-spacer" aria-hidden="true" />
          <h1 className="topbar-title">Agent</h1>
          <Suspense fallback={<span className="topbar-spacer" aria-hidden="true" />}>
            <AgentHistory />
          </Suspense>
        </header>
      ) : (
        <header className="topbar" />
      )}

      <div className="content">{children}</div>

      <nav className="bottomnav" aria-label="Primary">
        <div
          className={`bottomnav-inner${navActive ? " pressed" : navCompact ? " compact" : ""}`}
          onMouseEnter={() => setNavActive(true)}
          onMouseLeave={() => setNavActive(false)}
          onPointerDown={() => setNavActive(true)}
          onPointerUp={() => setNavActive(false)}
          onPointerCancel={() => setNavActive(false)}
          onPointerLeave={() => setNavActive(false)}
        >
          <Link
            href="/applications"
            className={tabClassName("/applications", isApplications)}
            aria-current={isApplications ? "page" : undefined}
            {...tabHoverHandlers("/applications")}
          >
            <BriefcaseIcon />
            <span>Applications</span>
          </Link>
          {/* Ref present -> the icon is "controlled": hover no longer
              auto-triggers the draw-in animation, so tapping the tab is
              what plays it (via the imperative startAnimation handle). */}
          <Link
            href="/library"
            className={tabClassName("/library", isLibrary)}
            aria-current={isLibrary ? "page" : undefined}
            onClick={() => libraryIconRef.current?.startAnimation()}
            {...tabHoverHandlers("/library")}
          >
            <BlocksIcon ref={libraryIconRef} />
            <span>Library</span>
          </Link>
          <Link
            href="/"
            className={tabClassName("/", isAgent)}
            aria-current={isAgent ? "page" : undefined}
            onClick={() => agentIconRef.current?.startAnimation()}
            {...tabHoverHandlers("/")}
          >
            <AtomIcon ref={agentIconRef} />
            <span>Agent</span>
          </Link>
          <Link
            href="/settings"
            className={tabClassName("/settings", isProfile)}
            aria-current={isProfile ? "page" : undefined}
            onClick={() => profileIconRef.current?.startAnimation()}
            {...tabHoverHandlers("/settings")}
          >
            <UserRoundIcon ref={profileIconRef} />
            <span>Profile</span>
          </Link>
        </div>
      </nav>
    </div>
  );
}
