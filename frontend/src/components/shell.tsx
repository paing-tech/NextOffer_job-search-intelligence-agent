"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
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

// A tap that also triggers Link navigation doesn't reliably fire
// pointerup/pointercancel afterward on mobile Safari — the "press" state
// (whatever it drives) could get stuck enlarged until the next unrelated
// touch. This hook is the fix: press-start also arms a timeout that force
// -releases on its own, while a genuine release (if it does fire) clears
// that timeout and releases immediately instead of waiting on it.
function usePressState() {
  const [pressed, setPressed] = useState(false);
  const timeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const start = useCallback(() => {
    setPressed(true);
    if (timeout.current) clearTimeout(timeout.current);
    timeout.current = setTimeout(() => setPressed(false), 400);
  }, []);
  const end = useCallback(() => {
    if (timeout.current) {
      clearTimeout(timeout.current);
      timeout.current = null;
    }
    setPressed(false);
  }, []);

  useEffect(() => () => {
    if (timeout.current) clearTimeout(timeout.current);
  }, []);

  return { pressed, start, end };
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
  const bar = usePressState();
  // Which tab (by href) is currently hovered/pressed — the sliding indicator
  // only enlarges while it's the one being interacted with.
  const [hoveredTab, setHoveredTab] = useState<string | null>(null);
  const tabPress = usePressState();
  const lastScrollY = useRef(0);

  // The sliding indicator: measured off the active tab's real DOM position
  // rather than living per-tab, so it can animate *between* two different
  // elements' positions (a CSS pseudo-element scoped to one tab can't).
  const tabRefs = useRef<Partial<Record<string, HTMLAnchorElement | null>>>({});
  const [indicator, setIndicator] = useState<{ left: number; width: number } | null>(null);
  const [sliding, setSliding] = useState(false);
  const prevActiveHref = useRef<string | null>(null);
  const slideTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  const isApplications = pathname.startsWith("/applications");
  const isLibrary = pathname.startsWith("/library");
  const isAgent = pathname === "/";
  const isProfile = pathname.startsWith("/settings");
  const activeHref = isApplications ? "/applications" : isLibrary ? "/library" : isAgent ? "/" : isProfile ? "/settings" : null;

  const measure = useCallback(() => {
    const tabEl = activeHref ? tabRefs.current[activeHref] : null;
    if (!tabEl) return;
    // offsetLeft/offsetWidth are layout-space (relative to .bottomnav-inner,
    // its offsetParent — it has position:relative) and unaffected by any
    // transform:scale() currently applied to the bar (pressed/compact
    // states). getBoundingClientRect() would return post-transform visual
    // pixels instead, which — reapplied as this indicator's own translateX
    // — get scaled *again* by the bar's transform, compounding into a
    // misaligned pill whenever a scale happens to be active at tap time
    // (which it usually is, since tapping a tab also triggers the bar's own
    // press-scale). A small inset keeps adjacent pills from ever touching.
    setIndicator({ left: tabEl.offsetLeft + 3, width: tabEl.offsetWidth - 4 });
  }, [activeHref]);

  useLayoutEffect(() => {
    const isFirst = prevActiveHref.current === null;
    prevActiveHref.current = activeHref;
    measure();
    if (!isFirst) {
      setSliding(true);
      if (slideTimeout.current) clearTimeout(slideTimeout.current);
      slideTimeout.current = setTimeout(() => setSliding(false), 320);
    }
  }, [activeHref, measure]);

  useEffect(() => {
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [measure]);

  if (pathname === "/login" || pathname.startsWith("/auth/")) return <>{children}</>;

  function tabHoverHandlers(href: string) {
    return {
      onMouseEnter: () => setHoveredTab(href),
      onMouseLeave: () => setHoveredTab((h) => (h === href ? null : h)),
      onPointerDown: () => {
        setHoveredTab(href);
        tabPress.start();
      },
      onPointerUp: () => {
        setHoveredTab((h) => (h === href ? null : h));
        tabPress.end();
      },
      onPointerCancel: () => {
        setHoveredTab((h) => (h === href ? null : h));
        tabPress.end();
      },
      onPointerLeave: () => {
        setHoveredTab((h) => (h === href ? null : h));
        tabPress.end();
      },
    };
  }

  const indicatorEnlarged = sliding || (tabPress.pressed && hoveredTab === activeHref);

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
          className={`bottomnav-inner${bar.pressed ? " pressed" : navCompact ? " compact" : ""}`}
          onMouseEnter={bar.start}
          onMouseLeave={bar.end}
          onPointerDown={bar.start}
          onPointerUp={bar.end}
          onPointerCancel={bar.end}
          onPointerLeave={bar.end}
        >
          {indicator && (
            <span
              aria-hidden="true"
              className={`nav-indicator${indicatorEnlarged ? " enlarged" : ""}`}
              style={{ transform: `translateX(${indicator.left}px) scale(${indicatorEnlarged ? 1.15 : 1})`, width: indicator.width }}
            />
          )}
          <Link
            href="/applications"
            ref={(el) => {
              tabRefs.current["/applications"] = el;
            }}
            className={isApplications ? "navtab active" : "navtab"}
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
            ref={(el) => {
              tabRefs.current["/library"] = el;
            }}
            className={isLibrary ? "navtab active" : "navtab"}
            aria-current={isLibrary ? "page" : undefined}
            onClick={() => libraryIconRef.current?.startAnimation()}
            {...tabHoverHandlers("/library")}
          >
            <BlocksIcon ref={libraryIconRef} />
            <span>Library</span>
          </Link>
          <Link
            href="/"
            ref={(el) => {
              tabRefs.current["/"] = el;
            }}
            className={isAgent ? "navtab active" : "navtab"}
            aria-current={isAgent ? "page" : undefined}
            onClick={() => agentIconRef.current?.startAnimation()}
            {...tabHoverHandlers("/")}
          >
            <AtomIcon ref={agentIconRef} />
            <span>Agent</span>
          </Link>
          <Link
            href="/settings"
            ref={(el) => {
              tabRefs.current["/settings"] = el;
            }}
            className={isProfile ? "navtab active" : "navtab"}
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
