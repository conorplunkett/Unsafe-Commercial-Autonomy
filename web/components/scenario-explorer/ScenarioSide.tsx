"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { RoleBadge } from "@/components/ScenarioBrowser";
import { OfferCard } from "./OfferCard";
import { PolicyFields } from "./PolicyFields";
import { compactDate } from "@/lib/format";
import type { ScenarioExplorerRecord, ScenarioReview } from "@/lib/scenarioExplorer";

// Local, not shared: this codebase copies small display patterns per feature
// rather than promoting a one-off to a shared component (see RoleBadge/VerdictPill
// precedent). Mirrors EpisodeBrowser.tsx's own JsonBlock exactly.
function JsonBlock({ value }: { value: unknown }) {
  const text = JSON.stringify(value, null, 2);
  const [copied, setCopied] = useState(false);
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          navigator.clipboard?.writeText(text).then(
            () => {
              setCopied(true);
              setTimeout(() => setCopied(false), 1200);
            },
            () => undefined,
          );
        }}
        className="tap absolute right-2 top-2 rounded-lg border border-border bg-paper px-2 py-0.5 font-mono text-caption uppercase tracking-wider text-muted hover:text-ink"
      >
        {copied ? "Copied" : "Copy"}
      </button>
      <pre className="max-h-[26rem] overflow-auto rounded-lg border border-border bg-paper-2 p-4 pr-14 font-mono text-caption leading-relaxed">
        {text}
      </pre>
    </div>
  );
}

function ReviewToggle({
  reviewed,
  reviewedAt,
  onToggle,
}: {
  reviewed: boolean;
  reviewedAt: string | null;
  onToggle: (next: boolean) => void;
}) {
  return (
    <span className="ml-auto flex items-center gap-2">
      {reviewed && reviewedAt && (
        <span className="font-mono text-caption text-muted">
          {compactDate(reviewedAt)}
        </span>
      )}
      <button
        type="button"
        onClick={() => onToggle(!reviewed)}
        className={`tap rounded-full border px-2.5 py-0.5 font-mono text-caption uppercase tracking-wider transition-colors ${
          reviewed
            ? "border-accent/40 bg-accent/10 text-accent"
            : "border-border text-muted hover:text-ink"
        }`}
      >
        {reviewed ? "Reviewed" : "Mark reviewed"}
      </button>
    </span>
  );
}

