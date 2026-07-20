import type { NextConfig } from "next";

/**
 * Static-export mode (for GitHub Pages) is enabled by setting STATIC_EXPORT=1.
 * In this mode:
 *   - the app is exported as static HTML (`output: "export"`)
 *   - images are unoptimized (no server to optimize them)
 *   - basePath/assetPrefix are set from PAGES_BASE_PATH so assets resolve under
 *     the project-pages sub-path (e.g. /b.a.f..d.g)
 * The API route is excluded from the build by the Pages workflow (it moves
 * app/api aside before building), and the contact form falls back to a mailto
 * link — see components/forms/contact-form.tsx.
 *
 * Normal (server) deploys — e.g. Vercel — ignore all of this and keep the
 * fully functional contact API.
 */
const isStaticExport = process.env.STATIC_EXPORT === "1";
const basePath = process.env.PAGES_BASE_PATH || "";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  ...(isStaticExport
    ? {
        output: "export",
        images: { unoptimized: true },
        basePath: basePath || undefined,
        assetPrefix: basePath || undefined,
        trailingSlash: true,
      }
    : {}),
};

export default nextConfig;
