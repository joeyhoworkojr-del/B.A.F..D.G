import * as React from "react";
import { ArrowRight } from "lucide-react";
import { resources } from "@/data/resources";
import { ResourceCard } from "@/components/resources/resource-card";
import { SectionHeader } from "@/components/ui/section-header";
import { Button } from "@/components/ui/button";

export function ResourcesPreview() {
  const items = resources.slice(0, 3);
  return (
    <section className="py-20 lg:py-28">
      <div className="container-el">
        <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
          <SectionHeader
            eyebrow="Resources"
            title="Reading for research buyers."
            description="Cautious, professional explainers on analytical documentation — no administration or dosing guidance."
          />
          <Button href="/resources" variant="secondary" className="flex-shrink-0">
            View All Resources
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {items.map((r, i) => (
            <ResourceCard key={r.slug} resource={r} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
