import { CONFIG } from "@/lib/config";

export function Nav() {
  return (
    <nav className="sticky top-0 z-40 border-b border-border bg-paper/85 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-center gap-7 px-5 py-3.5 sm:gap-10 sm:px-8">
        <a href="#summary" className="font-serif text-lg transition-colors hover:text-accent">
          Summary
        </a>
        <a href="#findings" className="font-serif text-lg transition-colors hover:text-accent">
          Findings
        </a>
        <a href="#method" className="font-serif text-lg transition-colors hover:text-accent">
          Method
        </a>
        <a
          href={CONFIG.repoUrl}
          target="_blank"
          rel="noreferrer"
          className="rounded-md border border-ink px-4 py-1.5 font-serif text-lg transition-colors hover:bg-ink hover:text-paper"
        >
          About
        </a>
      </div>
    </nav>
  );
}
