import * as React from "react";
import { Button } from "./button";
import { AmbientEmblem } from "./emblem";
import { Reveal } from "./reveal";

/** Dark premium CTA band with an ambient emblem in the background. */
export function CtaSection({
  eyebrow = "Get started",
  title,
  description,
  primary,
  secondary,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  primary: { label: string; href: string };
  secondary?: { label: string; href: string };
}) {
  return (
    <section className="relative overflow-hidden bg-navy py-20 lg:py-28">
      <AmbientEmblem className="left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2" />
      <div className="glow-soft absolute inset-x-0 top-0 h-40 opacity-60" aria-hidden />
      <div className="container-el relative">
        <Reveal className="mx-auto flex max-w-3xl flex-col items-center text-center">
          <div className="flex items-center gap-3">
            <span className="h-px w-8 bg-elysium" aria-hidden />
            <span className="mono-label text-elysium/90">{eyebrow}</span>
            <span className="h-px w-8 bg-elysium" aria-hidden />
          </div>
          <h2 className="mt-5 font-[family-name:var(--font-display)] text-balance text-3xl font-semibold leading-[1.1] tracking-tight text-white sm:text-4xl lg:text-5xl">
            {title}
          </h2>
          {description && (
            <p className="mt-5 max-w-xl text-base leading-relaxed text-white/65 sm:text-lg">
              {description}
            </p>
          )}
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <Button href={primary.href} size="lg">
              {primary.label}
            </Button>
            {secondary && (
              <Button href={secondary.href} variant="dark" size="lg">
                {secondary.label}
              </Button>
            )}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
