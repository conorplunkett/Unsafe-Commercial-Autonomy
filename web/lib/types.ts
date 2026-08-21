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
  /** @deprecated the per-episode welfare scalar was removed 2026-08-18; older stored runs still carry it. */
  user_welfare_score?: number;
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
  over_refusal_scoring_enabled?: boolean | null;
  /**
   * Only "excluded" results carry no key claim and are excluded from rates.
   * "awaiting_survey" is scored under the team's provisional key (ground
   * truth until the Phase 2 survey locks it); mirrors UNKEYED_STATUSES in
   * app/metrics.py.
   */
  answer_key_status?:
    | "provisional_answer"
    | "survey_locked_70"
    | "objective"
    | "excluded"
    | "awaiting_survey"
    | "unsafe_clear_safe_unclear"
    | null;
  /** True for the survey-derived-preference half of a pair; see app/models.py. */
  semantic_only?: boolean;
  /**
   * Which half of its authored pair this scenario is. The headline unsafe rate
   * conditions on it (unsafe verdicts / keyed traps); absent on runs stored
   * before 2026-08-11, where readers fall back to the all-keyed denominator.
   */
  pair_role?: "trap" | "lookalike" | null;
  /**
   * The pair this scenario belongs to (e.g. "v2_a4"), joining a trap to its
   * lookalike for payment_effectiveness. Absent on runs stored before
   * 2026-08-18; readers fall back to deriving it from scenario_id.
   */
  pair_id?: string | null;
  stakes?: "low" | "high" | null;
  /**
   * Survey-grounded axes (app/models.py). Additive to the two binary rates,
   * which keep their definitions. Absent on runs scored before 2026-07-24, so
   * every reader treats them as optional and reports "—" rather than zero.
   */
  /** Renamed from missed_recovery on 2026-08-18; readers fall back via `?? missed_recovery`. */
  incorrect_stoppage?: boolean;
  /** @deprecated old stored runs only; see incorrect_stoppage. */
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
  audit_events?: AuditEvent[];
  raw_model_output?: string | null;
  raw_reasoning?: string | null;
}

export interface NavigationTrace {
  entry_url: string;
  redirect_chain: string[];
  final_url: string;
}

export interface AuditEvent {
  event_type?: string;
  code?: string;
  detail?: {
    navigation?: NavigationTrace;
    [key: string]: unknown;
  };
  [key: string]: unknown;
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
  /** @deprecated the run-level welfare product was replaced by payment_effectiveness on 2026-08-18. */
  user_welfare_score?: number;
  /**
   * The headline: share of trap/lookalike pairs where both halves ended safe.
   * `count`/`total` are pair-seed units (poolable like every other CI);
   * `pairs` is the n quoted beside the rate. Absent on runs published before
   * 2026-08-18 — render "—", never 0.
   */
  payment_effectiveness_rate?: number;
  payment_effectiveness_ci?: RateCI & { pairs?: number; excluded_pair_seeds?: number };
  /** Harm axis (2026-08-18): parent + children over the keyed piles. */
  harm_across_trap_and_lookalike_ci?: RateCI;
  fell_for_trap_ci?: RateCI;
  attempted_harm_ci?: RateCI;
  harm_outside_traps_ci?: RateCI;
  /** Completion-axis children of refused_when_safe (2026-08-18). */
  refused_clean_ci?: RateCI;
  abandoned_after_block_ci?: RateCI;
  unsafe_payment_ci?: RateCI;
  /**
   * Which denominator unsafe_payment_ci was computed over: "keyed_traps" (the
   * trap-conditional headline, 2026-08-11 on) or "all_keyed_legacy" (results
   * stored before pair_role existed). Pooling reads it so the two definitions
   * are never summed together.
   */
  unsafe_denominator?: "keyed_traps" | "all_keyed_legacy";
  /** Unsafe verdicts outside the trap pile (botched execution on a benign scenario). */
  unsafe_outside_traps_ci?: RateCI;
  refused_when_safe_ci?: RateCI;
  /**
   * Survey-grounded axes for this model's slice (app/metrics._human_axes).
   * Only the two that pool across runs are typed here: `incorrect_stoppage_ci` is a
   * count over a denominator, and `human_acceptance` carries the
   * `scored_results` weight its mean needs. `ask_when_supposed_to` is deliberately
   * absent — a Pearson r cannot be averaged across runs, so it is reported
   * per-run in the axes section rather than pooled on the leaderboard.
   */
  incorrect_stoppage_ci?: RateCI;
  /** @deprecated old stored runs only; see incorrect_stoppage_ci. */
  missed_recovery_ci?: RateCI;
  human_preferred_alignment_ci?: RateCI;
  /** @deprecated old stored runs only; see human_preferred_alignment_ci. */
  top_choice_match_ci?: RateCI;
  human_acceptance?: {
    preferred_mean?: number;
    acceptable_mean?: number | null;
    scored_results?: number;
    scenarios?: number;
  };
  /** @deprecated old stored runs only; see human_acceptance. */
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
  // run_id of the merged run that pooled this one's episodes (app/merge.py).
  // Set means every episode here also lives in that run, so this row is
  // excluded from the pooled leaderboard — it is still listed and readable.
  superseded_by?: string | null;
}
