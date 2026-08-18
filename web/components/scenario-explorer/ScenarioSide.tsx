"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { RoleBadge } from "@/components/ScenarioBrowser";
import { OfferCard } from "./OfferCard";
import { PolicyFields } from "./PolicyFields";
import type { ScenarioExplorerRecord } from "@/lib/scenarioExplorer";

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

export function ScenarioSide({ scenario }: { scenario: ScenarioExplorerRecord }) {
  const sandbox = scenario.environment.sandbox;
  const offers = sandbox?.offers ?? [];
  const requiredFields = sandbox?.checkout_required_fields ?? [];
  const optionalFields = sandbox?.checkout_optional_fields ?? [];

  return (
    <Card as="article" tone="raised" className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <RoleBadge role={scenario.pair_role} />
        <span className="font-mono text-caption uppercase tracking-wider text-muted">
          {scenario.scenario_id}
        </span>
      </div>

      <div>
        <p className="label">Situation</p>
        <p className="mt-1 text-ui leading-snug text-ink/90">
          {scenario.environment.situation}
        </p>
      </div>

      <div>
        <p className="label">Policy</p>
        <PolicyFields policy={scenario.payment_policy} />
      </div>

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
