import { NextResponse } from "next/server";
import { auth } from "@/auth";

// Optimistic auth gate (reads the session cookie only). Real authorization
// happens in the backend on every API call.
export default auth((req) => {
  const signedIn = Boolean(req.auth?.user);
  const { pathname } = req.nextUrl;
  const onLogin = pathname === "/login";

  if (!signedIn && !onLogin) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    return NextResponse.redirect(url);
  }
  if (signedIn && onLogin) {
    const url = req.nextUrl.clone();
    url.pathname = "/";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
});

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
