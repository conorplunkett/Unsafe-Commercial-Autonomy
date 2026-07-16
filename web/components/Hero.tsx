import { CONFIG } from "@/lib/config";

const LEDE_1 =
  "AI shopping has been “coming soon” for years. But nobody trusts AI to spend their money yet. The industry has not developed a measurable frontier for “safe agentic payments” yet.";
const LEDE_2 =
  "PayBench provides that benchmark. It runs models through a gauntlet of payment scenarios. Half are traps: a subscription that jumps from $2 to $200 30 days in, a merchant on the exclusion list, a prompt injection buried in a product page. Each trap has a harmless lookalike the agent should simply buy safely.";
const LEDE_3 =
  "Together they map the agentic payment frontier: agents that spend on their own when it's safe, and stop to ask when it isn't.";

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
        className="group block overflow-hidden rounded-md border border-border bg-white shadow-sm transition-shadow hover:shadow-md"
      >
        <object
          data={`${CONFIG.paperPdf}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`}
          type="application/pdf"
          aria-hidden="true"
          tabIndex={-1}
          className="pointer-events-none aspect-[3/4] w-full"
        >
          <div className="flex aspect-[3/4] w-full items-center justify-center bg-ink/5 p-6 text-center font-mono text-xs text-muted">
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
          <h1 className="font-serif text-6xl leading-[0.98] tracking-tight sm:text-[5rem]">
            Pay<span className="text-accent">Bench</span>
          </h1>
          <p className="mt-4 max-w-3xl font-serif text-xl italic leading-snug text-ink/80 sm:text-2xl">
            A benchmark for unsafe commercial autonomy in AI agents with
            delegated payment authority.
          </p>
          <p className="mt-4 font-mono text-sm text-muted">
            <a href="mailto:hello@conorplunkett.com" className="text-inherit no-underline">
              Conor Plunkett
            </a>{" "}
            · Independent researcher
          </p>

          <div className="mt-6 max-w-2xl space-y-4 text-lg leading-relaxed text-ink/85">
            <p>{LEDE_1}</p>
            <p>{LEDE_2}</p>
            <p>{LEDE_3}</p>
          </div>

          <div className="mt-7 flex flex-wrap items-center gap-3 font-serif text-[1.05rem]">
            <a
              href={CONFIG.paperPdf}
              download="PayBench - A Benchmark for Unsafe Commercial Autonomy.pdf"
              className="rounded-md bg-ink px-4 py-2 text-paper transition-colors hover:bg-accent"
            >
              Download PDF
            </a>
            <a
              href={CONFIG.repoUrl}
              target="_blank"
              rel="noreferrer"
              className="rounded-md border border-ink px-4 py-2 transition-colors hover:bg-ink hover:text-paper"
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
