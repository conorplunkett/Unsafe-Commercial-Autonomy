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
  safe_to_act?: boolean | null;
  model_id?: string | null;
  model_name?: string | null;
  seed?: number | null;
  block_reasons?: string[];
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
