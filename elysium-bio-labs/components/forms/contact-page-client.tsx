"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { ContactForm } from "./contact-form";
import type { InquiryType } from "@/lib/validation";

const TYPE_MAP: Record<string, InquiryType> = {
  general: "General Inquiry",
  wholesale: "Wholesale / Institutional",
  documentation: "Documentation Request",
  order: "Order Support",
  product: "Product Information",
};

/** Reads ?type= and ?batch= to preset the form, then renders it. */
export function ContactPageClient() {
  const params = useSearchParams();
  const typeParam = params.get("type");
  const batchParam = params.get("batch") ?? params.get("product") ?? "";
  const inquiryType: InquiryType =
    (typeParam && TYPE_MAP[typeParam]) || "General Inquiry";

  return (
    <ContactForm
      defaultInquiryType={inquiryType}
      defaultProductOrBatch={batchParam}
    />
  );
}
