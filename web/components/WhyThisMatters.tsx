import { SectionDivider } from "./SectionDivider";

export function WhyThisMatters() {
  return (
    <>
      <SectionDivider id="why" eyebrow="Motivation" title="Why this matters" />
      <div className="mt-6 grid gap-10 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-5 text-lg leading-relaxed text-ink/85">
          <p>
            Emerging agentic payment systems already expose the controls this
            requires: delegated payment methods, scoped cards, stablecoin
            wallets, card-based checkout, x402 payments, agent credentials,
            spend controls, and human approval flows. Authorization is the
            well-understood part.
          </p>
          <p>
            Traditional fintech QA checks whether a payment system correctly
            authorizes, declines, settles, or logs a transaction. PayBench
            studies whether an AI agent <em>should have attempted</em> the
            transaction in the first place. That makes it an AI safety problem,
            not a payments-reliability one.
          </p>
          <p>
            A chatbot giving bad shopping advice is low-stakes. An agent buying
            the wrong thing, overspending, subscribing the user, leaking
            personal data, or paying the wrong counterparty is a real-world
            harm. Delegated payment is also a tractable proxy for delegated
            resource control: the same failure modes appear when agents manage
            compute, credentials, API budgets, procurement, or cloud resources.
          </p>
        </div>
        <figure className="self-start border-l-2 border-accent pl-5">
          <blockquote className="font-serif text-2xl leading-snug text-ink">
            “Payment authorization is relatively well-understood. The harder
            unsolved question is whether the agent should attempt the payment in
            the first place.”
          </blockquote>
        </figure>
      </div>
    </>
  );
}
