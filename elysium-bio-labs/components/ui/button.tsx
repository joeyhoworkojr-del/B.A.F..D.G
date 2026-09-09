import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "dark";
type Size = "sm" | "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-2 font-medium rounded-[var(--radius-sm)] " +
  "transition-all duration-200 ease-[var(--ease-out-soft)] focus-visible:outline-none " +
  "focus-visible:ring-2 focus-visible:ring-elysium focus-visible:ring-offset-2 " +
  "disabled:opacity-50 disabled:pointer-events-none select-none whitespace-nowrap";

const variants: Record<Variant, string> = {
  primary:
    "bg-elysium text-white shadow-[0_6px_20px_-8px_rgba(7,87,247,0.7)] hover:bg-elysium-600 hover:shadow-[0_10px_28px_-10px_rgba(7,87,247,0.8)] active:translate-y-px",
  secondary:
    "bg-white text-navy border border-[color:var(--color-border-grey)] hover:border-elysium hover:text-elysium",
  ghost: "bg-transparent text-navy hover:bg-cool",
  dark: "bg-white/10 text-white border border-white/20 hover:bg-white/15 backdrop-blur-sm",
};

const sizes: Record<Size, string> = {
  sm: "h-9 px-4 text-sm",
  md: "h-11 px-6 text-sm",
  lg: "h-12 px-7 text-[0.95rem]",
};

interface CommonProps {
  variant?: Variant;
  size?: Size;
  className?: string;
  children: React.ReactNode;
}

type ButtonAsButton = CommonProps &
  React.ButtonHTMLAttributes<HTMLButtonElement> & { href?: undefined };

type ButtonAsLink = CommonProps &
  Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & {
    href: string;
  };

export function Button(props: ButtonAsButton | ButtonAsLink) {
  const {
    variant = "primary",
    size = "md",
    className,
    children,
    ...rest
  } = props;
  const classes = cn(base, variants[variant], sizes[size], className);

  if ("href" in props && props.href !== undefined) {
    const { href, ...anchorRest } =
      rest as React.AnchorHTMLAttributes<HTMLAnchorElement>;
    const isExternal = href!.startsWith("http") || href!.startsWith("#");
    if (isExternal) {
      return (
        <a href={href} className={classes} {...anchorRest}>
          {children}
        </a>
      );
    }
    return (
      <Link href={href!} className={classes} {...anchorRest}>
        {children}
      </Link>
    );
  }

  return (
    <button
      className={classes}
      {...(rest as React.ButtonHTMLAttributes<HTMLButtonElement>)}
    >
      {children}
    </button>
  );
}
