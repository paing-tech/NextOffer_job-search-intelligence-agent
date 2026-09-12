import { Suspense } from "react";
import { requireUser } from "@/lib/session";
import { ApplicationsList } from "@/components/applications-list";

export default async function ApplicationsPage() {
  await requireUser();
  return (
    <main className="apps-page">
      <Suspense fallback={<p className="apps-empty">Loading…</p>}>
        <ApplicationsList />
      </Suspense>
    </main>
  );
}
