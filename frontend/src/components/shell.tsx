"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType } from "react";

function BriefcaseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="7.5" width="18" height="12.5" rx="1.6" />
      <path d="M9 7.5V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v1.5" />
      <path d="M3 12h18" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 5h16a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H9l-4 3.5V16H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z" />
    </svg>
  );
}

function ProfileIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="8" r="3.4" />
      <path d="M5 20c1.4-3.6 4-5.4 7-5.4s5.6 1.8 7 5.4" />
    </svg>
  );
}

const TABS: { href: string; label: string; Icon: ComponentType }[] = [
  { href: "/applications", label: "Jobs", Icon: BriefcaseIcon },
  { href: "/", label: "Chat", Icon: ChatIcon },
  { href: "/settings", label: "Profile", Icon: ProfileIcon },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/login" || pathname.startsWith("/auth/")) return <>{children}</>;

  const active = TABS.find((t) => (t.href === "/" ? pathname === "/" : pathname.startsWith(t.href)));

  return (
    <div className="shell">
      <header className="topbar" />

      <div className="content">{children}</div>

      <nav className="bottomnav" aria-label="Primary">
        <div className="bottomnav-inner">
          {TABS.map(({ href, label, Icon }) => {
            const isActive = active?.href === href;
            return (
              <Link
                key={href}
                href={href}
                className={isActive ? "navtab active" : "navtab"}
                aria-current={isActive ? "page" : undefined}
              >
                <Icon />
                <span>{label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
