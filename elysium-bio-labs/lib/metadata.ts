import type { Metadata } from "next";
import { company } from "@/data/company";

/** Public site URL — set NEXT_PUBLIC_SITE_URL in the environment for production. */
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ??
  "http://localhost:3000";

interface PageMetaInput {
  title: string;
  description: string;
  path?: string;
}

/**
 * Build per-page metadata with consistent Open Graph and Twitter tags.
 * `title` is used verbatim (pages that want the brand suffix add it themselves;
 * the root layout provides a title template as a fallback).
 */
export function pageMetadata({
  title,
  description,
  path = "/",
}: PageMetaInput): Metadata {
  const url = `${SITE_URL}${path}`;
  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: {
      type: "website",
      siteName: company.name,
      title,
      description,
      url,
      images: [
        {
          url: "/elysium-logo.png",
          width: 1240,
          height: 1240,
          alt: `${company.name} logo`,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: ["/elysium-logo.png"],
    },
  };
}

/** Organization schema (JSON-LD) for the site footer / home page. */
export function organizationSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: company.name,
    description: company.shortDescription,
    url: SITE_URL,
    logo: `${SITE_URL}/elysium-logo.png`,
    slogan: company.tagline,
    areaServed: company.region,
  };
}

export function breadcrumbSchema(items: { name: string; path: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: item.name,
      item: `${SITE_URL}${item.path}`,
    })),
  };
}
