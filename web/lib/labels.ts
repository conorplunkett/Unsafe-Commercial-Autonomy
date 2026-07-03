export const CONDITION_ORDER = [
  "no_policy",
  "prompt_policy",
  "structured_policy",
  "preflight_check",
  "tool_constraints",
  "approval_gate",
] as const;

export const CONDITION_LABELS: Record<string, string> = {
  no_policy: "No policy",
  prompt_policy: "Prompt policy",
  structured_policy: "Structured policy",
  preflight_check: "Preflight check",
  tool_constraints: "Tool constraints",
  approval_gate: "Approval gate",
};

export const CONDITION_SHORT: Record<string, string> = {
  no_policy: "None",
  prompt_policy: "Prompt",
  structured_policy: "Struct",
  preflight_check: "Preflight",
  tool_constraints: "Tools",
  approval_gate: "Approval",
};

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

// The six control conditions as an ordered ladder, weakest to strongest, each
// with a one-line description of what layer it adds.
export const CONDITION_DESCRIPTIONS: Record<string, string> = {
  no_policy: "Task and tools only, with no explicit payment policy at all.",
  prompt_policy: "The policy is stated in natural language in the system prompt.",
  structured_policy: "The policy is given as structured fields, but not enforced by tools.",
  preflight_check: "The agent must call a policy-check tool before paying (allow / block / approval).",
  tool_constraints: "Payment tools hard-enforce caps, merchant allowlists, and rail restrictions.",
  approval_gate: "Unsafe or ambiguous actions pause for explicit human approval before executing.",
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
