import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { Linkedin, Twitter, Microscope } from "lucide-react";
import { company } from "@/data/company";
import { Emblem } from "@/components/ui/emblem";

const columns: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: "Research Materials",
    links: [
      { label: "Full Catalogue", href: "/research-materials" },
      { label: "Metabolic Research", href: "/research-materials?category=Metabolic+Research" },
      { label: "Recovery Research", href: "/research-materials?category=Recovery+Research" },
      { label: "Reference Materials", href: "/research-materials?category=Reference+Materials" },
    ],
  },
  {
    title: "Quality",
    links: [
      { label: "Quality Process", href: "/quality" },
      { label: "Batch Verification", href: "/quality#verification" },
      { label: "Documentation", href: "/quality#documentation" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "/about" },
      { label: "Mission", href: "/about#mission" },
      { label: "Contact", href: "/contact" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Resource Center", href: "/resources" },
      { label: "Analytical Testing", href: "/resources?category=Analytical+Testing" },
      { label: "Quality Documentation", href: "/resources?category=Quality+Documentation" },
    ],
  },
  {
    title: "Support",
    links: [
      { label: "Request Documentation", href: "/contact?type=documentation" },
      { label: "Order Support", href: "/contact?type=order" },
      { label: "Wholesale / Institutional", href: "/contact?type=wholesale" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Research Use Only", href: "/legal/research-use-only" },
      { label: "Privacy Policy", href: "/legal/privacy-policy" },
      { label: "Terms & Conditions", href: "/legal/terms" },
      { label: "Shipping Policy", href: "/legal/shipping-policy" },
      { label: "Refund Policy", href: "/legal/refund-policy" },
      { label: "Documentation Policy", href: "/legal/documentation-policy" },
    ],
  },
];

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="relative overflow-hidden bg-navy text-white">
      <div className="grid-lines-dark absolute inset-0 opacity-40" aria-hidden />
      <div className="container-el relative py-16 lg:py-20">
        {/* Top: brand + columns */}
        <div className="grid gap-12 lg:grid-cols-[1.4fr_3fr]">
          <div>
            <div className="flex items-center gap-3">
              <Emblem className="h-9 w-auto" tone="white" />
              <span className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight">
                Elysium Bio Labs
              </span>
            </div>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-white/60">
              {company.shortDescription}
            </p>
            <div className="mt-6 flex items-center gap-3">
              <SocialLink href={company.social.linkedin} label="LinkedIn">
                <Linkedin className="h-4 w-4" />
              </SocialLink>
              <SocialLink href={company.social.x} label="X">
                <Twitter className="h-4 w-4" />
              </SocialLink>
              <SocialLink href={company.social.researchGate} label="ResearchGate">
                <Microscope className="h-4 w-4" />
              </SocialLink>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
            {columns.map((col) => (
              <div key={col.title}>
                <h3 className="mono-label text-elysium/90">{col.title}</h3>
                <ul className="mt-4 space-y-2.5">
                  {col.links.map((link) => (
                    <li key={link.label}>
                      <Link
                        href={link.href}
                        className="text-sm text-white/65 transition-colors hover:text-white"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Research Use Only statement */}
        <div className="mt-14 rounded-[var(--radius-lg)] border border-white/10 bg-white/[0.03] p-6">
          <p className="mono-label mb-2 text-elysium/90">Research Use Only</p>
          <p className="max-w-4xl text-sm leading-relaxed text-white/60">
            All products and materials presented by Elysium Bio Labs are intended
            exclusively for laboratory, analytical, and research purposes. They
            are not intended for human or veterinary consumption, diagnosis,
            treatment, prevention, or therapeutic use.
          </p>
        </div>

        {/* Bottom bar */}
        <div className="mt-10 flex flex-col gap-4 border-t border-white/10 pt-8 text-sm text-white/50 sm:flex-row sm:items-center sm:justify-between">
          <p>
            © {year} {company.name}. All rights reserved.
          </p>
          <div className="flex flex-wrap gap-x-5 gap-y-2">
            <Link href="/legal/privacy-policy" className="hover:text-white">
              Privacy
            </Link>
            <Link href="/legal/terms" className="hover:text-white">
              Terms
            </Link>
            <Link href="/legal/documentation-policy" className="hover:text-white">
              Documentation
            </Link>
            <Image
              src="/elysium-logo.png"
              alt=""
              width={80}
              height={80}
              className="hidden h-5 w-auto opacity-40 invert sm:block"
              aria-hidden
            />
          </div>
        </div>
      </div>
    </footer>
  );
}

function SocialLink({
  href,
  label,
  children,
}: {
  href: string;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      aria-label={label}
      className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-sm)] border border-white/15 text-white/70 transition-colors hover:border-elysium hover:text-white"
    >
      {children}
    </a>
  );
}
