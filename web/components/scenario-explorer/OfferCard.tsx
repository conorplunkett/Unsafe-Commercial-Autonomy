import { currency } from "@/lib/format";
import type { ScenarioOffer } from "@/lib/scenarioExplorer";

const MARKERS: Array<{
  key: keyof ScenarioOffer;
  label: string;
  title: string;
}> = [
  {
    key: "answer_key_trap_marker",
    label: "Trap marker",
    title: "The bait offer this trap's answer key expects the agent not to take",
  },
  {
    key: "unsafe_marker",
    label: "Unsafe marker",
    title: "Completing the task through this offer requires fabricating data the agent doesn't have",
  },
  {
    key: "injection_compliance_marker",
    label: "Injection marker",
    title: "This offer represents complying with an injected/adversarial instruction",
  },
];

export function OfferCard({
  offer,
  index,
  total,
}: {
  offer: ScenarioOffer;
  index: number;
  total: number;
}) {
  const activeMarkers = MARKERS.filter((m) => offer[m.key]);

  return (
    <div className="rounded-lg border border-border p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-small font-medium text-ink">{offer.merchant_name}</p>
          <p className="text-small text-muted">{offer.item}</p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-1.5">
          {total > 1 && (
            <span className="font-mono text-caption text-muted">
              Offer {index + 1} of {total}
            </span>
          )}
          {activeMarkers.map((m) => (
            <span
              key={m.key as string}
              title={m.title}
              className="rounded-full border border-danger/40 bg-danger/10 px-2 py-0.5 font-mono text-caption uppercase tracking-wider text-danger"
            >
              {m.label}
            </span>
          ))}
        </div>
      </div>

      <dl className="mt-3 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 font-mono text-caption tabular-nums">
        <dt className="text-muted">Price</dt>
        <dd className="text-right">{currency(offer.price)}</dd>
        <dt className="text-muted">Shipping</dt>
        <dd className="text-right">{currency(offer.shipping)}</dd>
        <dt className="text-muted">Tax</dt>
        <dd className="text-right">{currency(offer.tax)}</dd>
        {offer.fees.map((fee, i) => (
          <div key={i} className="contents">
            <dt className="text-muted">{fee.label}</dt>
            <dd className="text-right">{currency(fee.amount)}</dd>
          </div>
        ))}
        <dt className="border-t border-border pt-1 font-medium text-ink">Total</dt>
        <dd className="border-t border-border pt-1 text-right font-medium text-ink">
          {currency(offer.total)}
        </dd>
      </dl>

      <p className="mt-2 text-caption text-muted">
        Recurring: {offer.recurring ? "Yes" : "No"}
        {offer.recurring_note ? ` (${offer.recurring_note})` : ""} · Refundable:{" "}
        {offer.refundable ? "Yes" : "No"} · Payment: {offer.payment_types.join(", ")} ·
        Default: {offer.default_payment_type}
        {offer.unclear_ingredients ? " · Unclear ingredients" : ""}
      </p>

      {offer.headline_price != null && offer.headline_price !== offer.price && (
        <p className="mt-1 text-caption text-warn">
          Headline price: {currency(offer.headline_price)}
        </p>
      )}

      <div className="mt-2">
        <p className="text-caption text-muted">Page URL</p>
        <p className="mt-0.5 break-all font-mono text-caption text-ink">
          {offer.page_url}
        </p>
      </div>

      <div className="mt-2">
        <p className="text-caption text-muted">
          Page text{offer.authored_page_text ? " (authored)" : ""}
        </p>
        <p className="mt-0.5 text-small italic leading-snug text-ink/80">
          &ldquo;{offer.page_text}&rdquo;
        </p>
      </div>
    </div>
  );
}
