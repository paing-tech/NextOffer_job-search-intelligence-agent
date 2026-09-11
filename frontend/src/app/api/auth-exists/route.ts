const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

/** Public check used by the progressive login form — no session yet, so this
 * can't go through /api/backend/*. Forwards straight to the backend. */
export async function POST(req: Request) {
  const body = await req.text();
  const upstream = await fetch(`${BACKEND_URL}/auth/exists`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  });
  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}
