"use client";

import * as React from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import {
  contactSchema,
  contactDefaults,
  INQUIRY_TYPES,
  type ContactFormValues,
  type InquiryType,
} from "@/lib/validation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { company } from "@/data/company";

const CONTACT_EMAIL = company.email;

type SubmitState = "idle" | "submitting" | "success" | "error";

export function ContactForm({
  defaultInquiryType = "General Inquiry",
  defaultProductOrBatch = "",
  compact = false,
}: {
  defaultInquiryType?: InquiryType;
  defaultProductOrBatch?: string;
  compact?: boolean;
}) {
  const [state, setState] = React.useState<SubmitState>("idle");
  const [serverError, setServerError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ContactFormValues>({
    resolver: zodResolver(contactSchema),
    defaultValues: {
      ...contactDefaults(defaultInquiryType),
      productOrBatch: defaultProductOrBatch,
    },
  });

  // In static-export builds (GitHub Pages) there is no server API route, so we
  // fall back to opening the user's email client with a pre-filled message.
  const isStatic = process.env.NEXT_PUBLIC_STATIC_EXPORT === "1";

  const onSubmit = async (values: ContactFormValues) => {
    setState("submitting");
    setServerError(null);

    if (isStatic) {
      const subject = `Inquiry: ${values.inquiryType}`;
      const body = [
        `Name: ${values.firstName} ${values.lastName}`,
        `Organization: ${values.organization}`,
        `Email: ${values.email}`,
        values.phone ? `Phone: ${values.phone}` : null,
        values.productOrBatch
          ? `Product / batch: ${values.productOrBatch}`
          : null,
        "",
        values.message,
      ]
        .filter(Boolean)
        .join("\n");
      window.location.href = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(
        subject,
      )}&body=${encodeURIComponent(body)}`;
      setState("success");
      return;
    }

    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.message ?? "Submission failed");
      }
      setState("success");
      reset({
        ...contactDefaults(defaultInquiryType),
        productOrBatch: defaultProductOrBatch,
      });
    } catch (err) {
      setState("error");
      setServerError(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again.",
      );
    }
  };

  if (state === "success") {
    return (
      <div className="flex flex-col items-center rounded-[var(--radius-lg)] border border-emerald-200 bg-emerald-50/60 px-6 py-12 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100">
          <CheckCircle2 className="h-6 w-6 text-emerald-600" aria-hidden />
        </div>
        <h3 className="mt-4 text-lg font-semibold text-navy">
          Inquiry received
        </h3>
        <p className="mt-1.5 max-w-sm text-sm text-ink/60">
          Thank you. Your inquiry has been recorded and our team will respond to
          the email you provided.
        </p>
        <Button
          variant="secondary"
          size="sm"
          className="mt-6"
          onClick={() => setState("idle")}
        >
          Submit another inquiry
        </Button>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      className="space-y-5"
      aria-describedby={serverError ? "form-error" : undefined}
    >
      {/* Honeypot — visually hidden, off-screen; real users never fill it. */}
      <div aria-hidden className="absolute left-[-9999px] h-0 w-0 overflow-hidden">
        <label htmlFor="company_website">Company website</label>
        <input
          id="company_website"
          type="text"
          tabIndex={-1}
          autoComplete="off"
          {...register("company_website")}
        />
      </div>

      <div className={cn("grid gap-5", !compact && "sm:grid-cols-2")}>
        <Field label="First name" error={errors.firstName?.message} required>
          <input
            type="text"
            autoComplete="given-name"
            {...register("firstName")}
            className={inputCls(!!errors.firstName)}
          />
        </Field>
        <Field label="Last name" error={errors.lastName?.message} required>
          <input
            type="text"
            autoComplete="family-name"
            {...register("lastName")}
            className={inputCls(!!errors.lastName)}
          />
        </Field>
      </div>

      <Field
        label="Organization"
        error={errors.organization?.message}
        required
      >
        <input
          type="text"
          autoComplete="organization"
          {...register("organization")}
          className={inputCls(!!errors.organization)}
        />
      </Field>

      <div className={cn("grid gap-5", !compact && "sm:grid-cols-2")}>
        <Field label="Email" error={errors.email?.message} required>
          <input
            type="email"
            autoComplete="email"
            {...register("email")}
            className={inputCls(!!errors.email)}
          />
        </Field>
        <Field label="Phone" error={errors.phone?.message} hint="Optional">
          <input
            type="tel"
            autoComplete="tel"
            {...register("phone")}
            className={inputCls(!!errors.phone)}
          />
        </Field>
      </div>

      <div className={cn("grid gap-5", !compact && "sm:grid-cols-2")}>
        <Field label="Inquiry type" error={errors.inquiryType?.message} required>
          <select
            {...register("inquiryType")}
            className={cn(inputCls(!!errors.inquiryType), "appearance-none")}
          >
            {INQUIRY_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label="Product or batch number"
          error={errors.productOrBatch?.message}
          hint="Optional"
        >
          <input
            type="text"
            {...register("productOrBatch")}
            className={inputCls(!!errors.productOrBatch)}
          />
        </Field>
      </div>

      <Field label="Message" error={errors.message?.message} required>
        <textarea
          rows={compact ? 4 : 5}
          {...register("message")}
          className={cn(inputCls(!!errors.message), "h-auto min-h-[7rem] resize-y py-2.5")}
        />
      </Field>

      <div>
        <label className="flex cursor-pointer items-start gap-3 text-sm text-ink/70">
          <input
            type="checkbox"
            {...register("consent")}
            className="mt-0.5 h-4 w-4 accent-[color:var(--color-elysium)]"
          />
          <span>
            I confirm this inquiry relates to laboratory, analytical, or research
            purposes, and I agree to the{" "}
            <Link
              href="/legal/privacy-policy"
              className="text-elysium hover:underline"
            >
              Privacy Policy
            </Link>
            .
          </span>
        </label>
        {errors.consent && (
          <p className="mt-1.5 text-xs text-red-600">{errors.consent.message}</p>
        )}
      </div>

      {serverError && (
        <div
          id="form-error"
          role="alert"
          className="flex items-center gap-2 rounded-[var(--radius-sm)] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          <AlertCircle className="h-4 w-4 flex-shrink-0" aria-hidden />
          {serverError}
        </div>
      )}

      <Button
        type="submit"
        size="lg"
        disabled={state === "submitting"}
        className="w-full sm:w-auto"
      >
        {state === "submitting" ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Submitting…
          </>
        ) : (
          "Submit Inquiry"
        )}
      </Button>
    </form>
  );
}

function Field({
  label,
  error,
  hint,
  required,
  children,
}: {
  label: string;
  error?: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  const id = React.useId();
  // Attach id/aria to the single child input via cloneElement.
  const child = React.isValidElement(children)
    ? React.cloneElement(children as React.ReactElement<Record<string, unknown>>, {
        id,
        "aria-invalid": !!error,
        "aria-describedby": error ? `${id}-error` : undefined,
      })
    : children;

  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1.5 flex items-center gap-2 text-sm font-medium text-navy"
      >
        {label}
        {required && <span className="text-elysium">*</span>}
        {hint && <span className="text-xs font-normal text-ink/40">{hint}</span>}
      </label>
      {child}
      {error && (
        <p id={`${id}-error`} className="mt-1.5 text-xs text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}

function inputCls(hasError: boolean): string {
  return cn(
    "h-11 w-full rounded-[var(--radius-sm)] border bg-white px-3.5 text-sm text-navy outline-none transition-colors placeholder:text-ink/40",
    hasError
      ? "border-red-300 focus:border-red-500"
      : "border-[color:var(--color-border-grey)] focus:border-elysium",
  );
}
