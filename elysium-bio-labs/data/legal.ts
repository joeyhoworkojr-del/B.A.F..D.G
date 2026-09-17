/* ==========================================================================
   Elysium Bio Labs — legal page copy (centralized, EDITABLE)
   --------------------------------------------------------------------------
   ⚠️  IMPORTANT — NOT LEGAL ADVICE
   The copy below is placeholder legal language provided as a starting point
   only. It is NOT legal advice and is NOT guaranteed to satisfy Canadian (or
   any other) legal or regulatory requirements. Have all legal pages reviewed
   by qualified Canadian regulatory counsel before launch, and replace the
   bracketed placeholders with your own reviewed terms.
   ========================================================================== */

export interface LegalSection {
  heading: string;
  paragraphs: string[];
}

export interface LegalPage {
  slug: string;
  title: string;
  summary: string;
  updated: string;
  sections: LegalSection[];
}

const RUO_STATEMENT =
  "All products and materials presented by Elysium Bio Labs are intended exclusively for laboratory, analytical, and research purposes. They are not intended for human or veterinary consumption, diagnosis, treatment, prevention, or therapeutic use.";

export const legalPages: LegalPage[] = [
  {
    slug: "research-use-only",
    title: "Research Use Only Policy",
    summary:
      "Materials supplied by Elysium Bio Labs are for laboratory and research use only.",
    updated: "2026-07-01",
    sections: [
      {
        heading: "Scope",
        paragraphs: [
          RUO_STATEMENT,
          "By purchasing or inquiring about our materials, you confirm that they will be used solely within a laboratory, analytical, or research setting by qualified personnel.",
        ],
      },
      {
        heading: "Prohibited uses",
        paragraphs: [
          "Materials must not be used in or on humans or animals, nor for any diagnostic, therapeutic, or clinical purpose. We do not provide dosing, administration, or clinical-use information of any kind.",
          "The purchaser is responsible for ensuring that intended uses comply with all applicable laws, institutional policies, and ethical requirements.",
        ],
      },
      {
        heading: "No guarantee of regulatory compliance",
        paragraphs: [
          "This policy describes our intended use restrictions. It does not, by itself, guarantee compliance with any regulatory framework. Purchasers remain responsible for their own compliance obligations. [Have this policy reviewed by qualified Canadian regulatory counsel before launch.]",
        ],
      },
    ],
  },
  {
    slug: "privacy-policy",
    title: "Privacy Policy",
    summary:
      "How Elysium Bio Labs collects, uses, and protects the information you provide.",
    updated: "2026-07-01",
    sections: [
      {
        heading: "Information we collect",
        paragraphs: [
          "When you submit an inquiry or documentation request, we collect the information you provide — such as your name, organization, email, optional phone number, and message — so that we can respond.",
          "We may also collect limited technical information (such as IP address) for security and anti-spam purposes.",
        ],
      },
      {
        heading: "How we use information",
        paragraphs: [
          "We use the information you provide to respond to your inquiry, process documentation requests, and maintain records of correspondence. We do not sell your personal information.",
          "[Describe any analytics, email-provider, or CRM processors you use, and update this section accordingly.]",
        ],
      },
      {
        heading: "Data retention and your rights",
        paragraphs: [
          "We retain inquiry records for as long as necessary to fulfil the purposes described here or as required by law. You may request access to, correction of, or deletion of your personal information by contacting us.",
          "[Confirm retention periods and applicable privacy-law rights — e.g. PIPEDA in Canada — with qualified counsel.]",
        ],
      },
    ],
  },
  {
    slug: "terms",
    title: "Terms and Conditions",
    summary:
      "The terms that govern your use of this website and any inquiry or order placed with Elysium Bio Labs.",
    updated: "2026-07-01",
    sections: [
      {
        heading: "Acceptance of terms",
        paragraphs: [
          "By accessing this website or submitting an inquiry, you agree to these terms. If you do not agree, please do not use the site.",
        ],
      },
      {
        heading: "Eligibility and permitted use",
        paragraphs: [
          RUO_STATEMENT,
          "You represent that you are acquiring materials for legitimate research purposes and that you are authorized to do so on behalf of your organization.",
        ],
      },
      {
        heading: "Documentation and sample data",
        paragraphs: [
          "Certain figures, batch numbers, and certificates shown on this site are clearly labelled demonstrations or sample data. They are provided to illustrate our documentation format and must not be relied upon as verified analytical results.",
        ],
      },
      {
        heading: "Limitation of liability",
        paragraphs: [
          "To the fullest extent permitted by law, Elysium Bio Labs is not liable for any indirect or consequential loss arising from use of this website or materials. [This clause must be reviewed and adapted by qualified Canadian counsel.]",
        ],
      },
    ],
  },
  {
    slug: "shipping-policy",
    title: "Shipping Policy",
    summary:
      "How orders are prepared, handled, and dispatched. Placeholder terms pending confirmation.",
    updated: "2026-07-01",
    sections: [
      {
        heading: "Handling and dispatch",
        paragraphs: [
          "Materials are prepared and dispatched under documented handling procedures. [Confirm processing times, carriers, and packaging standards.]",
        ],
      },
      {
        heading: "Shipping regions",
        paragraphs: [
          "[Specify the regions you ship to and any restrictions. Confirm import/export and controlled-substance requirements with qualified counsel before publishing.]",
        ],
      },
      {
        heading: "Cold-chain and receipt",
        paragraphs: [
          "Where materials require temperature control, they are packaged accordingly. Recipients are responsible for prompt receipt and correct storage on arrival, as described in each material's handling information.",
        ],
      },
    ],
  },
  {
    slug: "refund-policy",
    title: "Refund Policy",
    summary:
      "Placeholder refund and returns terms. Confirm before launch.",
    updated: "2026-07-01",
    sections: [
      {
        heading: "Returns",
        paragraphs: [
          "Because these are research materials with specific handling and storage requirements, returns may be limited. [Define your returns eligibility, timeframes, and conditions here.]",
        ],
      },
      {
        heading: "Refunds",
        paragraphs: [
          "[Describe how and when refunds are issued, and any restocking or handling deductions.] Refund terms must be confirmed with qualified counsel and aligned with applicable consumer-protection law.",
        ],
      },
      {
        heading: "Damaged or incorrect items",
        paragraphs: [
          "If an item arrives damaged or incorrect, contact us promptly with your batch reference so we can investigate and resolve the issue.",
        ],
      },
    ],
  },
  {
    slug: "documentation-policy",
    title: "Documentation Policy",
    summary:
      "How Elysium Bio Labs presents, labels, and provides batch documentation.",
    updated: "2026-07-01",
    sections: [
      {
        heading: "What documentation represents",
        paragraphs: [
          "Batch documentation is intended to describe a specific batch of material, including identity and purity information tied to named analytical methods. Documentation is meaningful only in relation to the batch it references.",
        ],
      },
      {
        heading: "Demonstration and sample data",
        paragraphs: [
          "Where this website shows certificates, purity figures, or batch numbers that are not yet backed by verified records, they are clearly labelled as demonstrations or sample data. We do not present demonstration data as real analytical results.",
        ],
      },
      {
        heading: "Requesting documentation",
        paragraphs: [
          "You may request documentation for a specific material through our contact form. Provide the product name and batch reference so we can respond with the correct records.",
        ],
      },
    ],
  },
];

export function getLegalPage(slug: string): LegalPage | undefined {
  return legalPages.find((p) => p.slug === slug);
}
