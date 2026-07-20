/* ==========================================================================
   Elysium Bio Labs — product catalogue (centralized data source)
   --------------------------------------------------------------------------
   Edit products here. Everything on the site (catalogue, product detail,
   featured grid, schema markup) reads from this file.

   NOTE FOR FUTURE CMS INTEGRATION:
   This module is intentionally the single source of truth for product data.
   To connect a headless CMS (Sanity, Payload, Contentful), replace the
   `products` array below with an async fetch and keep the exported helper
   signatures the same so page components do not need to change.

   COMPLIANCE:
   Batch numbers, purity figures, and analytical methods below are clearly
   marked SAMPLE / DEMONSTRATION values. Replace them with verified data
   before publishing. Do not present sample values as real test results.
   ========================================================================== */

export type ProductStatus = "in-stock" | "limited" | "backorder";
export type ResearchCategory =
  | "Metabolic Research"
  | "Recovery Research"
  | "Cellular Research"
  | "Growth-Factor Research"
  | "Longevity Research"
  | "Reference Materials";

export interface Product {
  slug: string;
  name: string;
  shortName: string;
  category: ResearchCategory;
  description: string;
  presentation: string;
  status: ProductStatus;
  /** SAMPLE identifier — replace with verified batch reference before launch. */
  batchNumber: string;
  documentationAvailable: boolean;
  featured: boolean;
  molecularFormula: string;
  molecularWeight: string;
  storageInformation: string;
  handlingInformation: string;
  /** ISO date used only for "newest" sorting in the catalogue. */
  addedOn: string;
}

export const CATEGORIES: ResearchCategory[] = [
  "Metabolic Research",
  "Recovery Research",
  "Cellular Research",
  "Growth-Factor Research",
  "Longevity Research",
  "Reference Materials",
];

