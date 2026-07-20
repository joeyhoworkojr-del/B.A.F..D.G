import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/metadata";

// Required so this route can be statically exported (GitHub Pages build).
export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
