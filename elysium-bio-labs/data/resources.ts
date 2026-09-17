/* ==========================================================================
   Elysium Bio Labs — resources / articles (centralized data source)
   --------------------------------------------------------------------------
   Sample educational articles written with cautious, professional language.
   No administration, dosing, or clinical-outcome guidance.

   FUTURE CMS: replace the `resources` array with a CMS fetch; keep the
   helper signatures stable so the resource pages do not need to change.
   ========================================================================== */

export type ResourceCategory =
  | "Analytical Testing"
  | "Quality Documentation"
  | "Research Handling"
  | "Industry Standards"
  | "Company Updates";

export interface ResourceSection {
  heading: string;
  paragraphs: string[];
}

export interface Resource {
  slug: string;
  title: string;
  category: ResourceCategory;
  excerpt: string;
  author: string;
  publishedOn: string;
  featured: boolean;
  sections: ResourceSection[];
}

export const RESOURCE_CATEGORIES: ResourceCategory[] = [
  "Analytical Testing",
  "Quality Documentation",
  "Research Handling",
  "Industry Standards",
  "Company Updates",
];

export const resources: Resource[] = [
  {
    slug: "understanding-analytical-purity-reports",
    title: "Understanding Analytical Purity Reports",
    category: "Analytical Testing",
    excerpt:
      "A plain-language look at what a purity report describes, what its figures represent, and how to read one critically as a research buyer.",
    author: "Elysium Bio Labs",
    publishedOn: "2026-06-10",
    featured: true,
    sections: [
      {
        heading: "What a purity report is",
        paragraphs: [
          "An analytical purity report is a document that summarizes how a laboratory evaluated a material and what the results of that evaluation were. It typically identifies the material, describes the analytical methods used, and reports a purity figure alongside the conditions under which it was measured.",
          "Read as a research buyer, the value of a purity report is not the single headline percentage — it is the context around it: which method produced the number, what the acceptance criteria were, and whether the report is tied to a specific batch.",
        ],
      },
      {
        heading: "Method matters more than the number",
        paragraphs: [
          "Different analytical methods answer different questions. A chromatographic method such as HPLC separates components and can report the relative proportion of a target compound. A mass-based method contributes evidence about identity and molecular weight. A purity figure is only meaningful alongside the method that produced it.",
          "When you see a purity figure without a named method, treat it as marketing rather than data. A credible report always states how the measurement was made.",
        ],
      },
      {
        heading: "Tie every figure to a batch",
        paragraphs: [
          "Purity is a property of a specific batch, not of a product name in the abstract. A report that cannot be traced to a batch identifier tells you very little about the material actually in front of you.",
          "This is why batch traceability and documentation belong together. The report answers 'how pure', and the batch record answers 'pure — of what, and when'.",
        ],
      },
    ],
  },
  {
    slug: "identity-testing-vs-purity-testing",
    title: "Identity Testing vs. Purity Testing",
    category: "Analytical Testing",
    excerpt:
      "Identity and purity are often mentioned in the same breath, but they answer different questions. Understanding the distinction sharpens how you evaluate documentation.",
    author: "Elysium Bio Labs",
    publishedOn: "2026-05-28",
    featured: false,
    sections: [
      {
        heading: "Two different questions",
        paragraphs: [
          "Identity testing asks: is this material what it is labelled to be? Purity testing asks: of the material present, how much is the target compound versus everything else? A material can pass one and not the other.",
          "Confusing the two leads to over-confidence. A strong identity assessment does not, on its own, tell you how pure a material is, and a high purity figure does not confirm identity if the wrong reference was used.",
        ],
      },
      {
        heading: "How they complement each other",
        paragraphs: [
          "Good documentation pairs the two. Identity assessment establishes what the material is; purity analysis quantifies how much of it is the target compound. Together they give a fuller picture than either alone.",
          "When reviewing documentation, look for both — and for a clear statement of the methods behind each.",
        ],
      },
    ],
  },
  {
    slug: "how-batch-traceability-supports-research",
    title: "How Batch Traceability Supports Research",
    category: "Quality Documentation",
    excerpt:
      "Traceability is less glamorous than a purity percentage, but it is what makes a purity percentage trustworthy. Here is why batch-level records matter.",
    author: "Elysium Bio Labs",
    publishedOn: "2026-05-12",
    featured: false,
    sections: [
      {
        heading: "Reproducibility starts with records",
        paragraphs: [
          "Research depends on being able to repeat work and compare results. If you cannot tie a result to a specific batch of material, you cannot meaningfully compare it to a later result using a different batch.",
          "Batch traceability is the connective tissue that makes documentation useful over time. It links a material to the records that describe it, so a figure on a report can be traced back to a physical batch.",
        ],
      },
      {
        heading: "What a traceable batch looks like",
        paragraphs: [
          "A traceable batch has a unique identifier, a documented evaluation history, and records that stay attached to it through handling and storage. When any of those links is missing, the chain of evidence weakens.",
          "For a research buyer, the practical test is simple: can every figure you are shown be tied back to a batch identifier you can reference later? If yes, the documentation is doing its job.",
        ],
      },
    ],
  },
];

/* -------------------------------------------------------------------------- */
/*  Helpers                                                                    */
/* -------------------------------------------------------------------------- */

export function getResource(slug: string): Resource | undefined {
  return resources.find((r) => r.slug === slug);
}

export function getFeaturedResource(): Resource {
  return resources.find((r) => r.featured) ?? resources[0];
}

export function getRelatedResources(slug: string, limit = 2): Resource[] {
  const current = getResource(slug);
  if (!current) return resources.slice(0, limit);
  const sameCategory = resources.filter(
    (r) => r.slug !== slug && r.category === current.category,
  );
  const others = resources.filter(
    (r) => r.slug !== slug && r.category !== current.category,
  );
  return [...sameCategory, ...others].slice(0, limit);
}

/** Full plain text of an article, used for reading-time estimation. */
export function resourceText(resource: Resource): string {
  return resource.sections
    .flatMap((s) => [s.heading, ...s.paragraphs])
    .join(" ");
}
