import { CONFIG } from "@/lib/config";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-border bg-paper-2/60">
      <div className="mx-auto flex max-w-5xl flex-col gap-4 px-5 py-10 sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <div>
          <p className="font-serif text-lg">Unsafe Commercial Autonomy</p>
          <p className="mt-1 max-w-md text-sm text-muted">
            An open benchmark for delegated-payment safety. Results are published
            from the evaluation harness; run it yourself by cloning the repo.
          </p>
        </div>
        <div className="flex items-center gap-5 font-mono text-sm">
          <a href={CONFIG.repoUrl} target="_blank" rel="noreferrer" className="hover:text-accent">
            GitHub
          </a>
          <a href="#summary" className="hover:text-accent">
            Top
          </a>
        </div>
      </div>
    </footer>
  );
}
