/**
 * Prefix a public-asset path with the deployment base path.
 *
 * `next/image` and metadata `icons` do not automatically apply `basePath` in a
 * static export, so public assets referenced by string (the logo, favicon)
 * must be prefixed explicitly. NEXT_PUBLIC_BASE_PATH is empty for normal
 * (server) deploys, so this is a no-op there.
 */
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export function asset(path: string): string {
  const clean = path.startsWith("/") ? path : `/${path}`;
  return `${BASE_PATH}${clean}`;
}
