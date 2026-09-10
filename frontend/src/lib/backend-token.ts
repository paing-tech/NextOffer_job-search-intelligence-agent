import "server-only";
import { SignJWT } from "jose";

const secret = new TextEncoder().encode(process.env.AUTH_SECRET ?? "dev-insecure-change-me");

/** Short-lived HS256 token the FastAPI backend verifies with the shared AUTH_SECRET. */
export async function mintBackendToken(user: { id: string; email: string }): Promise<string> {
  return new SignJWT({ email: user.email })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(user.id)
    .setIssuedAt()
    .setExpirationTime("10m")
    .sign(secret);
}