export const products: Product[] = [
  {
    slug: "retatrutide",
    name: "Retatrutide",
    shortName: "Retatrutide",
    category: "Metabolic Research",
    description:
      "A multi-receptor peptide reference material supplied for in-vitro and analytical research applications. Provided with batch-level documentation to support method development and comparative study.",
    presentation: "10 mg lyophilized · single vial",
    status: "in-stock",
    batchNumber: "ELB-RETA-0000 (sample)",
    documentationAvailable: true,
    featured: true,
    molecularFormula: "C221H342N46O68",
    molecularWeight: "≈ 4731.3 g/mol",
    storageInformation:
      "Store lyophilized material at -20 °C, protected from light and moisture. Once reconstituted for research use, keep refrigerated and use within the working period defined by the receiving laboratory.",
    handlingInformation:
      "Handle under appropriate laboratory controls using standard personal protective equipment. For laboratory research use only.",
    addedOn: "2026-06-01",
  },
  {
    slug: "bpc-157",
    name: "BPC-157",
    shortName: "BPC-157",
    category: "Recovery Research",
    description:
      "A synthetic peptide sequence provided as a research reference material. Supplied with identity and purity documentation to support recovery-pathway and cellular research workflows.",
    presentation: "5 mg lyophilized · single vial",
    status: "in-stock",
    batchNumber: "ELB-BPC-0000 (sample)",
    documentationAvailable: true,
    featured: true,
    molecularFormula: "C62H98N16O22",
    molecularWeight: "≈ 1419.5 g/mol",
    storageInformation:
      "Store lyophilized material at -20 °C, protected from light and moisture. Reconstituted solutions should be refrigerated and handled per the receiving laboratory's protocols.",
    handlingInformation:
      "Handle under appropriate laboratory controls using standard personal protective equipment. For laboratory research use only.",
    addedOn: "2026-05-18",
  },
  {
    slug: "tb-500",
    name: "TB-500",
    shortName: "TB-500",
    category: "Recovery Research",
    description:
      "A synthetic fragment reference material used in cellular and recovery-pathway research. Supplied with batch documentation and controlled-handling records.",
    presentation: "5 mg lyophilized · single vial",
    status: "limited",
    batchNumber: "ELB-TB5-0000 (sample)",
    documentationAvailable: true,
    featured: true,
    molecularFormula: "C212H350N56O78S",
    molecularWeight: "≈ 4963.4 g/mol",
    storageInformation:
      "Store lyophilized material at -20 °C, protected from light and moisture. Refrigerate reconstituted material and use within the working period defined by the receiving laboratory.",
    handlingInformation:
      "Handle under appropriate laboratory controls using standard personal protective equipment. For laboratory research use only.",
    addedOn: "2026-05-02",
  },
  {
    slug: "ghk-cu",
    name: "GHK-Cu",
    shortName: "GHK-Cu",
    category: "Cellular Research",
    description:
      "A copper-peptide complex reference material for cellular and longevity research. Supplied with identity assessment and purity documentation.",
    presentation: "50 mg lyophilized · single vial",
    status: "in-stock",
    batchNumber: "ELB-GHK-0000 (sample)",
    documentationAvailable: true,
    featured: true,
    molecularFormula: "C14H24N6O4·Cu",
    molecularWeight: "≈ 403.9 g/mol",
    storageInformation:
      "Store lyophilized material at -20 °C, protected from light and moisture. Keep reconstituted solutions refrigerated.",
    handlingInformation:
      "Handle under appropriate laboratory controls using standard personal protective equipment. For laboratory research use only.",
    addedOn: "2026-04-20",
  },
  {
    slug: "cjc-1295",
    name: "CJC-1295",
    shortName: "CJC-1295",
    category: "Growth-Factor Research",
    description:
      "A synthetic peptide reference material supplied for growth-factor pathway research. Provided with batch-level identity and purity documentation.",
    presentation: "5 mg lyophilized · single vial",
    status: "in-stock",
    batchNumber: "ELB-CJC-0000 (sample)",
    documentationAvailable: true,
    featured: true,
    molecularFormula: "C165H269N47O46",
    molecularWeight: "≈ 3647.2 g/mol",
    storageInformation:
      "Store lyophilized material at -20 °C, protected from light and moisture. Refrigerate reconstituted material.",
    handlingInformation:
      "Handle under appropriate laboratory controls using standard personal protective equipment. For laboratory research use only.",
    addedOn: "2026-04-05",
  },
  {
    slug: "ipamorelin",
    name: "Ipamorelin",
    shortName: "Ipamorelin",
    category: "Growth-Factor Research",
    description:
      "A synthetic pentapeptide reference material for growth-factor pathway research. Supplied with identity assessment and purity documentation to support method development.",
    presentation: "5 mg lyophilized · single vial",
    status: "backorder",
    batchNumber: "ELB-IPA-0000 (sample)",
    documentationAvailable: false,
    featured: true,
    molecularFormula: "C38H49N9O5",
    molecularWeight: "≈ 711.9 g/mol",
    storageInformation:
      "Store lyophilized material at -20 °C, protected from light and moisture. Refrigerate reconstituted material.",
    handlingInformation:
      "Handle under appropriate laboratory controls using standard personal protective equipment. For laboratory research use only.",
    addedOn: "2026-03-22",
  },
];

/* -------------------------------------------------------------------------- */
/*  Helpers                                                                    */
/* -------------------------------------------------------------------------- */

export const STATUS_META: Record<
  ProductStatus,
  { label: string; tone: "positive" | "warning" | "neutral" }
> = {
  "in-stock": { label: "In Stock", tone: "positive" },
  limited: { label: "Limited", tone: "warning" },
  backorder: { label: "Backorder", tone: "neutral" },
};

export function getProduct(slug: string): Product | undefined {
  return products.find((p) => p.slug === slug);
}

export function getFeaturedProducts(): Product[] {
  return products.filter((p) => p.featured);
}

export function getRelatedProducts(slug: string, limit = 3): Product[] {
  const current = getProduct(slug);
  if (!current) return products.slice(0, limit);
  const sameCategory = products.filter(
    (p) => p.slug !== slug && p.category === current.category,
  );
  const others = products.filter(
    (p) => p.slug !== slug && p.category !== current.category,
  );
  return [...sameCategory, ...others].slice(0, limit);
}
