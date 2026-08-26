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

export interface CheckoutControlChoice {
  value: string;
  label: string;
  [key: string]: unknown;
}

// One merchant checkout control, rendered exactly as the merchant page
// presents it: kind, label, initial state, choices, required.
export interface CheckoutControl {
  control_id: string;
  kind: "checkbox" | "radio" | "select";
  label: string;
  initial_value: boolean | string | null;
  required: boolean;
  choices?: CheckoutControlChoice[];
  [key: string]: unknown;
}

// What picking one control's branch silently does at grading time -- never
// shown on the merchant page, only in the answer key (app/phase2/sandbox.py
// CHECKOUT_EFFECT_FIELDS). `amount`/`amount_delta` change the charged total,
// `recurrence`/`authorizations` can turn a one-time buy into a standing
// charge, `disclosures` names fields that leak, `rail` swaps the payment rail.
export interface CheckoutEffect {
  amount?: number;
  amount_delta?: number;
  rail?: string;
  recurrence?:
    | boolean
    | string
    | { recurring?: boolean; amount?: number; interval?: string; [key: string]: unknown }
    | null;
  disclosures?: string[];
  authorizations?: Array<{ type?: string; amount?: number; interval?: string; [key: string]: unknown }>;
  [key: string]: unknown;
}

export interface OfferCheckout {
  controls: CheckoutControl[];
  // control_id -> branch ("true"/"false" for a checkbox, a choice value for
  // radio/select) -> effect. Scorer-only.
  effects?: Record<string, Record<string, CheckoutEffect>>;
  [key: string]: unknown;
}

// An offer's authored reply options for the send_message tool (see
// _initialize_reply_options / _public_reply_options in app/phase2/sandbox.py).
// `discloses` is scorer-only -- the model picks an option by id and never
// sees it -- kept here only so a reviewer can tell which option is the
// disclosing one without opening the raw JSON record.
export interface ReplyOption {
  id: string;
  text: string;
  discloses?: string[];
  [key: string]: unknown;
}

export interface ReplyOptions {
  recipient: string;
  options: ReplyOption[];
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
  page_url: string;
  page_text: string;
  authored_page_text?: boolean;
  checkout?: OfferCheckout;
  reply_options?: ReplyOptions;
  // Scorer-only markers on specific bait offers -- exactly the "this is the
  // deliberately tempting wrong option" signal a verification pass needs.
  answer_key_trap_marker?: boolean;
  unsafe_marker?: boolean;
  injection_compliance_marker?: boolean;
  // Value-conditioned forms of the two flat markers above, for a trap whose
  // bait is a checkout control state rather than a separate offer (e14's tip
  // choice, e19's ToS checkbox) -- see marker_condition_matches in
  // app/policies.py. control_id -> the checkbox/radio/select branch values
  // that constitute the marked act (checkbox values arrive as JSON booleans).
  answer_key_trap_marker_when?: Record<string, Array<string | boolean>>;
  injection_compliance_marker_when?: Record<string, Array<string | boolean>>;
  // Fields that must appear in disclosed_fields for paying this offer to be
  // safe (d2/d3/d13's "genuine discount vs. invented data" trap) -- see
  // _fabricated_disclosure in app/policies.py. Paying while withholding every
  // named field is the measured failure; no separate offer_id marks it.
  unsafe_marker_unless_disclosed?: string[];
  [key: string]: unknown;
}

export interface ScenarioSandbox {
  offers: ScenarioOffer[];
  checkout_required_fields?: string[];
  checkout_optional_fields?: string[];
  semantic_only?: boolean;
  prompt_injection?: unknown;
  unsafe_disclosure?: string[];
  ambient_context?: string | null;
  capabilities?: Record<string, boolean> | null;
  free_source?: { name: string; current: boolean; [key: string]: unknown } | null;
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

// The tool_constraints arm's reach for one scenario -- from the committed
// projection (data/answer_keys/phase2_enforcement_scope.json), not recomputed
// client-side. `fires_on` is the cheapest surface the rail refuses on: null
// when nothing the world offers trips it (a lookalike in the arm only as its
// trap's pair partner, or a scenario the arm skips entirely).
export interface ScenarioEnforcement {
  rail_reachable: boolean;
  in_enforced_arm: boolean;
  fires_on:
    | "offer_as_listed"
    | "checkout_control"
    | "payment_rail"
    | "optional_disclosure"
    | "unswept"
    | null;
  decisions: string[];
  reasons: string[];
  offers: string[];
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
  expected_safe_behavior: { summary: string; safe_autonomous_allowed: boolean; [key: string]: unknown };
  safe_to_act?: boolean | null;
  phase?: string | null;
  // sha256 of the whole record, computed by generate_scenario_explorer_data.py
  // before this field is added -- see isReviewCurrent() below.
  content_hash: string;
  pair_id: string;
  pair_role: "trap" | "lookalike";
  source_situation?: string | null;
  right_answer: string | null;
  failure_tested: string | null;
  answer_key_status:
    | "provisional_answer"
    | "survey_locked_70"
    | "objective"
    | "excluded"
    | "awaiting_survey"
    | "unsafe_clear_safe_unclear";
  over_refusal_scoring_enabled: boolean | null;
  semantic_only: boolean;
  enforcement: ScenarioEnforcement;
  [key: string]: unknown;
}

export interface ScenarioPair {
  pair_id: string;
  pair_label: string;
  category: string;
  trap: ScenarioExplorerRecord;
  lookalike: ScenarioExplorerRecord;
}

// git blob sha of each source file (data/scenario_sets/v2_250_scenarios.md,
// data/answer_keys/v2_constraints.json) at the moment
// generate_scenario_explorer_data.py last ran, keyed by repo-relative path.
// The Explorer's freshness check compares these against the live blob sha
// GitHub reports for the same paths on `main`.
export interface ScenarioExplorerMeta {
  source_blob_shas: Record<string, string>;
}

export interface ScenarioExplorerPayload {
  pairs: ScenarioPair[];
  count: number;
  meta: ScenarioExplorerMeta;
}

// One row per scenario_id in the scenario_reviews table, fetched from
// admin-scenario-reviews. reviewed_at is stamped server-side -- the client
// only ever sends { scenario_id, reviewed, content_hash }, never a date.
// content_hash is the scenario's content_hash at the moment it was marked
// reviewed, null if it was reviewed before this tracking existed or if
// reviewed is false.
export interface ScenarioReview {
  scenario_id: string;
  reviewed: boolean;
  reviewed_at: string | null;
  content_hash: string | null;
}

// Whether a stored review still describes the scenario as it exists today.
// A review recorded before content_hash tracking shipped (content_hash null)
// is trusted as-is rather than treated as stale -- there's nothing to compare
// it against. Otherwise, any edit to the scenario's record since it was
// reviewed -- text, answer key, enforcement scope, anything -- changes
// content_hash and this reports the review as no longer current, which every
// Explorer view (badge, panel counts, "Mark reviewed" button) reads instead
// of the raw `reviewed` flag.
export function isReviewCurrent(
  review: ScenarioReview | undefined,
  scenario: ScenarioExplorerRecord,
): boolean {
  if (!review?.reviewed) return false;
  if (review.content_hash == null) return true;
  return review.content_hash === scenario.content_hash;
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
