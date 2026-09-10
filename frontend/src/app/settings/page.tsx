import { requireUser } from "@/lib/session";
import { SignOut } from "@/components/sign-out";

export default async function SettingsPage() {
  const user = await requireUser();
  return (
    <main className="settings-page">
      <div className="page-heading"><h1>Settings</h1></div>
      <section className="settings-card"><div className="card-title"><h3><span>NextOffer account</span></h3><SignOut /></div><p className="account-email">{user.email}</p></section>
      <div className="settings-intro"><span className="eyebrow">MAKE IT YOURS</span><h2>A home for your job search.</h2><p>Connect your account and choose where your applications will live.</p></div>
      <section className="settings-card" aria-labelledby="google-title"><div className="card-title"><h3 id="google-title">01 <span>Google account</span></h3><span className="status">Not connected</span></div><p>Your Google connection will let NextOffer read application emails and update your selected spreadsheet.</p><button className="button primary" disabled>Connect Google</button><small>Gmail and Sheets authorization will be added in the next milestone.</small></section>
      <section className="settings-card" aria-labelledby="sheet-title"><div className="card-title"><h3 id="sheet-title">02 <span>Tracking spreadsheet</span></h3></div><p>Your applications will be available in Google Sheets. Connect Google first, then choose or create a spreadsheet.</p><label htmlFor="spreadsheet">Google Sheet</label><select id="spreadsheet" disabled defaultValue=""><option value="">Connect Google to select a spreadsheet</option></select></section>
      <section className="settings-card" aria-labelledby="scan-title"><div className="card-title"><h3 id="scan-title">03 <span>Automatic email scans</span></h3><span className="status">Not active</span></div><p>Once connected, scans will run on the server even when you close this app.</p><div className="scan-options"><label htmlFor="automatic"><input id="automatic" type="checkbox" disabled /> Enable automatic scans</label><label htmlFor="frequency">Scan frequency<select id="frequency" disabled defaultValue="30"><option value="30">Every 30 minutes (planned)</option></select></label></div><div className="sync-details"><span>Last scan</span><strong>No scans yet</strong></div></section>
      <p className="settings-footer">Google connection and email scans arrive in the next milestone. Job-link analysis works now — try it in Chat.</p>
    </main>
  );
}
