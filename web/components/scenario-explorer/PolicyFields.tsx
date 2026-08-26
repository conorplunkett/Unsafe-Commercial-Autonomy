import { currency } from "@/lib/format";
import {
  POLICY_FIELD_ORDER,
  type ScenarioPaymentPolicy,
} from "@/lib/scenarioExplorer";

const FIELD_LABELS: Record<string, string> = {
  max_total_spend: "Max total spend",
  approval_threshold: "Approval threshold",
  allowed_merchants: "Allowed merchants",
  allow_subscriptions: "Allow subscriptions",
  allowed_payment_types: "Allowed payment types",
  privacy_allowed_fields: "Privacy allowed fields",
  refundable_only: "Refundable only",
  prohibited_categories: "Prohibited categories",
  prohibit_unclear_ingredients: "Prohibit unclear ingredients",
  requires_delivery_proof: "Requires delivery proof",
  expected_action: "Expected action",
  acceptable_actions: "Acceptable actions",
};

const CURRENCY_FIELDS = new Set(["max_total_spend", "approval_threshold"]);
const PILL_FIELDS = new Set([
  "allowed_merchants",
  "allowed_payment_types",
  "privacy_allowed_fields",
  "prohibited_categories",
  "acceptable_actions",
]);
const BOOLEAN_FIELDS = new Set([
  "allow_subscriptions",
  "refundable_only",
  "prohibit_unclear_ingredients",
  "requires_delivery_proof",
]);

// Expected actions that already mean "just complete the purchase". Any other
// expected action narrows what a compliant purchase looks like, so the
// `purchase` pill carries it as a qualifier (e.g. "purchase · select standard
// shipping").
const PLAIN_PURCHASE_EXPECTATIONS = new Set(["buy", "pay", "purchase", "proceed"]);

function acceptableActionLabel(value: string, expectedAction?: string): string {
  if (
    value === "purchase" &&
    expectedAction &&
    !PLAIN_PURCHASE_EXPECTATIONS.has(expectedAction)
  ) {
    return `purchase · ${expectedAction.replace(/_/g, " ")}`;
  }
  return value.replace(/_/g, " ");
}

function Pills({ values }: { values: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {values.map((v) => (
        <span
          key={v}
          className="rounded-lg border border-border bg-paper-2 px-2 py-0.5 font-mono text-caption text-ink/80"
        >
          {v}
        </span>
      ))}
    </div>
  );
}

export function PolicyFields({ policy }: { policy: ScenarioPaymentPolicy }) {
  const present = POLICY_FIELD_ORDER.filter(
    (key) => policy[key] !== undefined && policy[key] !== null,
  );

  if (!present.length) {
    return <p className="mt-1 text-ui">None</p>;
  }

  return (
    <dl className="mt-1.5 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-2 text-small">
      {present.map((key) => {
        const value = policy[key];
        return (
          <div key={key} className="contents">
            <dt className="text-muted">{FIELD_LABELS[key] ?? String(key).replace(/_/g, " ")}</dt>
            <dd>
              {CURRENCY_FIELDS.has(key) ? (
                <span className="font-mono tabular-nums">{currency(value as number)}</span>
              ) : BOOLEAN_FIELDS.has(key) ? (
                value ? "Yes" : "No"
              ) : PILL_FIELDS.has(key) ? (
                <Pills
                  values={(value as string[]).map((v) =>
                    key === "acceptable_actions"
                      ? acceptableActionLabel(v, policy.expected_action)
                      : v.replace(/_/g, " "),
                  )}
                />
              ) : (
                String(value).replace(/_/g, " ")
              )}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
