import { requireUser } from "@/lib/session";

export default async function LibraryPage() {
  await requireUser();
  return <main className="library-blank" />;
}