export function ScenarioSide({
  scenario,
  review,
  onToggleReview,
}: {
  scenario: ScenarioExplorerRecord;
  review?: ScenarioReview;
  onToggleReview?: (next: boolean) => void;
}) {
  const sandbox = scenario.environment.sandbox;
  const offers = sandbox?.offers ?? [];
  const requiredFields = sandbox?.checkout_required_fields ?? [];
  const optionalFields = sandbox?.checkout_optional_fields ?? [];
  const redirects = Object.entries(sandbox?.page_url_redirects ?? {});
  const capabilities = Object.entries(sandbox?.capabilities ?? {});

  return (
    <Card as="article" tone="raised" className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <RoleBadge role={scenario.pair_role} />
        <span className="font-mono text-caption uppercase tracking-wider text-muted">
          {scenario.scenario_id}
        </span>
        {onToggleReview && (
          <ReviewToggle
            reviewed={review?.reviewed ?? false}
            reviewedAt={review?.reviewed_at ?? null}
            onToggle={onToggleReview}
          />
        )}
      </div>

      <p className="text-h4 leading-snug text-ink">{scenario.title}</p>

      <div>
        <p className="label">Instruction</p>
        <p className="mt-1 text-ui leading-snug text-ink/90">
          {scenario.user_instruction}
        </p>
      </div>

      <div>
        <p className="label">Situation</p>
        <p className="mt-1 text-ui leading-snug text-ink/90">
          {scenario.environment.situation}
        </p>
      </div>

      <div>
        <p
          className="label"
          title="What the agent should do -- withheld from the agent, used to grade its response"
        >
          Hidden preference
        </p>
        <p className="mt-1 text-ui leading-snug text-ink/90">
          {scenario.hidden_preference}
        </p>
      </div>

      {sandbox?.ambient_context != null && (
        <div>
          <p className="label">Ambient context</p>
          <p className="mt-1 text-ui leading-snug text-ink/90">
            {sandbox.ambient_context}
          </p>
        </div>
      )}

      <div>
        <p className="label">Policy</p>
        <PolicyFields policy={scenario.payment_policy} />
      </div>

      <div>
        <p
          className="label"
          title="Whether the agent may act on its own here, or must ask/refuse"
        >
          Safe behavior
        </p>
        <p className="mt-1 text-small">
          {scenario.expected_safe_behavior.summary}
          <span className="text-muted">
            {" "}
            · Autonomous action:{" "}
            {scenario.expected_safe_behavior.safe_autonomous_allowed ? "Allowed" : "Not allowed"}
          </span>
        </p>
      </div>

      {capabilities.length > 0 && (
        <div>
          <p className="label">Capabilities</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {capabilities.map(([name, enabled]) => (
              <span
                key={name}
                className={`rounded-lg border px-2 py-0.5 font-mono text-caption ${
                  enabled
                    ? "border-border bg-paper-2 text-ink/80"
                    : "border-border text-muted line-through"
                }`}
              >
                {name.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {offers.length > 0 && (
        <div>
          <p className="label">Offers</p>
          <div className="mt-2 space-y-3">
            {offers.map((offer, i) => (
              <OfferCard key={offer.offer_id} offer={offer} index={i} total={offers.length} />
            ))}
          </div>
        </div>
      )}

      {sandbox?.free_source && (
        <div>
          <p
            className="label"
            title="A free, current source claimed to substitute for a paid item"
          >
            Free source
          </p>
          <p className="mt-1 text-small">
            {sandbox.free_source.name}
            <span className="text-muted">
              {" "}
              · {sandbox.free_source.current ? "Current" : "Not current"}
            </span>
          </p>
        </div>
      )}

      {redirects.length > 0 && (
        <div>
          <p className="label">Redirects</p>
          <ol className="mt-2 space-y-2 rounded-lg border border-border bg-paper-2 p-3 font-mono text-caption">
            {redirects.map(([from, to]) => (
              <li key={from} className="break-all">
                <span className="text-muted">{from}</span>
                <span className="mx-2 text-muted">→</span>
                <span>{to}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {(requiredFields.length > 0 || optionalFields.length > 0) && (
        <div>
          <p className="label">Checkout fields</p>
          <p className="mt-1 text-small">
            {requiredFields.length > 0 && (
              <>
                <span className="text-muted">Required: </span>
                {requiredFields.join(", ")}
              </>
            )}
            {requiredFields.length > 0 && optionalFields.length > 0 && " · "}
            {optionalFields.length > 0 && (
              <>
                <span className="text-muted">Optional: </span>
                {optionalFields.join(", ")}
              </>
            )}
          </p>
        </div>
      )}

      {!!sandbox?.unsafe_disclosure?.length && (
        <div>
          <p
            className="label"
            title="Fields that would be disclosed here but aren't required for this checkout"
          >
            Unsafe disclosure
          </p>
          <p className="mt-1 text-small text-danger">
            {sandbox.unsafe_disclosure.join(", ")}
          </p>
        </div>
      )}

      {sandbox?.prompt_injection != null && (
        <div>
          <p
            className="label"
            title="Adversarial instruction embedded in merchant-page text, testing whether the agent follows it over the user's policy"
          >
            Prompt injection
          </p>
          <p className="mt-1 text-small text-danger">
            {typeof sandbox.prompt_injection === "string"
              ? sandbox.prompt_injection
              : JSON.stringify(sandbox.prompt_injection)}
          </p>
        </div>
      )}

      <p className="font-mono text-caption text-muted">
        Tests: {scenario.unsafe_behavior}
      </p>

      {scenario.semantic_only && (
        <span
          title="Correct answer is a human-preference judgment call, not a structured-rule violation -- graded by the preference survey"
          className="inline-block w-fit rounded-full border border-warn/40 bg-warn/10 px-2.5 py-0.5 font-mono text-caption uppercase tracking-wider text-warn"
        >
          Semantic only
        </span>
      )}

      <div>
        <p className="label mb-1.5">Full record</p>
        <JsonBlock value={scenario} />
      </div>
    </Card>
  );
}
