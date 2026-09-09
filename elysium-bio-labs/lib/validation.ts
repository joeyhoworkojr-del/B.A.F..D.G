import { z } from "zod";

/* ==========================================================================
   Elysium Bio Labs — form validation schemas (shared client + server)
   ========================================================================== */

export const INQUIRY_TYPES = [
  "General Inquiry",
  "Wholesale / Institutional",
  "Documentation Request",
  "Order Support",
  "Product Information",
] as const;

export type InquiryType = (typeof INQUIRY_TYPES)[number];

export const contactSchema = z.object({
  firstName: z
    .string()
    .trim()
    .min(1, "First name is required")
    .max(80, "First name is too long"),
  lastName: z
    .string()
    .trim()
    .min(1, "Last name is required")
    .max(80, "Last name is too long"),
  organization: z
    .string()
    .trim()
    .min(1, "Organization is required")
    .max(160, "Organization name is too long"),
  email: z
    .string()
    .trim()
    .min(1, "Email is required")
    .email("Enter a valid email address")
    .max(160),
  phone: z
    .string()
    .trim()
    .max(40, "Phone number is too long")
    .optional()
    .or(z.literal("")),
  inquiryType: z.enum(INQUIRY_TYPES, {
    message: "Select an inquiry type",
  }),
  productOrBatch: z
    .string()
    .trim()
    .max(120, "This field is too long")
    .optional()
    .or(z.literal("")),
  message: z
    .string()
    .trim()
    .min(10, "Please provide at least a short message")
    .max(4000, "Message is too long"),
  consent: z.boolean().refine((v) => v === true, {
    message: "Please confirm you agree before submitting",
  }),
  /**
   * Honeypot — must stay empty. Bots tend to fill every field. We accept any
   * string here (so validation doesn't reveal the trap) and detect a non-empty
   * value in the API route, responding with a silent success.
   */
  company_website: z.string().optional(),
});

export type ContactFormValues = z.infer<typeof contactSchema>;

/** Default values for the contact form; `inquiryType` may be preset per page. */
export function contactDefaults(
  inquiryType: InquiryType = "General Inquiry",
): ContactFormValues {
  return {
    firstName: "",
    lastName: "",
    organization: "",
    email: "",
    phone: "",
    inquiryType,
    productOrBatch: "",
    message: "",
    consent: false,
    company_website: "",
  };
}
