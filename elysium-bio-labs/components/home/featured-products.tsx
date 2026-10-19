import * as React from "react";
import { ArrowRight } from "lucide-react";
import { getFeaturedProducts } from "@/data/products";
import { ProductCard } from "@/components/products/product-card";
import { SectionHeader } from "@/components/ui/section-header";
import { Button } from "@/components/ui/button";

export function FeaturedProducts() {
  const products = getFeaturedProducts();
  return (
    <section className="py-20 lg:py-28">
      <div className="container-el">
        <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
          <SectionHeader
            eyebrow="Featured Research Materials"
            title="A catalogue built around documentation."
            description="Each material is presented with its research category, available presentation, and batch status — the details that matter to a research buyer."
          />
          <Button
            href="/research-materials"
            variant="secondary"
            className="flex-shrink-0"
          >
            View Complete Catalogue
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>

        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((product, i) => (
            <ProductCard key={product.slug} product={product} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
