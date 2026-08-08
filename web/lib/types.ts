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
  /** Phase 2 ablation axis: whether the system prompt added a deadline. */
  urgency?: "none" | "time_pressure" | null;
  /**
   * Phase 2 ablation axis crossed with `urgency`: whether the delegating human
   * was stated to be away. Separate from `urgency` so a behaviour change under
   * pressure can be attributed to the deadline, the absent overseer, or both.
   */
  user_availability?: "none" | "unreachable" | null;
  safe_to_act?: boolean | null;
  /** "dropped" / "awaiting_survey" results carry no key claim and are excluded from rates. */
  answer_key_status?:
    | "provisional"
    | "locked"
    | "objective"
    | "dropped"
    | "awaiting_survey"
    | null;
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
  human_top_share?: number | null;
  human_ask_share?: number | null;
  model_id?: string | null;
  model_name?: string | null;
  seed?: number | null;
  block_reasons?: string[];
  // Episode-level detail, only read by the episode browser's JSON panel. Shapes
  // are the harness's (app/models.py) and change with the action schema, so they
  // stay loose here and are rendered as JSON rather than typed field by field.
  // (`stakes` is declared above, where the splits that group on it can rely on
  // the harness's own low/high literal.)
  agent_name?: string | null;
  error?: string | null;
  action?: Record<string, unknown> | null;
  proposed_action?: Record<string, unknown> | null;
  audit_events?: unknown[];
  raw_model_output?: string | null;
}

/** A rate with its numerator, denominator, and Wilson interval. */
export interface RateCI {
  rate: number;
  count: number;
  total: number;
  ci_low?: number;
  ci_high?: number;
}

/** One model's slice of a run's committed metrics (`by_model_name`). */
export interface ModelMetrics {
  total_results?: number;
  error_count?: number;
  unsafe_payment_rate?: number;
  refused_when_safe_rate?: number;
  user_welfare_score?: number;
  unsafe_payment_ci?: RateCI;
  refused_when_safe_ci?: RateCI;
  /**
   * Survey-grounded axes for this model's slice (app/metrics._human_axes).
   * Only the two that pool across runs are typed here: `missed_recovery_ci` is a
   * count over a denominator, and `human_alignment` carries the
   * `scored_results` weight its mean needs. `ask_when_supposed_to` is deliberately
   * absent — a Pearson r cannot be averaged across runs, so it is reported
   * per-run in the axes section rather than pooled on the leaderboard.
   */
  missed_recovery_ci?: RateCI;
  top_choice_match_ci?: RateCI;
  human_alignment?: {
    preferred_mean?: number;
    acceptable_mean?: number | null;
    scored_results?: number;
    scenarios?: number;
  };
}

/** The run's own quality stamp (app/metrics._run_quality). */
export interface RunQuality {
  status?: "ok" | "degraded" | "incomplete" | "empty";
  error_rate?: number;
  error_count?: number;
  reasons?: string[];
}

export interface RunMetrics {
  by_model_name?: Record<string, ModelMetrics>;
  quality?: RunQuality;
  [key: string]: unknown;
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
  model_names?: string[];
  // Top-level `metrics` column, fetched with the run list so the leaderboard
  // never has to download a run's episodes.
  metrics?: RunMetrics | null;
}
