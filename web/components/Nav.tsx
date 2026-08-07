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
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3 sm:px-8">
        <Link
          href="/#summary"
          aria-label="PayBench, back to summary"
          className="tap-link whitespace-nowrap text-h4 tracking-tight transition-opacity hover:opacity-70"
        >
          <span aria-hidden className="mr-1.5">
            💳
          </span>
          Pay
          <span className="text-accent">Bench</span>
        </Link>

        <div className="hidden items-center gap-5 lg:flex">
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`/#${s.id}`}
              className={`tap-link whitespace-nowrap text-small transition-colors hover:text-accent ${
                active === s.id ? "text-accent" : ""
              }`}
            >
              {s.short ?? s.label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/run"
            className="tap-link hidden whitespace-nowrap text-small transition-colors hover:text-accent sm:inline-flex"
          >
            Run it yourself
          </Link>
          <Link
            href="/scenarios"
            className="tap-link hidden whitespace-nowrap text-small transition-colors hover:text-accent sm:inline-flex"
          >
            Dataset
          </Link>
          <a
            href={CONFIG.repoUrl}
            target="_blank"
            rel="noreferrer"
            className="tap-link whitespace-nowrap rounded-lg border border-ink px-3.5 py-1.5 text-small transition-colors hover:bg-ink hover:text-paper"
          >
            GitHub
          </a>
        </div>
      </div>
    </nav>
  );
}
