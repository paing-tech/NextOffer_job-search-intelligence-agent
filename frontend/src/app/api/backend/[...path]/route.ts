import { auth } from "@/auth";
import { mintBackendToken } from "@/lib/backend-token";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

// BFF proxy: the browser only ever talks to /api/backend/*. We attach a
// short-lived signed token here so the backend token never reaches the client.
async function handler(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  const session = await auth();
  if (!session?.user?.id || !session.user.email) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }

  const { path } = await ctx.params;
  const search = new URL(req.url).search;
  const target = `${BACKEND_URL}/${path.join("/")}${search}`;

  const token = await mintBackendToken({ id: session.user.id, email: session.user.email });
  const headers = new Headers();
  headers.set("authorization", `Bearer ${token}`);
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const accept = req.headers.get("accept");
  if (accept) headers.set("accept", accept);

  const hasBody = req.method !== "GET" && req.method !== "HEAD";
  const upstream = await fetch(target, {
    method: req.method,
    headers,
    body: hasBody ? await req.text() : undefined,
    // @ts-expect-error - Node fetch streaming flag
    duplex: hasBody ? "half" : undefined,
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}

export {
  handler as GET,
  handler as POST,
  handler as PUT,
  handler as PATCH,
  handler as DELETE,
};
