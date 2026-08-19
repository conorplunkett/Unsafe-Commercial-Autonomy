export const CONDITION_ORDER = [
  "no_policy",
  "prompt_policy",
  "structured_policy",
  "required_check",
  "tool_constraints",
] as const;

export const CONDITION_LABELS: Record<string, string> = {
  no_policy: "No policy",
  prompt_policy: "Prompt policy",
  structured_policy: "Structured policy",
  required_check: "Required check",
  tool_constraints: "Tool constraints",
};

export const CONDITION_SHORT: Record<string, string> = {
  no_policy: "None",
  prompt_policy: "Prompt",
  structured_policy: "Struct",
  required_check: "Required",
  tool_constraints: "Tools",
};

// Read-time alias: rows published before the 2026-08 rename carry
// "preflight_check"; new code writes "required_check".
const LEGACY_CONDITION_ALIASES: Record<string, string> = {
  preflight_check: "required_check",
};

export function normalizeCondition(condition: string): string {
  return LEGACY_CONDITION_ALIASES[condition] ?? condition;
}

// Results with no control_condition predate the 3-condition split; the lab
// dashboard labels them "legacy" and so does the episode browser.
export function controlConditionLabel(condition?: string | null): string {
  if (!condition) return "Legacy";
  const key = normalizeCondition(condition);
  return CONDITION_LABELS[key] ?? key.replace(/_/g, " ");
}

// Verdicts worst-first: the order the episode browser sorts and filters by, so
// unsafe payments sit at the top of the table.
export const VERDICT_ORDER = [
  "unsafe",
  "welfare_loss",
  "refused_when_safe",
  "error",
  "safe",
] as const;

export const VERDICT_LABELS: Record<string, string> = {
  unsafe: "Unsafe",
  welfare_loss: "Welfare loss",
  refused_when_safe: "Refused when safe",
  error: "Error",
  safe: "Safe",
};

export function verdictLabel(verdict?: string | null): string {
  if (!verdict) return "None";
  return VERDICT_LABELS[verdict] ?? verdict.replace(/_/g, " ");
}

// Display names for models published under a harness handle. The always-cheapest
// control agent publishes as "naive-always-cheapest" / "baseline_naive"; it reads
// as "Naive Baseline" everywhere on the site.
const MODEL_DISPLAY_NAMES: Record<string, string> = {
  "naive-always-cheapest": "Naive Baseline",
  baseline_naive: "Naive Baseline",
};

export function modelDisplayName(name?: string | null): string {
  if (!name) return "unknown";
  return MODEL_DISPLAY_NAMES[name] ?? name;
}

// Run labels are free text set at publish time ("naive baseline, full v1, seed
// 1"), so the same rename is applied to the run pickers.
export function runDisplayLabel(label?: string | null): string {
  if (!label) return "";
  return label.replace(/naive([ -]always[ -]cheapest|[ -]baseline)/gi, "Naive Baseline");
}

export const CATEGORY_ORDER = [
  "spend_limits",
  "authorization_scope",
  "consent_and_escalation",
  "privacy_and_disclosure",
  "adversarial_robustness",
] as const;

export const CATEGORY_LABELS: Record<string, string> = {
  spend_limits: "Spend limits",
  authorization_scope: "Authorization scope",
  consent_and_escalation: "Consent & escalation",
  privacy_and_disclosure: "Privacy & disclosure",
  adversarial_robustness: "Adversarial robustness",
};

// One-line descriptions of the five scenario categories, for the explainer grid.
export const CATEGORY_BLURBS: Record<string, string> = {
  spend_limits:
    "Budget caps, taxes, shipping, fees, currency conversion, and recurring charges that push a purchase over the line.",
  authorization_scope:
    "Merchant allowlists, prohibited product categories, and payment-method restrictions the agent must respect.",
  consent_and_escalation:
    "Approval thresholds, irreversible actions, subscriptions, and ambiguity that should trigger a human check.",
  privacy_and_disclosure:
    "Data minimisation: disclosing only the fields a checkout truly requires, not optional personal data.",
  adversarial_robustness:
    "Prompt injection, deceptive pricing, and social engineering that try to override the user's policy.",
};

export function categoryLabel(id: string): string {
  return CATEGORY_LABELS[id] ?? id.replace(/_/g, " ");
}

// Where a scenario's answer key stands: whether it's scored today, and if
// so, on what basis. Used by the Scenario Explorer's status pill.
export const ANSWER_KEY_STATUS_LABELS: Record<string, string> = {
  locked: "Locked",
  objective: "Objective",
  provisional: "Provisional",
  awaiting_survey: "Awaiting survey",
  dropped: "Dropped",
};

export function answerKeyStatusLabel(status?: string | null): string {
  if (!status) return "Unknown";
  return ANSWER_KEY_STATUS_LABELS[status] ?? status.replace(/_/g, " ");
}

// The control conditions supported across both phases, each with a one-line
// description of what layer it adds.
export const CONDITION_DESCRIPTIONS: Record<string, string> = {
  no_policy: "Task and tools only, with no explicit payment policy at all.",
  prompt_policy: "The policy is stated in natural language in the system prompt.",
  structured_policy: "The policy is given as structured fields, but not enforced by tools.",
  required_check: "The agent must call a policy-check tool before paying (allow / block / approval).",
  tool_constraints: "Payment tools hard-enforce caps, merchant allowlists, and rail restrictions.",
};

export interface TaxonomyItem {
  key: string;
  label: string;
  blurb: string;
}

// The failure taxonomy — what the benchmark is looking for. Static, always shown.
export const TAXONOMY: TaxonomyItem[] = [
  { key: "budget", label: "Budget", blurb: "Exceeds an item- or total-level budget." },
  { key: "fees", label: "Fee blindness", blurb: "Ignores shipping, tax, fees, FX, or renewals." },
  { key: "recurring", label: "Recurring", blurb: "Signs the user up for a subscription unasked." },
  { key: "merchant", label: "Merchant", blurb: "Buys from an unapproved or risky merchant." },
  { key: "category", label: "Category", blurb: "Buys outside the permitted product category." },
  { key: "approval", label: "Approval", blurb: "Fails to ask above a threshold or under ambiguity." },
  { key: "evasion", label: "Approval evasion", blurb: "Splits or reroutes to dodge approval." },
  { key: "privacy", label: "Privacy", blurb: "Leaks unnecessary personal or payment data." },
  { key: "injection", label: "Prompt injection", blurb: "Follows merchant or tool text over policy." },
  { key: "settlement", label: "Settlement", blurb: "Pays before verification or delivery." },
  { key: "welfare", label: "User welfare", blurb: "Follows the task but makes a bad call." },
  { key: "audit", label: "Audit", blurb: "Pays with too little reasoning to inspect." },
];
