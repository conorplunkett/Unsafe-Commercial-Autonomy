import { SectionDivider } from "./SectionDivider";

const WORKS: { name: string; detail: string }[] = [
  {
    name: "τ-bench",
    detail:
      "Tool-agent-user interaction in airline and retail domains, scoring task success and policy adherence in a cooperative setting. Measures whether an agent can follow rules when asked, not whether it preserves commercial intent under adversarial or economically tempting conditions with money at stake.",
  },
  {
    name: "ToolEmu",
    detail:
      "A language-model-emulated sandbox surfacing high-stakes agent failures across 36 tools and 144 cases, including financial loss. Shows emulation can elicit real failures, but builds no matched safe/unsafe pairs and does not ablate payment-specific control layers.",
  },
  {
    name: "AgentDojo / InjecAgent",
    detail:
      "Measure susceptibility to indirect prompt injection (629 and 1,054 test cases). PayBench treats injection as one failure mode among twelve, situated in checkout and merchant contexts where the injected instruction competes with an explicit spending policy.",
  },
  {
    name: "AgentHarm",
    detail:
      "110 explicitly malicious tasks across 11 harm categories, testing whether agents comply with overtly malicious requests. PayBench targets the opposite regime: benign tasks where the agent must avoid implicit commercial harm while still acting when action is warranted.",
  },
  {
    name: "WebArena",
    detail:
      "Realistic, reproducible web environments including e-commerce, but focused on task capability rather than payment-safety constraints.",
  },
];

export function RelatedWork() {
  return (
    <>
      <SectionDivider eyebrow="Related work" title="What exists, and the gap">
        Existing benchmarks cover policy adherence, emulated risk, prompt
        injection, and web capability, but none isolate whether an agent should
        attempt a payment in the first place.
      </SectionDivider>
      <div className="mt-8 grid gap-5 md:grid-cols-2">
        {WORKS.map((w) => (
          <div key={w.name} className="rounded-xl border border-border bg-paper-2/40 p-5">
            <p className="font-serif text-xl">{w.name}</p>
            <p className="mt-2 text-sm leading-snug text-muted">{w.detail}</p>
          </div>
        ))}
        <div className="rounded-xl border border-accent/30 bg-accent/[0.05] p-5">
          <p className="label mb-2 text-accent">The gap</p>
          <p className="text-sm leading-snug text-ink/85">
            No existing benchmark isolates whether an agent <em>should</em>{" "}
            attempt a payment given delegated authority, scores behaviour along a
            safety–autonomy frontier using matched safe/unsafe pairs, or ablates
            payment-specific control layers such as a scoped credential, a
            policy layer, or an approval gate. PayBench fills that gap.
          </p>
        </div>
      </div>
    </>
  );
}
