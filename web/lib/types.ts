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
  model_id?: string | null;
  model_name?: string | null;
  seed?: number | null;
  block_reasons?: string[];
  // Episode-level detail, only read by the episode browser's JSON panel. Shapes
  // are the harness's (app/models.py) and change with the action schema, so they
  // stay loose here and are rendered as JSON rather than typed field by field.
  stakes?: string | null;
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
}

export interface RunMetrics {
  by_model_name?: Record<string, ModelMetrics>;
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
