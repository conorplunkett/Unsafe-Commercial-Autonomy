import Link from "next/link";
import { HeroChart } from "./HeroChart";
import { CONFIG, HAS_PAPER } from "@/lib/config";

const LEDE_1 =
  "AI agents are moving from recommendation into execution — buying, paying, subscribing, booking, refunding, and transferring money on a user's behalf. Authorizing a payment is the easy part. The harder, unsolved question is whether the agent should attempt the payment at all.";
const LEDE_2 =
  "PayBench drops models into realistic commercial tasks, each with a stated rule on spend limits, merchant restrictions, approval thresholds, or privacy — then measures whether the agent preserves the user's intent when the task turns ambiguous, adversarial, or economically tempting, and which control layers fix it without making the agent inert.";

export function Hero() {
  return (
    <header id="summary" className="scroll-mt-20 pt-14 sm:pt-20">
      <p className="label">A benchmark for AI agents spending human money</p>
      <h1 className="mt-4 font-serif text-6xl leading-[0.98] tracking-tight sm:text-[5rem]">
        Pay<span className="text-accent">Bench</span>
      </h1>
      <p className="mt-4 max-w-3xl font-serif text-xl italic leading-snug text-ink/80 sm:text-2xl">
        A benchmark for unsafe commercial autonomy in AI agents with delegated
        payment authority.
      </p>
      <p className="mt-4 font-mono text-sm text-muted">
        Conor Plunkett · Independent researcher
      </p>

      <div className="mt-6 max-w-2xl space-y-4 text-lg leading-relaxed text-ink/85">
        <p>{LEDE_1}</p>
        <p>{LEDE_2}</p>
      </div>

      <div className="mt-7 flex flex-wrap items-center gap-3 font-serif text-[1.05rem]">
        <a
          href={HAS_PAPER ? CONFIG.paperUrl : "#abstract"}
          target={HAS_PAPER ? "_blank" : undefined}
          rel={HAS_PAPER ? "noreferrer" : undefined}
          className="rounded-md bg-ink px-4 py-2 text-paper transition-colors hover:bg-accent"
        >
          {HAS_PAPER ? "Read the paper" : "Read the abstract"}
        </a>
        <Link
          href="/run"
          className="rounded-md border border-accent bg-accent/10 px-4 py-2 text-accent transition-colors hover:bg-accent hover:text-paper"
        >
          Run it yourself with your own key →
        </Link>
        <a
          href={CONFIG.repoUrl}
          target="_blank"
          rel="noreferrer"
          className="rounded-md border border-ink px-4 py-2 transition-colors hover:bg-ink hover:text-paper"
        >
          View on GitHub
        </a>
      </div>

      <figure className="mt-12">
        <HeroChart />
        <figcaption className="mt-3 text-center font-mono text-xs text-muted">
          The safety–autonomy frontier as control layers strengthen — unsafe
          payments fall, false refusals creep up.
        </figcaption>
      </figure>
    </header>
  );
}
