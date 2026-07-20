import * as React from "react";
import { QrCode, Download, ShieldCheck, FlaskConical } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./button";
import { LegalNotice } from "./legal-notice";
import type { Product } from "@/data/products";

/**
 * Mock Certificate-of-Analysis interface. Clearly labelled as a demonstration.
 * Values are drawn from the product's SAMPLE data; replace with verified
 * documents by wiring `documentUrl` and real analytical fields.
 */
export function DocumentationCard({
  product,
  className,
}: {
  product?: Partial<Product> & {
    reportedPurity?: string;
    analyticalMethod?: string;
    documentationStatus?: string;
  };
  className?: string;
}) {
  const data = {
    name: product?.name ?? "Sample Reference Material",
    batchNumber: product?.batchNumber ?? "ELB-SAMPLE-0000 (sample)",
    molecularFormula: product?.molecularFormula ?? "—",
    molecularWeight: product?.molecularWeight ?? "—",
    reportedPurity: product?.reportedPurity ?? "≥ 98% (sample value)",
    analyticalMethod: product?.analyticalMethod ?? "HPLC · MS (sample)",
    documentationStatus: product?.documentationStatus ?? "Demonstration",
  };

  return (
    <div
      className={cn(
        "overflow-hidden rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white shadow-[var(--shadow-card)]",
        className,
      )}
    >
      {/* header */}
      <div className="flex items-center justify-between border-b border-[color:var(--color-border-grey)] bg-cool/60 px-5 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] bg-navy">
            <FlaskConical className="h-4 w-4 text-white" aria-hidden />
          </div>
          <div>
            <p className="text-sm font-semibold text-navy">
              Certificate of Analysis
            </p>
            <p className="mono-label text-ink/45">Interface demonstration</p>
          </div>
        </div>
        <span className="mono-label rounded-[var(--radius-xs)] bg-amber-100 px-2 py-1 text-amber-700">
          Sample
        </span>
      </div>

      {/* batch overview */}
      <div className="grid grid-cols-2 gap-px bg-[color:var(--color-border-grey)] sm:grid-cols-4">
        {[
          { label: "Material", value: data.name },
          { label: "Batch No.", value: data.batchNumber, mono: true },
          { label: "Formula", value: data.molecularFormula, mono: true },
          { label: "MW", value: data.molecularWeight, mono: true },
        ].map((f) => (
          <div key={f.label} className="bg-white px-4 py-3">
            <p className="mono-label text-ink/45">{f.label}</p>
            <p
              className={cn(
                "mt-1 text-[0.8125rem] font-medium text-navy",
                f.mono && "font-[family-name:var(--font-mono)] text-xs",
              )}
            >
              {f.value}
            </p>
          </div>
        ))}
      </div>

      {/* identity + purity sections */}
      <div className="grid gap-px bg-[color:var(--color-border-grey)] sm:grid-cols-2">
        <DocSection
          title="Identity"
          rows={[
            ["Assessment", "Consistent with reference (sample)"],
            ["Method", "MS · comparative (sample)"],
          ]}
        />
        <DocSection
          title="Purity"
          rows={[
            ["Reported purity", data.reportedPurity],
            ["Analytical method", data.analyticalMethod],
          ]}
        />
      </div>

      {/* verification field */}
      <div className="flex flex-col gap-4 border-t border-[color:var(--color-border-grey)] px-5 py-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-[var(--radius-md)] border border-dashed border-[color:var(--color-border-grey)] bg-cool">
            <QrCode className="h-8 w-8 text-navy/70" aria-hidden />
          </div>
          <div>
            <p className="flex items-center gap-1.5 text-sm font-medium text-navy">
              <ShieldCheck className="h-4 w-4 text-elysium" aria-hidden />
              Document verification
            </p>
            <p className="mono-label mt-1 text-ink/45">
              Status: {data.documentationStatus}
            </p>
          </div>
        </div>
        <Button variant="secondary" size="sm" disabled>
          <Download className="h-4 w-4" aria-hidden />
          Download document
        </Button>
      </div>

      <div className="px-5 pb-5">
        <LegalNotice variant="sample">
          This is an interface demonstration. The values shown are sample data,
          not real analytical results. Replace with verified batch documents
          before publishing.
        </LegalNotice>
      </div>
    </div>
  );
}

function DocSection({
  title,
  rows,
}: {
  title: string;
  rows: [string, string][];
}) {
  return (
    <div className="bg-white px-5 py-4">
      <p className="mono-label mb-3 text-elysium">{title}</p>
      <dl className="space-y-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4 text-sm">
            <dt className="text-ink/55">{label}</dt>
            <dd className="text-right font-medium text-navy">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
