import { SectionDivider } from "./SectionDivider";
import { CONFIG } from "@/lib/config";

export function Authors() {
  return (
    <>
      <SectionDivider id="authors" eyebrow="Authors" title="Who built this" />
      <div className="mt-6 grid gap-8 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <p className="font-serif text-2xl">Conor Plunkett</p>
          <p className="mt-1 font-mono text-sm text-muted">
            Independent researcher
          </p>
          <p className="mt-4 max-w-xl text-lg leading-relaxed text-ink/85">
            Conor has worked directly on payment infrastructure and AI payment
            product workflows. That gives PayBench practical grounding in where
            real-world failures happen: consent UI, spend controls, delegated
            credentials, merchant coverage, checkout reliability, card rails, and
            auditability.
          </p>
        </div>
        <div className="flex flex-col gap-3 self-start rounded-xl border border-border bg-paper-2/40 p-5 font-mono text-sm">
          <a
            href={`mailto:${CONFIG.contactEmail}`}
            className="hover:text-accent"
          >
            {CONFIG.contactEmail}
          </a>
          <a
            href={CONFIG.repoUrl}
            target="_blank"
            rel="noreferrer"
            className="hover:text-accent"
          >
            github.com/conorplunkett
          </a>
        </div>
      </div>
    </>
  );
}
