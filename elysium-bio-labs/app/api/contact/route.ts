import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";
import { contactSchema } from "@/lib/validation";

/* ==========================================================================
   Contact / documentation-request API route
   --------------------------------------------------------------------------
   - Validates submissions server-side with the shared Zod schema.
   - Rejects honeypot hits silently (returns success to the bot).
   - Applies a lightweight in-memory rate limit (structure ready to swap for
     a shared store such as Upstash/Redis in production).
   - In development, logs submissions to ./.logs/inquiries.log.

   TO CONNECT AN EMAIL PROVIDER:
   Implement `deliverInquiry` below. Examples for Resend and SendGrid are
   included as comments. Set the relevant API key in the environment.
   ========================================================================== */

// --- Simple in-memory rate limiter (per server instance) -------------------
// NOTE: replace with a shared store (e.g. Upstash Redis) for multi-instance
// deployments. This is intentionally minimal but structured for extension.
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX = 5;
const hits = new Map<string, { count: number; resetAt: number }>();

function rateLimit(key: string): boolean {
  const now = Date.now();
  const entry = hits.get(key);
  if (!entry || now > entry.resetAt) {
    hits.set(key, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }
  if (entry.count >= RATE_LIMIT_MAX) return false;
  entry.count += 1;
  return true;
}

function clientKey(req: Request): string {
  const fwd = req.headers.get("x-forwarded-for");
  return fwd?.split(",")[0]?.trim() || "unknown";
}

async function deliverInquiry(
  data: Record<string, unknown>,
): Promise<void> {
  // --- Development: append to a local log file ---
  if (process.env.NODE_ENV !== "production") {
    const dir = path.join(process.cwd(), ".logs");
    await fs.mkdir(dir, { recursive: true });
    const line =
      JSON.stringify({ receivedAt: new Date().toISOString(), ...data }) + "\n";
    await fs.appendFile(path.join(dir, "inquiries.log"), line, "utf8");
    return;
  }

  // --- Production: connect a provider here. Examples: ---
  //
  // Resend:
  //   const { Resend } = await import("resend");
  //   const resend = new Resend(process.env.RESEND_API_KEY);
  //   await resend.emails.send({
  //     from: "Elysium Bio Labs <inquiries@yourdomain.com>",
  //     to: process.env.CONTACT_NOTIFICATION_EMAIL!,
  //     subject: `New inquiry: ${data.inquiryType}`,
  //     text: JSON.stringify(data, null, 2),
  //   });
  //
  // SendGrid:
  //   const sg = await import("@sendgrid/mail");
  //   sg.setApiKey(process.env.SENDGRID_API_KEY!);
  //   await sg.send({ to: ..., from: ..., subject: ..., text: ... });
  //
  // Until a provider is wired up in production, we log to the server console
  // so submissions are never silently lost.
  console.info("[contact] inquiry received", data);
}

export async function POST(req: Request) {
  // Rate limit
  if (!rateLimit(clientKey(req))) {
    return NextResponse.json(
      { ok: false, message: "Too many requests. Please try again shortly." },
      { status: 429 },
    );
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json(
      { ok: false, message: "Invalid request body." },
      { status: 400 },
    );
  }

  const parsed = contactSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      {
        ok: false,
        message: "Please check the form and try again.",
        issues: parsed.error.flatten().fieldErrors,
      },
      { status: 422 },
    );
  }

  // Honeypot — pretend success so bots don't learn anything.
  if (parsed.data.company_website) {
    return NextResponse.json({ ok: true });
  }

  // Strip honeypot and consent flag before delivery; keep the rest.
  const payload = { ...parsed.data };
  delete (payload as Partial<typeof payload>).company_website;
  delete (payload as Partial<typeof payload>).consent;

  try {
    await deliverInquiry(payload);
  } catch (err) {
    console.error("[contact] delivery failed", err);
    return NextResponse.json(
      { ok: false, message: "We could not record your inquiry. Please try again." },
      { status: 500 },
    );
  }

  return NextResponse.json({ ok: true });
}
