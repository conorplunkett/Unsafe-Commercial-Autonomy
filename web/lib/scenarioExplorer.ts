// Types for the Phase 2 Scenario Explorer's data payload, fetched at runtime
// from the admin-scenario-data Supabase Edge Function (never bundled at
// build time -- see web/components/scenario-explorer/ScenarioExplorer.tsx).
//
// Every interface carries an index signature alongside its explicit fields.
// That is deliberate, not laziness: a field this module doesn't give a
// bespoke row still type-checks and still reaches the page through the raw
// JSON fallback in ScenarioSide.tsx, so nothing about a scenario record is
// silently dropped just because this file didn't anticipate it.

export interface OfferFee {
  label: string;
  amount: number;
  [key: string]: unknown;
}

export interface ScenarioOffer {
  offer_id: string;
  merchant_id: string;
  merchant_name: string;
  item: string;
  price: number;
  shipping: number;
  tax: number;
  fees: OfferFee[];
  total: number;
  recurring: boolean;
  recurring_note: string | null;
  refundable: boolean;
  payment_types: string[];
  default_payment_type: string;
  category: string | null;
  unclear_ingredients: boolean;
  headline_price: number | null;
  page_text: string;
  authored_page_text?: boolean;
  // Scorer-only markers on specific bait offers -- exactly the "this is the
  // deliberately tempting wrong option" signal a verification pass needs.
  answer_key_trap_marker?: boolean;
  unsafe_marker?: boolean;
  injection_compliance_marker?: boolean;
  [key: string]: unknown;
}

export interface ScenarioSandbox {
  offers: ScenarioOffer[];
  checkout_required_fields?: string[];
  checkout_optional_fields?: string[];
  semantic_only?: boolean;
  prompt_injection?: unknown;
  unsafe_disclosure?: string[];
  free_source?: unknown;
  [key: string]: unknown;
}

export interface ScenarioEnvironment {
  situation: string;
  pair: string;
  pair_role: "trap" | "lookalike";
  sandbox?: ScenarioSandbox;
  [key: string]: unknown;
}

// The answer-key fields that vary by category. Order here matches
// data/answer_keys/v2_constraints.json's own `_meta.fields` list, which
// PolicyFields.tsx iterates to decide row order.
export interface ScenarioPaymentPolicy {
  max_total_spend?: number;
  approval_threshold?: number;
  allowed_merchants?: string[];
  allow_subscriptions?: boolean;
  allowed_payment_types?: string[];
  privacy_allowed_fields?: string[];
  refundable_only?: boolean;
  prohibited_categories?: string[];
  prohibit_unclear_ingredients?: boolean;
  requires_delivery_proof?: boolean;
  expected_action?: string;
  acceptable_actions?: string[];
  [key: string]: unknown;
}

export interface ScenarioExplorerRecord {
  scenario_id: string;
  title: string;
  category: string;
  payment_mode: string;
  user_instruction: string;
  payment_policy: ScenarioPaymentPolicy;
  hidden_preference: string;
  environment: ScenarioEnvironment;
  unsafe_behavior: string;
  measured_failure: string;
  phase?: string | null;
  pair_id: string;
  pair_role: "trap" | "lookalike";
  stakes: "low" | "high";
  source_situation?: string | null;
  right_answer: string | null;
  failure_tested: string | null;
  answer_key_status:
    | "provisional"
    | "locked"
    | "objective"
    | "dropped"
    | "awaiting_survey";
  safe_to_act: boolean | null;
  semantic_only: boolean;
  [key: string]: unknown;
}

export interface ScenarioPair {
  pair_id: string;
  pair_label: string;
  category: string;
  trap: ScenarioExplorerRecord;
  lookalike: ScenarioExplorerRecord;
}

export interface ScenarioExplorerPayload {
  pairs: ScenarioPair[];
  count: number;
}

// The answer-key's own field inventory, in its documented order -- PolicyFields
// walks this list and renders a row only for fields present on a given scenario.
export const POLICY_FIELD_ORDER: Array<keyof ScenarioPaymentPolicy & string> = [
  "max_total_spend",
  "approval_threshold",
  "allowed_merchants",
  "allow_subscriptions",
  "allowed_payment_types",
  "privacy_allowed_fields",
  "refundable_only",
  "prohibited_categories",
  "prohibit_unclear_ingredients",
  "requires_delivery_proof",
  "expected_action",
  "acceptable_actions",
];
