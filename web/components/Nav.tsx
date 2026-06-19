"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CONFIG } from "@/lib/config";
import { SECTIONS } from "@/lib/sections";

// Highlights the section currently near the middle of the viewport (ai-2027
// style). Degrades gracefully: if IntersectionObserver isn't available or the
// section elements aren't on the page (e.g. /scenarios), nothing is active and
// the links still scroll.
function useActiveSection(): string | null {
  const [active, setActive] = useState<string | null>(null);
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) setActive(e.target.id);
        }
      },
      { rootMargin: "-45% 0px -50% 0px", threshold: 0 },
    );
    const els = SECTIONS.map((s) => document.getElementById(s.id)).filter(
      (el): el is HTMLElement => el != null,
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);
  return active;
}

export function Nav() {
  const active = useActiveSection();
  return (
    <nav className="sticky top-0 z-40 border-b border-border bg-paper/85 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-3 sm:px-8">
        <Link href="/" className="font-serif text-xl tracking-tight">
          <span aria-hidden className="mr-1.5">💳</span>Pay
          <span className="text-accent">Bench</span>
        </Link>

        <div className="hidden items-center gap-6 md:flex">
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`/#${s.id}`}
              className={`font-serif text-[1.05rem] transition-colors hover:text-accent ${
                active === s.id ? "text-accent" : ""
              }`}
            >
              {s.label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/scenarios"
            className="hidden font-serif text-[1.05rem] transition-colors hover:text-accent sm:inline"
          >
            Dataset
          </Link>
          <a
            href={CONFIG.repoUrl}
            target="_blank"
            rel="noreferrer"
            className="rounded-md border border-ink px-3.5 py-1.5 font-serif text-[1.05rem] transition-colors hover:bg-ink hover:text-paper"
          >
            GitHub
          </a>
        </div>
      </div>
    </nav>
  );
}
