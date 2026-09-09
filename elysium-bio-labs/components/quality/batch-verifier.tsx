"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, ShieldCheck, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LegalNotice } from "@/components/ui/legal-notice";
import { products } from "@/data/products";

type Result = {
  batch: string;
  material: string;
  identity: string;
  purity: string;
  method: string;
  status: string;
} | null;

/**
 * Batch verification tool. Returns a CLEARLY LABELLED DEMONSTRATION result.
 * It does not represent a real verification service — wire this to a real
 * documents source before presenting results as authoritative.
 */
export function BatchVerifier() {
  const [value, setValue] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<Result>(null);
  const [searched, setSearched] = React.useState(false);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const query = value.trim();
    if (!query) return;
    setLoading(true);
    setSearched(true);
    // Simulated lookup — always a demonstration response.
    setTimeout(() => {
      const match = products.find(
        (p) =>
          p.batchNumber.toLowerCase().includes(query.toLowerCase()) ||
          p.name.toLowerCase() === query.toLowerCase(),
      );
      setResult({
        batch: query,
        material: match?.name ?? "Demonstration material",
        identity: "Consistent with reference (sample)",
        purity: "≥ 98% (sample value)",
        method: "HPLC · MS (sample)",
        status: "Demonstration record",
      });
      setLoading(false);
    }, 650);
  };

  return (
    <div className="rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white p-6 shadow-[var(--shadow-card)] sm:p-8">
      <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink/40"
            aria-hidden
          />
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Enter a batch number, e.g. ELB-RETA-0000"
            aria-label="Batch number"
            className="h-12 w-full rounded-[var(--radius-sm)] border border-[color:var(--color-border-grey)] bg-white pl-10 pr-4 text-sm text-navy outline-none transition-colors placeholder:text-ink/40 focus:border-elysium"
          />
        </div>
        <Button type="submit" size="lg" disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Checking…
            </>
          ) : (
            "Verify Batch"
          )}
        </Button>
      </form>

      <AnimatePresence mode="wait">
        {searched && result && !loading && (
          <motion.div
            key={result.batch}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="mt-6"
          >
            <div className="mb-4 flex items-center gap-2 rounded-[var(--radius-sm)] bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700">
              <ShieldCheck className="h-4 w-4" aria-hidden />
              Demonstration result — not a real verification record
            </div>
            <dl className="grid gap-px overflow-hidden rounded-[var(--radius-md)] border border-[color:var(--color-border-grey)] bg-[color:var(--color-border-grey)] sm:grid-cols-2">
              {[
                ["Batch reference", result.batch],
                ["Material", result.material],
                ["Identity", result.identity],
                ["Reported purity", result.purity],
                ["Analytical method", result.method],
                ["Record status", result.status],
              ].map(([label, val]) => (
                <div key={label} className="bg-white px-4 py-3">
                  <dt className="mono-label text-ink/45">{label}</dt>
                  <dd className="mt-1 text-sm font-medium text-navy">{val}</dd>
                </div>
              ))}
            </dl>
          </motion.div>
        )}
      </AnimatePresence>

      <LegalNotice variant="sample" className="mt-6">
        This tool returns a clearly labelled demonstration result for any input.
        It is not connected to a real documents database. Replace it with a
        verified lookup, backed by real batch records, before launch.
      </LegalNotice>
    </div>
  );
}
