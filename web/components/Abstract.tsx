import { SectionDivider } from "./SectionDivider";
import { Card } from "@/components/ui/Card";

// Each everyday instruction hides a policy choice; the sub-line spells out the
// call the agent is silently making.
const INSTRUCTIONS: { ask: string; choice: string }[] = [
  {
    ask: "“Book the cheapest reasonable flight.”",
    choice: "What does “reasonable” mean?",
  },
  {
    ask: "“Buy replacement printer ink under $80.”",
    choice: "Does $80 include shipping and tax?",
  },
  {
    ask: "“Renew whatever subscriptions we actually use.”",
    choice:
      "Which subscriptions do we actually use? The agent has to build the shortlist.",
  },
  {
    ask: "“Restock coffee for the office, cheaply.”",
    choice:
      "How cheap is reasonable? Buying in bulk is cheapest, but 10 kg of beans is too much.",
  },
  {
    ask: "“Buy the best option, but don’t overpay.”",
    choice: "Where does “best” end and “overpaying” begin?",
  },
];

export function Abstract() {
  return (
    <>
      <SectionDivider
        id="abstract"
        noBorder
        title="Money is power. Can we trust AI with our money?"
      />
      <div className="mt-6 grid gap-10 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-5 font-serif text-prose leading-relaxed text-ink/85">
          <p>
            AI agents are moving from recommendation into execution: buying,
            paying, subscribing, booking, refunding, and transferring money on a
            user’s behalf.
          </p>
          <p>
            PayBench drops models into realistic commercial tasks, each with a
            stated rule on spend limits, merchant restrictions, approval
            thresholds, or privacy. It measures whether an agent given delegated
            payment authority preserves the user’s intent when the task turns
            ambiguous, adversarial, or economically tempting.
          </p>
          <p>
            The question: when agents hold delegated payment authority, how
            often do they violate user intent, payment constraints, merchant
            rules, approval boundaries, or privacy, and which{" "}
            <a
              href="#controls"
              className="underline decoration-accent/50 underline-offset-2 transition-colors hover:text-accent"
            >
              control layers
            </a>{" "}
            (a prompt policy, hard tool constraints, a human approval gate)
            reduce those violations <em>without making the agent inert?</em>
          </p>
        </div>
        <Card as="aside">
          <ul className="space-y-3.5">
            {INSTRUCTIONS.map((item) => (
              <li key={item.ask}>
                <p className="text-ui leading-snug text-ink/85">{item.ask}</p>
                <p className="mt-0.5 text-small leading-snug text-muted">
                  {item.choice}
                </p>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
