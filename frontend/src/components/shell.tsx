"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="NextOffer home"><span className="brand-mark">N</span>NextOffer<span className="brand-dot">.</span></Link>
        <p className="sidebar-caption">YOUR NEXT CHAPTER</p>
        <nav aria-label="Main navigation">
          <Link className={pathname === "/" ? "nav-link active" : "nav-link"} href="/" aria-current={pathname === "/" ? "page" : undefined}><span aria-hidden="true">↗</span>Chat</Link>
          <Link className={pathname === "/settings" ? "nav-link active" : "nav-link"} href="/settings" aria-current={pathname === "/settings" ? "page" : undefined}><span aria-hidden="true">⚙</span>Settings</Link>
        </nav>
        <div className="sidebar-bottom"><div className="connection-dot" /><span>Google not connected</span><Link href="/settings">Set up →</Link></div>
      </aside>
      <div className="workspace">
        <header className="topbar"><span>Your job search, a little lighter.</span><button className="button secondary" disabled title="Connect Google and select a spreadsheet in a future step">Open Google Sheet ↗</button></header>
        {children}
      </div>
    </div>
  );
}
