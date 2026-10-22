"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { RuoBadge } from "@/components/ui/badge";
import { asset } from "@/lib/asset";
import { NAV_LINKS } from "./nav-links";

export function Header() {
  const [scrolled, setScrolled] = React.useState(false);
  const [open, setOpen] = React.useState(false);
  const pathname = usePathname();

  React.useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Close mobile menu on route change and lock scroll while open.
  React.useEffect(() => setOpen(false), [pathname]);
  React.useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-all duration-300 ease-[var(--ease-out-soft)]",
        scrolled
          ? "border-b border-[color:var(--color-border-grey)] glass shadow-[0_1px_20px_-12px_rgba(8,21,47,0.3)]"
          : "border-b border-transparent bg-transparent",
      )}
    >
      <div className="container-el flex h-[var(--header-height)] items-center justify-between gap-4">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2.5 rounded-sm"
          aria-label="Elysium Bio Labs — home"
        >
          <Image
            src={asset("/elysium-logo.png")}
            alt=""
            width={140}
            height={140}
            priority
            className="h-9 w-auto"
          />
          <span className="sr-only">Elysium Bio Labs</span>
        </Link>

        {/* Desktop nav */}
        <nav
          className="hidden items-center gap-1 lg:flex"
          aria-label="Primary"
        >
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "relative rounded-[var(--radius-xs)] px-3 py-2 text-sm font-medium transition-colors",
                isActive(link.href)
                  ? "text-elysium"
                  : "text-navy/75 hover:text-navy",
              )}
            >
              {link.label}
              {isActive(link.href) && (
                <motion.span
                  layoutId="nav-underline"
                  className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-elysium"
                />
              )}
            </Link>
          ))}
        </nav>

        {/* Right cluster */}
        <div className="flex items-center gap-3">
          <RuoBadge className="hidden xl:inline-flex" />
          <Button
            href="/research-materials"
            size="sm"
            className="hidden sm:inline-flex"
          >
            View Research Materials
          </Button>

          {/* Mobile toggle */}
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-sm)] border border-[color:var(--color-border-grey)] bg-white/60 text-navy lg:hidden"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            aria-controls="mobile-menu"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {open && (
          <motion.div
            id="mobile-menu"
            className="lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <motion.nav
              className="container-el flex flex-col gap-1 border-t border-[color:var(--color-border-grey)] glass pb-6 pt-3"
              aria-label="Mobile"
              initial={{ y: -8 }}
              animate={{ y: 0 }}
              exit={{ y: -8 }}
              transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            >
              {NAV_LINKS.map((link, i) => (
                <motion.div
                  key={link.href}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.04 * i, duration: 0.25 }}
                >
                  <Link
                    href={link.href}
                    className={cn(
                      "flex items-center justify-between rounded-[var(--radius-sm)] px-3 py-3 text-base font-medium",
                      isActive(link.href)
                        ? "bg-soft text-elysium"
                        : "text-navy hover:bg-cool",
                    )}
                  >
                    {link.label}
                    <ArrowUpRight className="h-4 w-4 opacity-40" aria-hidden />
                  </Link>
                </motion.div>
              ))}
              <div className="mt-3 flex flex-col gap-2.5">
                <Button href="/research-materials" className="w-full">
                  View Research Materials
                </Button>
                <Button
                  href="/contact?type=documentation"
                  variant="secondary"
                  className="w-full"
                >
                  Request Documentation
                </Button>
                <div className="pt-2">
                  <RuoBadge />
                </div>
              </div>
            </motion.nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
