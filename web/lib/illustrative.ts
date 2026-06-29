// Illustrative, hand-set frontier used by the hero figure. These are NOT
// measured results — no benchmark run has been collected yet. The numbers only
// sketch the *hypothesised* shape of the safety–autonomy frontier the proposal
// predicts (Notion §3/§7): as control layers strengthen, the unsafe-payment
// rate falls while the false-refusal rate creeps up, jumping most at the human
// approval gate. The live, data-driven charts (Donut, Findings, Leaderboard)
// only render once a real run is published to Supabase.
export interface FrontierPoint {
  condition: string;
  unsafe: number;
  falseRefusal: number;
}

export const ILLUSTRATIVE_FRONTIER: FrontierPoint[] = [
  { condition: "no_policy", unsafe: 0.62, falseRefusal: 0.03 },
  { condition: "prompt_policy", unsafe: 0.45, falseRefusal: 0.05 },
  { condition: "structured_policy", unsafe: 0.34, falseRefusal: 0.08 },
  { condition: "preflight_check", unsafe: 0.22, falseRefusal: 0.12 },
  { condition: "tool_constraints", unsafe: 0.12, falseRefusal: 0.15 },
  { condition: "approval_gate", unsafe: 0.05, falseRefusal: 0.28 },
];
