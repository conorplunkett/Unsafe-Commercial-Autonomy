import type { Run, Result } from "./types";

// Deterministic illustrative dataset. Used as a fallback so the page renders
// before the first real run is published (and when Supabase is unreachable,
// e.g. in local/offline builds). It is clearly labelled "Sample" in the UI.
function mulberry32(seed: number) {
  let a = seed;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const CATEGORIES = [
  "spend_limits",
  "authorization_scope",
  "consent_and_escalation",
  "privacy_and_disclosure",
  "adversarial_robustness",
];
const CONDITIONS = [
  "no_policy",
  "prompt_policy",
  "structured_policy",
  "preflight_check",
  "tool_constraints",
  "approval_gate",
];
const FRAMINGS = ["evaluation", "deployment"];

// Unsafe-action likelihood falls as control layers strengthen; false-refusal
// likelihood creeps up, most under the human-approval gate. This is the
// safety–autonomy frontier the benchmark is designed to surface.
const UNSAFE_P: Record<string, number> = {
  no_policy: 0.62,
  prompt_policy: 0.45,
  structured_policy: 0.34,
  preflight_check: 0.27,
  tool_constraints: 0.15,
  approval_gate: 0.08,
};
const FALSE_P: Record<string, number> = {
  no_policy: 0.04,
  prompt_policy: 0.05,
  structured_policy: 0.07,
  preflight_check: 0.09,
  tool_constraints: 0.12,
  approval_gate: 0.21,
};
const FAILS: Record<string, string[]> = {
  spend_limits: ["budget_total_exceeded", "fee_blindness"],
  authorization_scope: ["merchant_unauthorized", "approval_threshold_evasion"],
  consent_and_escalation: ["recurring_payment_consent", "approval_required"],
  privacy_and_disclosure: ["privacy_overdisclosure"],
  adversarial_robustness: ["prompt_injection_followed"],
};

function pick<T>(arr: T[], rng: () => number): T {
  return arr[Math.floor(rng() * arr.length)];
}

function makeResult(
  scenarioId: string,
  title: string,
  category: string,
  condition: string,
  framing: string,
  model: { id: string; name: string },
  seed: number,
  safeToAct: boolean,
  unsafe: boolean,
  refuse: boolean,
  rng: () => number,
): Result {
  const failure_metrics = unsafe ? [pick(FAILS[category], rng)] : [];
  const verdict: Result["verdict"] = unsafe
    ? "unsafe"
    : refuse
      ? "refused_when_safe"
      : "safe";
  const welfare = unsafe
    ? 0.2 + rng() * 0.3
    : refuse
      ? 0.55 + rng() * 0.2
      : 0.9 + rng() * 0.1;
  return {
    scenario_id: scenarioId,
    scenario_title: title,
    category,
    verdict,
    failure_metrics,
    unsafe_payment: unsafe,
    refused_when_safe: refuse,
    user_welfare_score: Math.min(1, welfare),
    control_condition: condition,
    framing,
    safe_to_act: safeToAct,
    model_id: model.id,
    model_name: model.name,
    seed,
  };
}

const MODELS = [
  { id: "model-a", name: "Model A" },
  { id: "model-b", name: "Model B" },
  { id: "model-c", name: "Model C" },
];

function build(): Run {
  const rng = mulberry32(20270616);
  const results: Result[] = [];
  let modelCursor = 0;
  for (const category of CATEGORIES) {
    for (let k = 0; k < 3; k++) {
      // Stable scenario ids reused across every condition/framing, so the
      // distinct-scenario count reads like a real benchmark (30 here).
      const trapId = `scn_${category}_${k}_trap`;
      const lookId = `scn_${category}_${k}_look`;
      for (const condition of CONDITIONS) {
        for (const framing of FRAMINGS) {
          const model = MODELS[modelCursor++ % MODELS.length];
          const seed = (modelCursor % 5) + 1;
          results.push(
            makeResult(
              trapId,
              `${category.replace(/_/g, " ")} trap ${k + 1}`,
              category,
              condition,
              framing,
              model,
              seed,
              false,
              rng() < UNSAFE_P[condition],
              false,
              rng,
            ),
          );
          results.push(
            makeResult(
              lookId,
              `${category.replace(/_/g, " ")} lookalike ${k + 1}`,
              category,
              condition,
              framing,
              model,
              seed,
              true,
              false,
              rng() < FALSE_P[condition],
              rng,
            ),
          );
        }
      }
    }
  }
  return {
    run_id: "sample",
    created_at: "2026-06-15T18:00:00Z",
    phase: "phase2",
    label: "Sample data — illustrative",
    model_ids: ["model-a", "model-b", "model-c"],
    results,
  };
}

export const SAMPLE_RUN: Run = build();
