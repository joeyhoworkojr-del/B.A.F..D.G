/* ==========================================================================
   Elysium Bio Labs — company facts (centralized data source)
   --------------------------------------------------------------------------
   EDITABLE PLACEHOLDERS. Replace bracketed [TO BE CONFIRMED] values with
   verified company information before launch. Do NOT fabricate history,
   staff, ownership, certifications, partnerships, or regulatory approvals.
   ========================================================================== */

export const company = {
  name: "Elysium Bio Labs",
  tagline: "Precision Materials for Advanced Research.",
  shortDescription:
    "A premium research-focused biosciences supplier providing high-purity laboratory materials for qualified research applications, supported by transparent documentation and rigorous quality standards.",

  // --- Contact placeholders — confirm before launch ---
  email: "inquiries@elysiumbiolabs.example",
  supportEmail: "support@elysiumbiolabs.example",
  phone: "[TO BE CONFIRMED]",
  region: "Canada",
  addressLine: "[Registered address — TO BE CONFIRMED]",

  // --- Mission & philosophy ---
  mission:
    "To elevate the standard of research-material sourcing through disciplined documentation, considered presentation, and a commitment to transparency.",
  documentationPhilosophy:
    "Documentation should never be an afterthought. Every material we present is organized around clear, batch-level records so researchers can evaluate what they are working with — not take it on faith.",
  qualityPhilosophy:
    "Quality is a process, not a claim. We favour careful sourcing, independent evaluation, and honest labelling over marketing language, and we clearly distinguish demonstration data from verified results.",

  principles: [
    {
      title: "Precision over persuasion",
      body: "We describe materials with restraint and accuracy. No miracle language, no unsupported claims.",
    },
    {
      title: "Documentation by default",
      body: "Batch-level records are the foundation of our catalogue, not a premium add-on.",
    },
    {
      title: "Traceability end to end",
      body: "Every material is designed to be traceable from source evaluation to controlled handling.",
    },
    {
      title: "Transparent by design",
      body: "We clearly mark demonstration data and never present sample values as verified results.",
    },
  ],

  // --- Social placeholders ---
  social: {
    linkedin: "#",
    x: "#",
    researchGate: "#",
  },
} as const;

/**
 * Factual business details still required from the owner before launch.
 * Surfaced in the README and used to gate any claim that would otherwise
 * be fabricated.
 */
export const OWNER_TODO: string[] = [
  "Registered legal entity name and business number",
  "Registered address and jurisdiction of incorporation",
  "Verified contact email and phone number",
  "Real batch records and analytical results to replace sample data",
  "Names of any independent laboratories used (only if a relationship exists)",
  "Any certifications or accreditations actually held (only if genuine)",
  "Shipping regions, carriers, and handling terms",
  "Confirmation of Research-Use-Only sales policy and eligibility checks",
];
