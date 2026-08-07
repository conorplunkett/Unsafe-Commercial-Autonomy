import { SectionDivider } from "./SectionDivider";

// Inline external reference. All links point at the leading agent-scoped
// offering for that control.
function Ref({ href, children }: { href: string; children: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="underline decoration-accent/50 underline-offset-2 transition-colors hover:text-accent"
    >
      {children}
    </a>
  );
}

export function WhyThisMatters() {
  return (
    <>
      <SectionDivider id="why" eyebrow="Motivation" title="Why this matters" />
      <div className="mt-6 grid gap-10 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-5 font-serif text-prose leading-relaxed text-ink/85">
          <p>
            Emerging agentic payment systems already expose the controls this
            requires:{" "}
            <Ref href="https://docs.stripe.com/agentic-commerce">
              delegated payment methods
            </Ref>
            ,{" "}
            <Ref href="https://corporate.visa.com/en/products/intelligent-commerce.html">
              scoped cards
            </Ref>
            ,{" "}
            <Ref href="https://docs.cdp.coinbase.com/agentkit/docs/welcome">
              stablecoin wallets
            </Ref>
            ,{" "}
            <Ref href="https://www.agenticcommerce.dev/">
              card-based checkout
            </Ref>
            , <Ref href="https://www.x402.org/">x402 payments</Ref>,{" "}
            <Ref href="https://ap2-protocol.org/">agent credentials</Ref>,{" "}
            <Ref href="https://docs.stripe.com/issuing/controls/spending-controls">
              spend controls
            </Ref>
            , and human approval flows. Authorization is the well-understood
            part.
          </p>
          <p className="font-semibold text-ink">
            A chatbot giving bad shopping advice is low-stakes. An agent buying
            the wrong thing, overspending, subscribing the user, leaking
            personal data, or paying the wrong counterparty is a real-world
            harm.
          </p>
          <blockquote className="border-l-[3px] border-accent pl-5 font-serif text-h3 italic leading-snug text-ink">
            Delegated payment is also a tractable proxy for delegated resource
            control: the same failure modes appear when agents manage compute,
            credentials, API budgets, procurement, or cloud resources.
          </blockquote>
          <p className="font-semibold text-ink">
            Money is power. An agent with $100,000 of spend authority is a very
            different risk from one with $10, yet today both ship with the same
            vibes-based confidence.
          </p>
        </div>
        <figure className="self-start border-l-2 border-accent pl-5">
          <blockquote className="font-serif text-h3 leading-snug text-ink">
            “Payment authorization is relatively well-understood. The harder
            unsolved question is whether the agent should attempt the payment in
            the first place.”
          </blockquote>
        </figure>
      </div>
    </>
  );
}
