"use client";

import * as React from "react";

/**
 * Soft luminous gradient that follows the cursor on desktop (fine pointer,
 * motion allowed). Purely decorative; disabled for touch and reduced motion.
 */
export function CursorGlow() {
  const ref = React.useRef<HTMLDivElement>(null);
  const [enabled, setEnabled] = React.useState(false);

  React.useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)").matches;
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (!fine || reduced) return;
    setEnabled(true);

    let raf = 0;
    const onMove = (e: MouseEvent) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        if (ref.current) {
          ref.current.style.setProperty("--gx", `${e.clientX}px`);
          ref.current.style.setProperty("--gy", `${e.clientY}px`);
        }
      });
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => {
      window.removeEventListener("mousemove", onMove);
      cancelAnimationFrame(raf);
    };
  }, []);

  if (!enabled) return null;

  return (
    <div
      ref={ref}
      aria-hidden
      className="pointer-events-none fixed inset-0 z-0 transition-opacity duration-500"
      style={{
        background:
          "radial-gradient(340px circle at var(--gx, 50%) var(--gy, 0px), rgba(7,87,247,0.06), transparent 70%)",
      }}
    />
  );
}
