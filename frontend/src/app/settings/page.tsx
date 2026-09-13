import { Suspense } from "react";
import { requireUser } from "@/lib/session";
import { SignOut } from "@/components/sign-out";
import { GoogleConnectionCard } from "@/components/google-connection-card";
import { SpreadsheetCard } from "@/components/spreadsheet-card";
import { ScanCard } from "@/components/scan-card";
import { AutoScanCard } from "@/components/auto-scan-card";

export default async function SettingsPage() {
  const user = await requireUser();
  return (
    <main className="settings-page">
      <div className="page-heading"><h1>Profile</h1></div>
      <section className="settings-card"><div className="card-title"><h3><span>NextOffer account</span></h3><SignOut /></div><p className="account-email">{user.email}</p></section>
      <div className="settings-intro"><span className="eyebrow">MAKE IT YOURS</span><h2>A home for your job search.</h2><p>Connect your account and choose where your applications will live.</p></div>
      <Suspense>
        <GoogleConnectionCard />
      </Suspense>
      <SpreadsheetCard />
      <ScanCard />
      <AutoScanCard />
      <p className="settings-footer">Google connection, Sheets sync, manual Gmail scans, and scheduled automatic scans are all live. Job-link analysis works now — try it in Agent.</p>
    </main>
  );
}
