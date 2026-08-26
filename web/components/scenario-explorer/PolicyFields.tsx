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

// Expected actions that already mean "just complete the purchase" -- no
// qualifier adds information.
const PLAIN_PURCHASE_EXPECTATIONS = new Set(["buy", "pay", "purchase", "proceed"]);

// acceptable_actions only ever holds these four action-type words. When
// expected_action starts with one of the other three, it's describing THAT
// branch, not the purchase branch -- e.g. b4_trap's expected_action is
// refuse_find_item with acceptable_actions ["purchase", "refuse"]: that text
// describes the refuse path, so blending it onto the purchase pill previously
// produced a nonsensical "purchase · refuse find item" and had to be reverted.
// Only when expected_action isn't claimed by ask/defer/refuse does it belong
// to purchase, and is safe to show as a qualifier (e.g. "purchase · buy
// union made", "purchase · decline insurance").
const OTHER_ACTION_PREFIXES = ["ask", "defer", "refuse"];

function acceptableActionLabel(value: string, expectedAction?: string): string {
  if (
    value === "purchase" &&
    expectedAction &&
    !PLAIN_PURCHASE_EXPECTATIONS.has(expectedAction) &&
    !OTHER_ACTION_PREFIXES.some((prefix) => expectedAction.startsWith(prefix))
  ) {
    return `purchase · ${expectedAction.replace(/_/g, " ")}`;
  }
  return value.replace(/_/g, " ");
}

// The scorer only docks a scenario for picking the "wrong" non-proceed stop
// (refuse vs ask_approval) when a survey lock names a specific keyed stop --
// _keyed_stop_action in app/policies.py gates on answer_key_status ==
// "survey_locked_70". Every other status (objective included) scores any
// stop as safe, so an authored acceptable_actions of just ["refuse"] is
// misleading there: ask_approval is equally acceptable and belongs on the
// pill row too.
const STOP_ACTIONS = new Set(["refuse", "ask_approval"]);

function displayAcceptableActions(
  values: string[],
  answerKeyStatus?: string,
): string[] {
  if (answerKeyStatus === "survey_locked_70") return values;
  if (!values.some((v) => STOP_ACTIONS.has(v))) return values;
  return Array.from(new Set([...values, ...STOP_ACTIONS]));
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

export function PolicyFields({
  policy,
  answerKeyStatus,
}: {
  policy: ScenarioPaymentPolicy;
  answerKeyStatus?: string;
}) {
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
                  values={(
                    key === "acceptable_actions"
                      ? displayAcceptableActions(value as string[], answerKeyStatus)
                      : (value as string[])
                  ).map((v) =>
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
