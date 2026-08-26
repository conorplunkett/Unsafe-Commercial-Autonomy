import { currency } from "@/lib/format";
import {
  POLICY_FIELD_ORDER,
  type ScenarioOffer,
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

function Pills({ values, titles }: { values: string[]; titles?: (string | undefined)[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {values.map((v, i) => (
        <span
          key={v}
          title={titles?.[i]}
          className="rounded-lg border border-border bg-paper-2 px-2 py-0.5 font-mono text-caption text-ink/80"
        >
          {v}
        </span>
      ))}
    </div>
  );
}

// When "purchase" is acceptable but one or more offers carry a disclosure
// marker (unsafe_marker_unless_disclosed -- see OfferCard), that offer is
// unsafe to pay either way (leak if disclosed, fabrication if not), so
// "purchase" can only mean a different, unmarked offer. Surfaced as a
// tooltip rather than a qualifier on the pill itself, since which offer
// qualifies isn't a single word -- see the Offers section for the marker.
function purchaseTitle(offers: ScenarioOffer[]): string | undefined {
  const marked = offers.some((o) => (o.unsafe_marker_unless_disclosed ?? []).length > 0);
  return marked
    ? "Only the offer(s) below without a disclosure marker -- see Offers"
    : undefined;
}

export function PolicyFields({
  policy,
  offers = [],
}: {
  policy: ScenarioPaymentPolicy;
  offers?: ScenarioOffer[];
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
                  values={(value as string[]).map((v) =>
                    key === "acceptable_actions"
                      ? acceptableActionLabel(v, policy.expected_action)
                      : v.replace(/_/g, " "),
                  )}
                  titles={
                    key === "acceptable_actions"
                      ? (value as string[]).map((v) =>
                          v === "purchase" ? purchaseTitle(offers) : undefined,
                        )
                      : undefined
                  }
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
