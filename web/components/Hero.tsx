import { HeroChart } from "./HeroChart";

const LEDE_1 =
  "AI agents are moving from recommendation into execution — buying, paying, subscribing, booking, refunding, and transferring money on a user's behalf. Authorizing a payment is the easy part. The harder question is whether the agent should attempt the payment at all.";
const LEDE_2 =
  "This benchmark drops models into realistic commercial tasks, each with a stated rule on spend limits, merchant restrictions, approval thresholds, or privacy — then checks whether the agent preserves the user's intent when the task turns ambiguous, adversarial, or economically tempting.";

export function Hero() {
  return (
    <header id="summary" className="scroll-mt-20 pt-14 sm:pt-20">
      <p className="label">A benchmark for agents spending human money</p>
      <h1 className="mt-4 font-serif text-5xl leading-[1.04] tracking-tight sm:text-[4.25rem]">
        Unsafe Commercial Autonomy
      </h1>
      <div className="mt-6 max-w-2xl space-y-4 text-lg leading-relaxed text-ink/85">
        <p>{LEDE_1}</p>
        <p>{LEDE_2}</p>
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
