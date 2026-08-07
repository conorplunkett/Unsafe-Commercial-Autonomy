import { SectionDivider } from "./SectionDivider";
import { Card } from "@/components/ui/Card";

const WORKS: {
  name: string;
  links: { label: string; href: string }[];
  detail: string;
}[] = [
  {
    name: "τ-bench",
    links: [{ label: "τ-bench", href: "https://arxiv.org/abs/2406.12045" }],
    detail:
      "Tool-agent-user interaction in airline and retail domains, scoring task success and policy adherence in a cooperative setting. Measures whether an agent can follow rules when asked, not whether it preserves commercial intent under adversarial or economically tempting conditions with money at stake.",
  },
  {
    name: "ToolEmu",
    links: [{ label: "ToolEmu", href: "https://arxiv.org/abs/2309.15817" }],
    detail:
      "A language-model-emulated sandbox surfacing high-stakes agent failures across 36 tools and 144 cases, including financial loss. Shows emulation can elicit real failures, but builds no matched safe/unsafe pairs and does not ablate payment-specific control layers.",
  },
  {
    name: "AgentDojo / InjecAgent",
    links: [
      { label: "AgentDojo", href: "https://arxiv.org/abs/2406.13352" },
      { label: "InjecAgent", href: "https://arxiv.org/abs/2403.02691" },
    ],
    detail:
      "Measure susceptibility to indirect prompt injection (629 and 1,054 test cases). PayBench treats injection as one failure mode among twelve, situated in checkout and merchant contexts where the injected instruction competes with an explicit spending policy.",
  },
  {
    name: "AgentHarm",
    links: [{ label: "AgentHarm", href: "https://arxiv.org/abs/2410.09024" }],
    detail:
      "110 explicitly malicious tasks across 11 harm categories, testing whether agents comply with overtly malicious requests. PayBench targets the opposite regime: benign tasks where the agent must avoid implicit commercial harm while still acting when action is warranted.",
  },
  {
    name: "WebArena",
    links: [{ label: "WebArena", href: "https://arxiv.org/abs/2307.13854" }],
    detail:
      "Realistic, reproducible web environments including e-commerce, but focused on task capability rather than payment-safety constraints.",
  },
];

export function RelatedWork() {
  return (
    <>
      <SectionDivider id="related" title="Related work">
        Existing benchmarks cover policy adherence, emulated risk, prompt
        injection, and web capability. None isolate whether an agent should
        attempt a payment in the first place.
      </SectionDivider>
      <Card as="details" tone="bare" pad="none" className="group mt-6 overflow-hidden">
        <summary className="flex cursor-pointer items-baseline gap-3 bg-paper-2/40 px-5 py-4 font-serif text-prose list-none marker:content-none [&::-webkit-details-marker]:hidden">
          <span
            aria-hidden
            className="inline-block text-accent transition-transform duration-150 group-open:rotate-90"
          >
            ▸
          </span>
          Related work: τ-bench, ToolEmu, AgentDojo, AgentHarm, WebArena
        </summary>
        <div className="grid gap-5 border-t border-border p-5 md:grid-cols-2">
          {WORKS.map((w) => (
            <div key={w.name}>
              <p className="font-serif text-h4">
                {w.links.map((l, i) => (
                  <span key={l.href}>
                    {i > 0 && " / "}
                    <a
                      href={l.href}
                      target="_blank"
                      rel="noreferrer"
                      className="underline decoration-accent/50 underline-offset-2 transition-colors hover:text-accent"
                    >
                      {l.label}
                    </a>
                  </span>
                ))}
              </p>
              <p className="mt-2 text-small leading-snug text-muted">{w.detail}</p>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}
