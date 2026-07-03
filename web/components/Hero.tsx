import { CONFIG, HAS_PAPER } from "@/lib/config";

const LEDE_1 =
  "AI agents are moving from recommendation into execution — buying, paying, subscribing, booking, refunding, and transferring money on a user's behalf. Authorizing a payment is the easy part. The harder, unsolved question is whether the agent should attempt the payment at all.";
const LEDE_2 =
  "PayBench drops models into realistic commercial tasks, each with a stated rule on spend limits, merchant restrictions, approval thresholds, or privacy — then measures whether the agent preserves the user's intent when the task turns ambiguous, adversarial, or economically tempting, and which control layers fix it without making the agent inert.";

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
            PDF preview unavailable — click to open the paper.
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
          <p className="label">A benchmark for AI agents spending human money</p>
          <h1 className="mt-4 font-serif text-6xl leading-[0.98] tracking-tight sm:text-[5rem]">
            Pay<span className="text-accent">Bench</span>
          </h1>
          <p className="mt-4 max-w-3xl font-serif text-xl italic leading-snug text-ink/80 sm:text-2xl">
            A benchmark for unsafe commercial autonomy in AI agents with
            delegated payment authority.
          </p>
          <p className="mt-4 font-mono text-sm text-muted">
            Conor Plunkett · Independent researcher
          </p>
          {/* Once results are live: remove this status line. */}
          <p className="mt-3 inline-flex flex-wrap items-center gap-x-2 rounded-full border border-warn/40 bg-warn/10 px-3.5 py-1.5 font-mono text-xs text-ink/80">
            <span className="font-medium uppercase tracking-wider text-warn">
              Research proposal
            </span>
            <span aria-hidden>·</span>
            <span>
              scenario set locked, validation survey starting — no results yet
            </span>
          </p>

          <div className="mt-6 max-w-2xl space-y-4 text-lg leading-relaxed text-ink/85">
            <p>{LEDE_1}</p>
            <p>{LEDE_2}</p>
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
              href={HAS_PAPER ? CONFIG.paperUrl : "#abstract"}
              target={HAS_PAPER ? "_blank" : undefined}
              rel={HAS_PAPER ? "noreferrer" : undefined}
              className="rounded-md border border-ink px-4 py-2 transition-colors hover:bg-ink hover:text-paper"
            >
              {HAS_PAPER ? "Read the paper" : "Read the abstract"}
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
