const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

/** Public sign-up: forwards to the backend, which creates the user + credential. */
export async function POST(req: Request) {
  const body = await req.text();
  const upstream = await fetch(`${BACKEND_URL}/auth/register`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  });
  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}
