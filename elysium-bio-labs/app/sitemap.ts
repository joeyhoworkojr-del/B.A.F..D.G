import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/metadata";
import { products } from "@/data/products";
import { resources } from "@/data/resources";
import { legalPages } from "@/data/legal";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();

  const staticRoutes = [
    "",
    "/research-materials",
    "/quality",
    "/about",
    "/resources",
    "/contact",
  ].map((path) => ({
    url: `${SITE_URL}${path}`,
    lastModified: now,
    changeFrequency: "monthly" as const,
    priority: path === "" ? 1 : 0.8,
  }));

  const productRoutes = products.map((p) => ({
    url: `${SITE_URL}/research-materials/${p.slug}`,
    lastModified: new Date(p.addedOn),
    changeFrequency: "monthly" as const,
    priority: 0.7,
  }));

  const resourceRoutes = resources.map((r) => ({
    url: `${SITE_URL}/resources/${r.slug}`,
    lastModified: new Date(r.publishedOn),
    changeFrequency: "monthly" as const,
    priority: 0.6,
  }));

  const legalRoutes = legalPages.map((p) => ({
    url: `${SITE_URL}/legal/${p.slug}`,
    lastModified: new Date(p.updated),
    changeFrequency: "yearly" as const,
    priority: 0.3,
  }));

  return [
    ...staticRoutes,
    ...productRoutes,
    ...resourceRoutes,
    ...legalRoutes,
  ];
}
