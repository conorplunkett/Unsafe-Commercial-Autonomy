import { currency } from "@/lib/format";
import type {
  CheckoutControl,
  CheckoutEffect,
  ReplyOption,
  ScenarioOffer,
} from "@/lib/scenarioExplorer";

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

// Both `_when` markers key by control_id -> the branch values that make the
// act. A checkbox's listed values arrive as JSON booleans (true/false); every
// other effect/marker key on the branch is the raw string choice value. This
// mirrors the exact normalization app/phase2/sandbox.py applies when
// validating them, so a branch here always matches a key in `effects`.
function branchKey(value: string | boolean): string {
  if (value === true) return "true";
  if (value === false) return "false";
  return value;
}

// Which markers fire, and what a checkout control's effect does, for one
// branch (a checkbox's checked/unchecked state, or one radio/select choice)
// -- the two things that turn "picking this" into the measured failure.
function branchInfo(
  offer: ScenarioOffer,
  controlId: string,
  branch: string,
): { tags: string[]; effect: CheckoutEffect | undefined } {
  const tags: string[] = [];
  if (branchesFor(offer.answer_key_trap_marker_when, controlId).includes(branch)) {
    tags.push("Trap");
  }
  if (branchesFor(offer.injection_compliance_marker_when, controlId).includes(branch)) {
    tags.push("Injection");
  }
  return { tags, effect: offer.checkout?.effects?.[controlId]?.[branch] };
}

function branchesFor(
  condition: Record<string, Array<string | boolean>> | undefined,
  controlId: string,
): string[] {
  return (condition?.[controlId] ?? []).map(branchKey);
}

// Plain-language summary of one checkout effect -- what silently changes
// about the offer if the agent picks this branch. See CheckoutEffect in
// web/lib/scenarioExplorer.ts for the field meanings.
function describeEffect(effect: CheckoutEffect): string[] {
  const parts: string[] = [];
  if (typeof effect.amount_delta === "number") {
    const sign = effect.amount_delta >= 0 ? "+" : "−";
    parts.push(`${sign}${currency(Math.abs(effect.amount_delta))}`);
  }
  if (typeof effect.amount === "number") {
    parts.push(`total becomes ${currency(effect.amount)}`);
  }
  if (effect.recurrence != null) {
    if (typeof effect.recurrence === "object") {
      const { amount, interval } = effect.recurrence;
      parts.push(
        amount != null
          ? `becomes ${currency(amount)}/${interval ?? "period"} recurring`
          : "becomes recurring",
      );
    } else if (effect.recurrence === true) {
      parts.push("becomes recurring");
    } else if (typeof effect.recurrence === "string") {
      parts.push(effect.recurrence);
    }
  }
  if (effect.rail) parts.push(`rail: ${effect.rail}`);
  if (effect.disclosures?.length) parts.push(`discloses: ${effect.disclosures.join(", ")}`);
  for (const auth of effect.authorizations ?? []) {
    if (typeof auth?.amount === "number") {
      const kind = auth.type ? ` (${String(auth.type).replace(/_/g, " ")})` : "";
      parts.push(`authorizes ${currency(auth.amount)}/${auth.interval ?? "charge"}${kind}`);
    }
  }
  return parts;
}

function BranchTags({ tags, effect }: { tags: string[]; effect: CheckoutEffect | undefined }) {
  const parts = effect ? describeEffect(effect) : [];
  if (!tags.length && !parts.length) return null;
  return (
    <span className="ml-1.5 inline-flex flex-wrap items-center gap-1 align-middle">
      {tags.map((tag) => (
        <span
          key={tag}
          title={
            tag === "Trap"
              ? "Picking this is the bait this trap's answer key expects the agent not to take"
              : "Picking this represents complying with an injected/adversarial instruction"
          }
          className="rounded-full border border-danger/40 bg-danger/10 px-1.5 py-0 font-mono text-caption uppercase tracking-wider text-danger"
        >
          {tag}
        </span>
      ))}
      {parts.length > 0 && (
        <span className="font-mono text-caption text-warn">{parts.join(" · ")}</span>
      )}
    </span>
  );
}

function ControlLabel({ control }: { control: CheckoutControl }) {
  return (
    <span className="text-small text-ink">
      {control.label}
      {control.required && (
        <span aria-hidden className="ml-0.5 text-muted">
          *
        </span>
      )}
    </span>
  );
}

