import * as React from "react";
import { Suspense } from "react";
import type { Metadata } from "next";
import { Mail, Building2, FileText, LifeBuoy } from "lucide-react";
import { PageHero } from "@/components/ui/page-hero";
import { ContactPageClient } from "@/components/forms/contact-page-client";
import { LegalNotice } from "@/components/ui/legal-notice";
import { Skeleton } from "@/components/ui/states";
import { pageMetadata } from "@/lib/metadata";
import { company } from "@/data/company";

export const metadata: Metadata = pageMetadata({
  title: "Contact & Documentation Requests",
  description:
    "Contact Elysium Bio Labs for general inquiries, wholesale or institutional requests, documentation, order support, or product information.",
  path: "/contact",
});

const channels = [
  {
    icon: Mail,
    title: "General inquiries",
    body: "Questions about materials, documentation, or the company.",
  },
  {
    icon: Building2,
    title: "Wholesale & institutional",
    body: "Volume, institutional, or recurring research supply.",
  },
  {
    icon: FileText,
    title: "Documentation requests",
    body: "Request batch documentation for a specific material.",
  },
  {
    icon: LifeBuoy,
    title: "Order support",
    body: "Help with an existing inquiry or order.",
  },
];

export default function ContactPage() {
  return (
    <>
      <PageHero
        eyebrow="Contact"
        title="Speak with the Elysium team."
        description="Choose the inquiry type that fits your request. Documentation requests are routed to the records tied to the batch you reference."
        breadcrumbs={[{ label: "Home", href: "/" }, { label: "Contact" }]}
      />

      <section className="py-14 lg:py-20">
        <div className="container-el grid gap-12 lg:grid-cols-[1fr_1.3fr] lg:gap-16">
          {/* Left: channels + info */}
          <div>
            <h2 className="mono-label text-elysium">How we can help</h2>
            <ul className="mt-6 space-y-5">
              {channels.map((c) => (
                <li key={c.title} className="flex gap-4">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-soft">
                    <c.icon className="h-5 w-5 text-elysium" aria-hidden />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-navy">
                      {c.title}
                    </h3>
                    <p className="mt-0.5 text-sm text-ink/60">{c.body}</p>
                  </div>
                </li>
              ))}
            </ul>

            <div className="mt-8 rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-cool/60 p-6">
              <p className="mono-label text-ink/50">Direct</p>
              <dl className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-ink/55">Inquiries</dt>
                  <dd className="font-medium text-navy">{company.email}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-ink/55">Support</dt>
                  <dd className="font-medium text-navy">{company.supportEmail}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-ink/55">Region</dt>
                  <dd className="font-medium text-navy">{company.region}</dd>
                </div>
              </dl>
              <p className="mt-3 border-t border-[color:var(--color-border-grey)] pt-3 text-xs text-ink/45">
                Contact details are editable placeholders pending confirmation.
              </p>
            </div>
          </div>

          {/* Right: form */}
          <div>
            <div className="rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white p-6 shadow-[var(--shadow-card)] sm:p-8">
              <Suspense
                fallback={
                  <div className="space-y-4">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Skeleton key={i} className="h-11 w-full" />
                    ))}
                  </div>
                }
              >
                <ContactPageClient />
              </Suspense>
            </div>
            <LegalNotice className="mt-6">
              Elysium Bio Labs materials are supplied for laboratory, analytical,
              and research purposes only — not for human or veterinary use.
            </LegalNotice>
          </div>
        </div>
      </section>
    </>
  );
}
