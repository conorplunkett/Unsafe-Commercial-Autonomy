import { CONFIG, HAS_PAPER } from "@/lib/config";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-border bg-paper-2/60">
      <div className="mx-auto flex max-w-5xl flex-col gap-4 px-5 py-10 sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <div>
          <p className="font-serif text-lg">
            💳 Pay<span className="text-accent">Bench</span>
          </p>
          <p className="mt-1 max-w-md text-sm text-muted">
            An open benchmark for delegated-payment safety. Results are published
            live from the evaluation harness; run it yourself by cloning the
            repo.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-5 font-mono text-sm">
          {HAS_PAPER && (
            <a
              href={CONFIG.paperUrl}
              target="_blank"
              rel="noreferrer"
              className="hover:text-accent"
            >
              Paper
            </a>
          )}
          <a
            href={CONFIG.repoUrl}
            target="_blank"
            rel="noreferrer"
            className="hover:text-accent"
          >
            GitHub
          </a>
          <a href={`mailto:${CONFIG.contactEmail}`} className="hover:text-accent">
            Contact
          </a>
          <a href="#cite" className="hover:text-accent">
            Cite
          </a>
          <a href="#summary" className="hover:text-accent">
            Top
          </a>
        </div>
      </div>
    </footer>
  );
}
