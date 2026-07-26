export interface Result {
  scenario_id: string;
  scenario_title: string;
  category: string;
  verdict: "safe" | "unsafe" | "refused_when_safe" | "welfare_loss" | "error";
  failure_metrics: string[];
  unsafe_payment: boolean;
  refused_when_safe: boolean;
  /** @deprecated pre-2026-07 runs used this key; readers fall back via `?? false_refusal`. */
  false_refusal?: boolean;
  user_welfare_score: number;
  control_condition?: string | null;
  framing?: string | null;
  /** Phase 2 ablation axis: whether the system prompt added time pressure. */
  urgency?: "none" | "time_pressure" | null;
  safe_to_act?: boolean | null;
  /** "dropped" / "awaiting_survey" results carry no key claim and are excluded from rates. */
  answer_key_status?: "provisional" | "locked" | "dropped" | "awaiting_survey" | null;
  /** True for the survey-derived-preference half of a pair; see app/models.py. */
  semantic_only?: boolean;
  stakes?: "low" | "high" | null;
  /**
   * Survey-grounded axes (app/models.py). Additive to the two binary rates,
   * which keep their definitions. Absent on runs scored before 2026-07-24, so
   * every reader treats them as optional and reports "—" rather than zero.
   */
  missed_recovery?: boolean;
  /** The one acceptable stop the key names, when it can grade the stop at all. */
  recovery_expected?: string | null;
  /** Coarse slot the action landed in, shared with the survey ballot: ask, refuse, proceed_*. */
  action_slot?: string | null;
  human_preferred_share?: number | null;
  human_acceptable_share?: number | null;
  human_ask_share?: number | null;
  model_id?: string | null;
  model_name?: string | null;
  seed?: number | null;
  block_reasons?: string[];
}

/** Wilson interval over a count, as emitted by app/metrics._rate_with_ci. */
export interface RateCI {
  count: number;
  total: number;
  rate: number;
  ci_low: number;
  ci_high: number;
}

export interface Run {
  run_id: string;
  created_at: string;
  phase?: string | null;
  label?: string | null;
  model_ids?: string[];
  model_names?: string[];
  results: Result[];
  metrics?: Record<string, unknown>;
}

export interface RunMeta {
  run_id: string;
  created_at: string;
  published_at?: string;
  phase?: string | null;
  label?: string | null;
}
