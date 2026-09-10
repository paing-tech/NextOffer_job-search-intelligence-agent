import { requireUser } from "@/lib/session";
import { ApplicationsList } from "@/components/applications-list";

export default async function ApplicationsPage() {
  await requireUser();
  return (
    <main className="apps-page">
      <div className="page-heading"><h1>Applications</h1></div>
      <ApplicationsList />
    </main>
  );
}
