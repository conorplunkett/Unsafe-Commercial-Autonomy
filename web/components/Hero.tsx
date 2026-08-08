import { CONFIG } from "@/lib/config";

// Each entry is a paragraph; a nested array breaks onto its own line inside it.
const LEDE: (string | string[])[] = [
  [
    "AI shopping has been “coming soon” for years.",
    "Nobody trusts AI to spend their money yet.",
  ],
  "We do not have a measurable frontier for “safe agentic payments” yet.",
  [
    "PayBench provides that benchmark. It runs models through a gauntlet of payment scenarios. Half are traps: a subscription that jumps from $2 to $200 in 30 days, a vendor from the not-allowed list, a prompt injection on the product page.",
    "Each trap has a harmless lookalike the agent should simply buy safely.",
  ],
  "Together, they map the agentic payment frontier: agents that spend on their own when it's safe, and stop to ask when it isn't.",
];

// Clickable thumbnail of the bundled paper PDF. The embedded preview renders the
// first page; clicking opens the full PDF in a new tab.
function PaperPreview() {
  return (
    <figure className="lg:sticky lg:top-24">
      <a
        href={CONFIG.paperPdf}
        target="_blank"
        rel="noreferrer"
        aria-label="Open the PayBench paper (PDF)"
        className="group block overflow-hidden rounded-lg border border-border bg-paper shadow-[0_4px_12px_rgba(0,0,0,0.05)] transition-shadow hover:shadow-[0_8px_20px_rgba(0,0,0,0.08)]"
      >
        <object
          data={`${CONFIG.paperPdf}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`}
          type="application/pdf"
          aria-hidden="true"
          tabIndex={-1}
          className="pointer-events-none aspect-[3/4] w-full"
        >
          <div className="flex aspect-[3/4] w-full items-center justify-center bg-ink/5 p-6 text-center font-mono text-caption text-muted">
            PDF preview unavailable. Click to open the paper.
          </div>
        </object>
      </a>
    </figure>
  );
}

export function Hero() {
  return (
    <header id="summary" className="scroll-mt-20 pt-14 sm:pt-20">
      <div className="grid items-start gap-10 lg:grid-cols-[minmax(0,1fr)_28rem] lg:gap-14">
        <div>
          <h1 className="text-display tracking-tight">
            Pay<span className="text-accent">Bench</span>
          </h1>
          <p className="mt-4 max-w-3xl font-serif text-h3 italic leading-snug text-ink/80">
            A benchmark for agents using human money safely.
          </p>
          <p className="mt-4 font-mono text-small text-muted">
            <a
              href="mailto:hello@conorplunkett.com"
              className="text-inherit no-underline"
            >
              Conor Plunkett
            </a>{" "}
            · Independent researcher
          </p>

          <div className="mt-6 max-w-2xl space-y-4 font-serif text-prose leading-relaxed text-ink/85">
            {LEDE.map((para, i) => (
              <p key={i}>
                {(Array.isArray(para) ? para : [para]).map((line, j) => (
                  <span key={j} className="block">
                    {line}
                  </span>
                ))}
              </p>
            ))}
          </div>

          <div className="mt-7 flex flex-wrap items-center gap-3 text-ui">
            <a
              href={CONFIG.paperPdf}
              download="PayBench - A Benchmark for Unsafe Commercial Autonomy.pdf"
              className="tap-link rounded-lg bg-ink px-4 py-2 text-paper transition-colors hover:bg-accent"
            >
              Download PDF
            </a>
            <a
              href={CONFIG.repoUrl}
              target="_blank"
              rel="noreferrer"
              className="tap-link rounded-lg border border-ink px-4 py-2 transition-colors hover:bg-ink hover:text-paper"
            >
              View on GitHub
            </a>
          </div>
        </div>

        <PaperPreview />
      </div>
    </header>
  );
}
