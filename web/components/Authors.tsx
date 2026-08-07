import { SectionDivider } from "./SectionDivider";
import { CONFIG } from "@/lib/config";
import { Card } from "@/components/ui/Card";

export function Authors() {
  return (
    <>
      <SectionDivider id="authors" eyebrow="Authors" title="Who built this" />
      <div className="mt-6 grid gap-8 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <p className="font-serif text-h3">Conor Plunkett</p>
          <p className="mt-1 font-mono text-small text-muted">
            Independent researcher
          </p>
          <p className="mt-4 max-w-xl text-prose leading-relaxed text-ink/85">
            Conor has worked directly on payment infrastructure and AI payment
            product workflows. That gives PayBench practical grounding in where
            real-world failures happen: consent UI, spend controls, delegated
            credentials, merchant coverage, checkout reliability, card rails, and
            auditability.
          </p>
        </div>
        <Card className="flex flex-col gap-3 self-start font-mono text-small">
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
        </Card>
      </div>
    </>
  );
}
