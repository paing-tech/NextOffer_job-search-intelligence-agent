import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { mintBackendToken } from "@/lib/backend-token";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

// Full-page navigation only (an <a>/window.location, never fetch()) — the
// browser needs to actually land on Google's consent screen, which a fetch()
// proxy would follow server-side instead of showing the user.
export async function GET(request: Request) {
  const session = await auth();
  if (!session?.user?.id || !session.user.email) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Reused as the OAuth `state` param: a short-lived signed token carrying the
  // user id through Google's redirect, which carries no Authorization header.
  const state = await mintBackendToken({ id: session.user.id, email: session.user.email });
  const url = new URL(`${BACKEND_URL}/google/authorize`);
  url.searchParams.set("state", state);
  return NextResponse.redirect(url);
}