// Static picture of one merchant checkout control in its initial state --
// ticked/unticked, selected/unselected -- exactly as the checkout page
// presents it before the agent touches anything. Not interactive.
//
// Each branch (checked/unchecked, or one radio/select choice) can carry a
// scorer-only trap/injection marker and a checkout effect -- what silently
// happens if the agent picks it, invisible on the merchant page itself. See
// branchInfo/describeEffect above; BranchTags renders whichever of those a
// branch actually has.
function ControlRow({ control, offer }: { control: CheckoutControl; offer: ScenarioOffer }) {
  if (control.kind === "checkbox") {
    const checked = control.initial_value === true;
    return (
      <div>
        <div className="flex items-start gap-2">
          <span
            className={`mt-0.5 flex size-4 shrink-0 items-center justify-center rounded border ${
              checked ? "border-ink bg-ink" : "border-muted bg-paper"
            }`}
          >
            {checked && (
              <svg
                viewBox="0 0 12 12"
                className="size-3 text-paper"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M2.5 6.5 5 9l4.5-6" />
              </svg>
            )}
          </span>
          <ControlLabel control={control} />
        </div>
        {(["true", "false"] as const).map((branch) => {
          const { tags, effect } = branchInfo(offer, control.control_id, branch);
          if (!tags.length && !effect) return null;
          return (
            <p key={branch} className="mt-1 pl-6 text-caption text-muted">
              {branch === "true" ? "If checked" : "If unchecked"}
              <BranchTags tags={tags} effect={effect} />
            </p>
          );
        })}
      </div>
    );
  }

  const choices = control.choices ?? [];

  if (control.kind === "radio") {
    return (
      <div>
        <ControlLabel control={control} />
        <div className="mt-1.5 space-y-1.5">
          {choices.map((choice) => {
            const selected = control.initial_value === choice.value;
            const { tags, effect } = branchInfo(offer, control.control_id, choice.value);
            return (
              <div key={choice.value} className="flex flex-wrap items-start gap-2">
                <span
                  className={`mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full border ${
                    selected ? "border-ink bg-paper" : "border-muted bg-paper"
                  }`}
                >
                  {selected && <span className="size-2 rounded-full bg-ink" />}
                </span>
                <span className="text-small text-ink">{choice.label}</span>
                <BranchTags tags={tags} effect={effect} />
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // select: the option list, with the initial choice (if any) highlighted
  return (
    <div>
      <ControlLabel control={control} />
      <div className="mt-1.5 overflow-hidden rounded border border-border bg-paper">
        {choices.map((choice) => {
          const selected = control.initial_value === choice.value;
          const { tags, effect } = branchInfo(offer, control.control_id, choice.value);
          return (
            <div
              key={choice.value}
              className={`flex flex-wrap items-center gap-1 px-2 py-1 text-small ${
                selected ? "bg-paper-2 font-medium text-ink" : "text-ink/80"
              }`}
            >
              {choice.label}
              <BranchTags tags={tags} effect={effect} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

// One authored reply_options candidate the agent can pick by id via
// send_message -- exactly the text the model reads. `discloses` never
// reaches the model; it's shown here so a reviewer can tell which option is
// the disclosing one without opening the raw JSON record.
function ReplyOptionRow({ option }: { option: ReplyOption }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <p className="text-small italic leading-snug text-ink/80">&ldquo;{option.text}&rdquo;</p>
      {!!option.discloses?.length && (
        <span className="shrink-0 whitespace-nowrap font-mono text-caption text-danger">
          discloses: {option.discloses.join(", ")}
        </span>
      )}
    </div>
  );
}

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
  const discloseUnlessFields = offer.unsafe_marker_unless_disclosed ?? [];
  const disclosureFieldNames = discloseUnlessFields.map((f) => f.replace(/_/g, " ")).join(", ");

  return (
    <div className="rounded-lg border border-border p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-small font-medium text-ink">{offer.merchant_name}</p>
          <p className="text-small text-muted">
            {offer.item}
            {offer.category && ` · ${offer.category.replace(/_/g, " ")}`}
          </p>
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
          {!!discloseUnlessFields.length && (
            <span
              title={`Paying this offer is the measured failure either way: disclosing ${disclosureFieldNames} leaks it, withholding it means the agent invented the data`}
              className="rounded-full border border-danger/40 bg-danger/10 px-2 py-0.5 font-mono text-caption uppercase tracking-wider text-danger"
            >
              Unsafe either way
            </span>
          )}
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

      {!!offer.checkout?.controls?.length && (
        <div className="mt-2">
          <p className="text-caption text-muted">Checkout</p>
          <div className="mt-1 space-y-2.5 rounded-lg border border-border bg-paper-2 p-3">
            {offer.checkout.controls.map((control) => (
              <ControlRow key={control.control_id} control={control} offer={offer} />
            ))}
          </div>
        </div>
      )}

      {!!offer.reply_options?.options?.length && (
        <div className="mt-2">
          <p className="text-caption text-muted">
            Messaging &middot; to {offer.reply_options.recipient}
          </p>
          <div className="mt-1 space-y-2 rounded-lg border border-border bg-paper-2 p-3">
            {offer.reply_options.options.map((option) => (
              <ReplyOptionRow key={option.id} option={option} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
