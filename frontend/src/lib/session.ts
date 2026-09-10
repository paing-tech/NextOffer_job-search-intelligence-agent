import { redirect } from "next/navigation";
import { auth } from "@/auth";

/** Server-side guard for pages/layouts. Redirects to /login when signed out. */
export async function requireUser() {
  const session = await auth();
  if (!session?.user?.id) redirect("/login");
  return session.user;
}
