import { Button } from "@/components/ui/button";
import { Emblem } from "@/components/ui/emblem";

export default function NotFound() {
  return (
    <div className="relative flex min-h-[70vh] flex-col items-center justify-center overflow-hidden px-6 pt-[var(--header-height)] text-center">
      <div className="grid-lines absolute inset-0 opacity-60" aria-hidden />
      <div className="relative">
        <Emblem className="mx-auto w-14" />
        <p className="mono-label mt-8 text-elysium">Error 404</p>
        <h1 className="mt-3 font-[family-name:var(--font-display)] text-4xl font-semibold tracking-tight text-navy sm:text-5xl">
          Page not found
        </h1>
        <p className="mx-auto mt-4 max-w-md text-ink/60">
          The page you&rsquo;re looking for doesn&rsquo;t exist or may have moved.
          Let&rsquo;s get you back on track.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Button href="/">Return Home</Button>
          <Button href="/research-materials" variant="secondary">
            View Research Materials
          </Button>
        </div>
      </div>
    </div>
  );
}
