"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";
import type { Product } from "@/data/products";
import { SpecTable } from "@/components/ui/spec-table";
import { DocumentationCard } from "@/components/ui/documentation-card";
import { LegalNotice } from "@/components/ui/legal-notice";
import { ContactForm } from "@/components/forms/contact-form";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "specifications", label: "Specifications" },
  { id: "documentation", label: "Documentation" },
  { id: "handling", label: "Handling" },
  { id: "disclaimer", label: "Disclaimer" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function ProductDetailTabs({ product }: { product: Product }) {
  const [active, setActive] = React.useState<TabId>("overview");

  return (
    <div>
      {/* Anchored tab navigation */}
      <div
        role="tablist"
        aria-label="Product information"
        className="sticky top-[var(--header-height)] z-10 -mx-5 mb-8 flex gap-1 overflow-x-auto rail-scroll border-b border-[color:var(--color-border-grey)] bg-white/85 px-5 backdrop-blur-md"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={active === tab.id}
            aria-controls={`panel-${tab.id}`}
            id={`tab-${tab.id}`}
            onClick={() => setActive(tab.id)}
            className={cn(
              "relative whitespace-nowrap px-4 py-3.5 text-sm font-medium transition-colors",
              active === tab.id
                ? "text-elysium"
                : "text-ink/55 hover:text-navy",
            )}
          >
            {tab.label}
            {active === tab.id && (
              <motion.span
                layoutId="tab-underline"
                className="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-elysium"
              />
            )}
          </button>
        ))}
      </div>

      {/* Panels */}
      <div className="min-h-[16rem]">
        {active === "overview" && (
          <Panel id="overview">
            <h2 className="text-xl font-semibold text-navy">Product overview</h2>
            <p className="mt-3 leading-relaxed text-ink/70">
              {product.description}
            </p>
            <p className="mt-4 leading-relaxed text-ink/70">
              {product.name} is supplied as a research reference material within
              the {product.category.toLowerCase()} category. It is presented with
              batch-level documentation to support method development, comparative
              study, and analytical workflows. All figures shown on this site are
              clearly marked as sample data until verified documents are attached.
            </p>
          </Panel>
        )}

        {active === "specifications" && (
          <Panel id="specifications">
            <h2 className="mb-4 text-xl font-semibold text-navy">
              Technical specifications
            </h2>
            <SpecTable
              rows={[
                { label: "Research category", value: product.category },
                { label: "Presentation", value: product.presentation },
                {
                  label: "Molecular formula",
                  value: product.molecularFormula,
                  mono: true,
                },
                {
                  label: "Molecular weight",
                  value: product.molecularWeight,
                  mono: true,
                },
                {
                  label: "Batch number",
                  value: product.batchNumber,
                  mono: true,
                },
              ]}
            />
            <LegalNotice variant="sample" className="mt-5">
              Molecular data is provided for identification and reference. Batch
              numbers shown are sample identifiers — replace with verified batch
              references before publishing.
            </LegalNotice>
          </Panel>
        )}

        {active === "documentation" && (
          <Panel id="documentation">
            <h2 className="mb-4 text-xl font-semibold text-navy">
              Batch documentation
            </h2>
            <DocumentationCard
              product={{
                ...product,
                reportedPurity: "≥ 98% (sample value)",
                analyticalMethod: "HPLC · MS (sample)",
                documentationStatus: product.documentationAvailable
                  ? "Available on request (demonstration)"
                  : "Pending",
              }}
            />
          </Panel>
        )}

        {active === "handling" && (
          <Panel id="handling">
            <h2 className="mb-4 text-xl font-semibold text-navy">
              Handling & storage
            </h2>
            <div className="grid gap-5 sm:grid-cols-2">
              <InfoBlock title="Storage information">
                {product.storageInformation}
              </InfoBlock>
              <InfoBlock title="Handling information">
                {product.handlingInformation}
              </InfoBlock>
            </div>
          </Panel>
        )}

        {active === "disclaimer" && (
          <Panel id="disclaimer">
            <h2 className="mb-4 text-xl font-semibold text-navy">Disclaimer</h2>
            <div className="flex items-start gap-3 rounded-[var(--radius-md)] border border-amber-200 bg-amber-50/70 px-5 py-4">
              <AlertTriangle
                className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600"
                aria-hidden
              />
              <div className="text-sm leading-relaxed text-amber-900">
                <p className="font-semibold">Not for human or veterinary use.</p>
                <p className="mt-1.5">
                  This material is supplied exclusively for laboratory,
                  analytical, and research purposes. It is not intended for human
                  or veterinary consumption, diagnosis, treatment, prevention, or
                  therapeutic use. No dosing, administration, or clinical guidance
                  is provided.
                </p>
              </div>
            </div>
            <p className="mt-4 text-sm text-ink/55">
              Compliance with applicable laws and institutional requirements is
              the responsibility of the purchaser.
            </p>
          </Panel>
        )}
      </div>
    </div>
  );
}

function Panel({ id, children }: { id: TabId; children: React.ReactNode }) {
  return (
    <motion.section
      id={`panel-${id}`}
      role="tabpanel"
      aria-labelledby={`tab-${id}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.section>
  );
}

function InfoBlock({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[color:var(--color-border-grey)] bg-white p-5">
      <h3 className="mono-label text-elysium">{title}</h3>
      <p className="mt-3 text-sm leading-relaxed text-ink/70">{children}</p>
    </div>
  );
}

/** Documentation-request form scoped to a product (compact variant). */
export function ProductInquiryForm({ product }: { product: Product }) {
  return (
    <ContactForm
      compact
      defaultInquiryType="Documentation Request"
      defaultProductOrBatch={`${product.name} — ${product.batchNumber}`}
    />
  );
}
