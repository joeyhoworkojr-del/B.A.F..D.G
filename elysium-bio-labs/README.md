# Elysium Bio Labs

A premium, production-quality marketing and catalogue website for **Elysium Bio Labs**, a research-focused biosciences company supplying high-purity laboratory materials for qualified research applications.

Built with Next.js 15 (App Router), TypeScript, Tailwind CSS v4, Framer Motion, React Hook Form, and Zod.

> ⚠️ **Compliance reminder:** This site includes legal, quality, and product copy that is **placeholder content and not legal advice**. Sample data (batch numbers, purity figures, certificates) is clearly labelled as demonstration content. **Have all legal, regulatory, and product-claim copy reviewed by qualified Canadian regulatory counsel before launch.** See [Compliance](#compliance-review-reminder) below.

---

## Setup

Requirements: **Node.js 18.18+** (Node 20+ recommended) and npm.

```bash
npm install
npm run dev
```

Open <http://localhost:3000>.

### Scripts

| Script | Purpose |
| --- | --- |
| `npm run dev` | Start the development server |
| `npm run build` | Production build |
| `npm run start` | Serve the production build |
| `npm run lint` | ESLint |
| `npm run typecheck` | TypeScript type checking (`tsc --noEmit`) |

---

## Environment Variables

Copy `.env.example` to `.env.local` and adjust as needed. **None are required for local development.**

| Variable | Required | Description |
| --- | --- | --- |
| `NEXT_PUBLIC_SITE_URL` | Recommended | Public base URL used for canonical URLs, sitemap, and Open Graph tags. Defaults to `http://localhost:3000`. |
| `RESEND_API_KEY` | Optional | Key for the Resend email provider (see [Connecting an email provider](#connecting-an-email-provider)). |
| `SENDGRID_API_KEY` | Optional | Key for SendGrid, if used instead. |
| `CONTACT_NOTIFICATION_EMAIL` | Optional | Destination address for inquiry notifications in production. |

---

## Project Structure

```
app/
  layout.tsx                 Root layout: fonts, header, footer, metadata, schema
  page.tsx                   Home page (11 sections)
  research-materials/        Catalogue + dynamic product detail ([slug])
  quality/                   Quality process + batch verification tool
  about/                     Company / editorial page
  resources/                 Resource center + article template ([slug])
  contact/                   Contact & documentation requests
  legal/                     Legal index + dynamic policy pages ([slug])
  api/contact/route.ts       Inquiry API (validation, honeypot, rate limit, logging)
  sitemap.ts, robots.ts      SEO
  loading.tsx, error.tsx, not-found.tsx

components/
  layout/                    Header, Footer, CursorGlow, PageTransition
  ui/                        Buttons, badges, cards, timeline, emblem, states, etc.
  home/                      Home page sections
  products/                  Product card, catalogue, product detail tabs
  quality/                   Batch verifier
  forms/                     Contact form + page client
  resources/                 Resource card + library

data/
  products.ts                Product catalogue (single source of truth)
  resources.ts               Resource articles
  company.ts                 Company facts + owner TODO list
  legal.ts                   Legal page copy

lib/
  validation.ts              Zod schemas (shared client + server)
  metadata.ts                Metadata + JSON-LD schema helpers
  utils.ts                   cn(), readingTime()

public/
  elysium-logo.png           Supplied brand logo
  favicon.svg
```

---

## Editing Content

All business content lives in **centralized data files** under `data/` so it can be edited in one place (and later swapped for a CMS — see comments in each file).

### Editing products

Edit `data/products.ts`. Each product follows this shape:

```ts
{
  slug,                    // URL segment: /research-materials/<slug>
  name, shortName,
  category,                // one of the ResearchCategory union values
  description,
  presentation,            // e.g. "10 mg lyophilized · single vial"
  status,                  // "in-stock" | "limited" | "backorder"
  batchNumber,             // SAMPLE identifier — replace before launch
  documentationAvailable,  // boolean
  featured,                // shown on the home page grid
  molecularFormula, molecularWeight,
  storageInformation, handlingInformation,
  addedOn,                 // ISO date, used for "newest" sorting
}
```

Add a category by extending the `ResearchCategory` union and the `CATEGORIES` array.

> Do **not** add dosing, protocols, cycles, injection guidance, personal-use
> instructions, or medical/therapeutic claims. The UI is intentionally built to
> present research and documentation details only.

### Editing resources

Edit `data/resources.ts`. Articles are structured as `sections` of `{ heading, paragraphs }`. Reading time is calculated automatically.

### Editing company facts

Edit `data/company.ts`. Fields marked `[TO BE CONFIRMED]` are intentional placeholders. The `OWNER_TODO` array lists factual details still required (also reproduced [below](#business-information-still-required)).

### Editing legal copy

Edit `data/legal.ts`. Every page renders a visible "not legal advice" notice.

---

## Replacing Sample Documentation

The site ships with a **demonstration** certificate-of-analysis interface and a
**demonstration** batch-verification tool. Both are clearly labelled as samples.

To replace them with real documents:

1. **Product batch data** — update `batchNumber` and molecular fields in
   `data/products.ts`, and replace the sample purity/method strings passed to
   `DocumentationCard` (search for `reportedPurity` / `analyticalMethod`).
2. **Downloadable documents** — place PDFs under `public/documents/` and wire a
   `documentUrl` into `DocumentationCard` (`components/ui/documentation-card.tsx`)
   to enable the "Download document" button (currently disabled).
3. **Batch verification** — `components/quality/batch-verifier.tsx` currently
   returns a labelled demonstration result for any input. Replace the simulated
   lookup with a real query against your documents source, and remove the
   "demonstration" labelling only once results are authoritative.

> Never present sample values as verified analytical results. Keep the
> demonstration labelling until real data is wired in.

---

## Connecting an Email Provider

Inquiry submissions are handled by `app/api/contact/route.ts`:

- **Development:** submissions are validated and appended to `./.logs/inquiries.log` (git-ignored).
- **Production:** implement delivery in the `deliverInquiry` function. Commented
  examples for **Resend** and **SendGrid** are included inline.

Example (Resend):

```ts
const { Resend } = await import("resend");
const resend = new Resend(process.env.RESEND_API_KEY);
await resend.emails.send({
  from: "Elysium Bio Labs <inquiries@yourdomain.com>",
  to: process.env.CONTACT_NOTIFICATION_EMAIL!,
  subject: `New inquiry: ${data.inquiryType}`,
  text: JSON.stringify(data, null, 2),
});
```

Then `npm install resend` (or `@sendgrid/mail`) and set the relevant env vars.

**Anti-spam** is already in place: a honeypot field, server-side Zod validation,
and a lightweight in-memory rate limiter. For multi-instance deployments,
replace the in-memory limiter with a shared store (e.g. Upstash Redis) — the
code is structured for that swap.

---

## Deployment

The app is a standard Next.js 15 project and deploys cleanly to any Node host.

### Vercel (recommended)

1. Push this repository to Git.
2. Import the project in Vercel.
3. Set `NEXT_PUBLIC_SITE_URL` (and email provider vars if used).
4. Deploy — build command `next build`, output handled automatically.

### GitHub Pages (free, no external account)

A workflow at `.github/workflows/deploy-elysium-pages.yml` builds the site as a
static export and publishes it to GitHub Pages. It enables Pages itself
(`actions/configure-pages` with `enablement: true`), so **no manual repo setting
is required** — it just needs to run on the default branch. Once this branch is
merged to `main`, the site auto-deploys to:

```
https://<owner>.github.io/<repo>/
```

You can also trigger it manually from the repo's **Actions** tab → *Deploy
Elysium site to GitHub Pages* → **Run workflow** (on `main`).

**Static-export trade-off:** GitHub Pages serves static files only, so the
server-side contact API (`/api/contact`) is not available there. In the static
build the contact form falls back to opening the visitor's email client
(`mailto:`) pre-filled with their message. Deploying to **Vercel** (above) keeps
the full server-side API. Static mode is controlled by the `STATIC_EXPORT` /
`NEXT_PUBLIC_STATIC_EXPORT` / `PAGES_BASE_PATH` / `NEXT_PUBLIC_BASE_PATH` env
vars — see `next.config.ts` and the workflow.

### Self-hosted / Docker

```bash
npm run build
npm run start   # serves on PORT (default 3000)
```

Put a reverse proxy (nginx/Caddy) in front for TLS. Ensure `NEXT_PUBLIC_SITE_URL`
matches the public origin so canonical URLs and the sitemap are correct.

---

## Accessibility & Performance

- Semantic HTML, logical heading hierarchy, visible focus states, skip link.
- Keyboard-accessible navigation, tabs, and filters; labelled form fields.
- `prefers-reduced-motion` respected globally; cursor glow disabled on touch.
- Fonts loaded via `next/font` with `display: swap`; images via `next/image`.
- Visuals are CSS/SVG (no heavy 3D libraries) to keep the bundle light.

---

## Compliance Review Reminder

**The generated legal, regulatory, and quality copy is placeholder content and is
NOT legal advice.** It is not guaranteed to satisfy Canadian (or any other) legal
or regulatory requirements. The Research-Use-Only disclaimer does **not**, by
itself, guarantee regulatory compliance.

Before launching:

- Have **all** legal pages (`data/legal.ts`) reviewed by **qualified Canadian
  regulatory counsel**.
- Confirm product presentation and claims comply with applicable regulations for
  research materials in your jurisdiction(s).
- Replace all sample/demonstration data with verified records, or keep it clearly
  labelled as demonstration.

This reminder is also embedded in the source: see `data/legal.ts` and the visible
notices rendered on every legal and demonstration surface.

---

## Business Information Still Required

The following factual details are **not** fabricated and must be supplied by the
owner before launch (also tracked in `data/company.ts` → `OWNER_TODO`):

- Registered legal entity name and business number
- Registered address and jurisdiction of incorporation
- Verified contact email and phone number
- Real batch records and analytical results to replace sample data
- Names of any independent laboratories used (only if a relationship exists)
- Any certifications or accreditations actually held (only if genuine)
- Shipping regions, carriers, and handling terms
- Confirmation of the Research-Use-Only sales policy and any eligibility checks

---

_Built as a complete, production-ready implementation. Sample content is
restrained and clearly labelled; no fabricated testimonials, customer counts,
laboratory partnerships, review scores, or medical claims are included._
