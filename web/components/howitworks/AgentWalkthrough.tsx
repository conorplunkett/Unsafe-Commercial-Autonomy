"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Card } from "@/components/ui/Card";
import { CONDITION_LABELS, CONDITION_DESCRIPTIONS } from "@/lib/labels";
import {
  CALLED_BY_STEP,
  CONDITIONS,
  OUTCOMES,
  PAY_CALL,
  SEARCH_OFFERS_CALL,
  SEARCH_OFFERS_RESULT,
  TOOLS,
  USER_PROMPT,
  VIEW_OFFER_CALL,
  VIEW_OFFER_RESULT,
  type ConditionId,
} from "./script";

const STEP_LABELS = [
  "System",
  "Task",
  "search_offers",
  "view_offer",
  "pay",
  "finish",
];
const LAST_STEP = STEP_LABELS.length - 1;

const VERDICT_TONE: Record<"danger" | "neutral", string> = {
  danger: "border-danger/40 bg-danger/10 text-danger",
  neutral: "border-border bg-paper-2 text-muted",
};

function RevealStep({ children }: { children: ReactNode }) {
  const [entered, setEntered] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setEntered(true));
    return () => cancelAnimationFrame(id);
  }, []);
  return (
    <div
      className={`transition-all duration-300 motion-reduce:transition-none ${
        entered ? "translate-y-0 opacity-100" : "translate-y-1 opacity-0"
      }`}
    >
      {children}
    </div>
  );
}

function Block({ children }: { children: ReactNode }) {
  return (
    <pre className="whitespace-pre-wrap rounded-lg border border-border bg-paper-2 p-4 font-mono text-caption leading-relaxed">
      {children}
    </pre>
  );
}

function stepContent(index: number, condition: ConditionId): ReactNode {
  const outcome = OUTCOMES[condition];
  switch (index) {
    case 0:
      return <Block>{outcome.systemPrompt}</Block>;
    case 1:
      return <p className="text-ui">{USER_PROMPT}</p>;
    case 2:
      return (
        <>
          <p className="mb-1.5 font-mono text-small text-muted">
            {SEARCH_OFFERS_CALL}
          </p>
          <Block>{SEARCH_OFFERS_RESULT}</Block>
        </>
      );
    case 3:
      return (
        <>
          <p className="mb-1.5 font-mono text-small text-muted">
            {VIEW_OFFER_CALL}
          </p>
          <Block>{VIEW_OFFER_RESULT}</Block>
        </>
      );
    case 4:
      return (
        <>
          <p className="mb-1.5 font-mono text-small text-muted">{PAY_CALL}</p>
          <Block>{outcome.payResult}</Block>
        </>
      );
    case 5:
      return (
        <>
          <p className="mb-1.5 font-mono text-small text-muted">
            {outcome.finishCall}
          </p>
          <Block>{outcome.finishResult}</Block>
          <div
            className={`mt-3 inline-block rounded-full border px-2.5 py-0.5 font-mono text-caption uppercase tracking-wider ${
              VERDICT_TONE[outcome.verdict.tone]
            }`}
          >
            {outcome.verdict.label}
          </div>
          <p className="mt-2 text-small text-muted">{outcome.verdict.caption}</p>
        </>
      );
    default:
      return null;
  }
}

export function AgentWalkthrough() {
  const [started, setStarted] = useState(false);
  const [unlocked, setUnlocked] = useState(false);
  const [condition, setCondition] = useState<ConditionId>("no_policy");
  const [step, setStep] = useState(0);

  const usedTools = new Set(CALLED_BY_STEP.slice(0, Math.max(0, step - 1)));
  const showTools = usedTools.size > 0;

  function selectCondition(next: ConditionId) {
    if (next === condition) return;
    setCondition(next);
    setStep(0);
  }

  function advance() {
    setStep((s) => {
      const next = Math.min(LAST_STEP, s + 1);
      if (next === LAST_STEP) setUnlocked(true);
      return next;
    });
  }

  if (!started) {
    return (
      <section className="mt-14">
        <button
          type="button"
          onClick={() => setStarted(true)}
          className="tap rounded-lg border border-ink px-5 text-ui transition-colors hover:bg-ink hover:text-paper"
        >
          Start the episode
        </button>
      </section>
    );
  }

  return (
    <section className="mt-14">
      {unlocked && (
        <div className="mb-8">
          <p className="label mb-3">Try a different policy</p>
          <Card as="ol" tone="bare" pad="none" className="overflow-hidden">
            {CONDITIONS.map((id, i) => {
              const selected = id === condition;
              return (
                <li key={id}>
                  <button
                    type="button"
                    onClick={() => selectCondition(id)}
                    aria-pressed={selected}
                    className={`tap flex w-full items-baseline gap-4 px-5 py-4 text-left transition-colors ${
                      selected ? "bg-accent/[0.06]" : "bg-paper-2 hover:bg-paper"
                    }`}
                  >
                    <span className="font-mono text-small text-accent">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span>
                      <p className="text-prose">{CONDITION_LABELS[id]}</p>
                      <p className="mt-0.5 text-small leading-snug text-muted">
                        {CONDITION_DESCRIPTIONS[id]}
                      </p>
                    </span>
                  </button>
                </li>
              );
            })}
          </Card>
        </div>
      )}

      <p className="label mb-3">Inside an episode</p>
      <div
        className={
          showTools
            ? "grid gap-8 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)] lg:items-start"
            : ""
        }
      >
        <div>
          <div aria-live="polite" className="space-y-5">
            {Array.from({ length: step + 1 }, (_, i) => i).map((i) => (
              <RevealStep key={`${condition}-${i}`}>
                <p className="label mb-1.5">{STEP_LABELS[i]}</p>
                {stepContent(i, condition)}
              </RevealStep>
            ))}
          </div>

          <div className="mt-6 flex items-center gap-3">
            <button
              type="button"
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0}
              className="tap rounded-lg border border-border px-4 text-small text-muted transition-colors hover:text-ink disabled:opacity-40"
            >
              Back
            </button>
            {step < LAST_STEP ? (
              <button
                type="button"
                onClick={advance}
                className="tap rounded-lg border border-ink px-4 text-small transition-colors hover:bg-ink hover:text-paper"
              >
                Next
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setStep(0)}
                className="tap rounded-lg border border-ink px-4 text-small transition-colors hover:bg-ink hover:text-paper"
              >
                Replay
              </button>
            )}
            <div className="ml-auto flex items-center gap-1.5" aria-hidden>
              {STEP_LABELS.map((label, i) => (
                <span
                  key={label}
                  className={`h-1.5 w-1.5 rounded-full ${
                    i <= step ? "bg-accent" : "bg-border"
                  }`}
                />
              ))}
            </div>
          </div>
        </div>

        {showTools && (
          <div className="lg:sticky lg:top-20">
            <p className="label mb-2">Tools called</p>
            <Card as="ol" tone="bare" pad="none" className="overflow-hidden">
              {TOOLS.filter((tool) => usedTools.has(tool.name)).map((tool) => (
                <li key={tool.name} className="bg-accent/[0.06] px-4 py-3">
                  <p className="font-mono text-small text-accent">{tool.name}</p>
                  <p className="mt-0.5 text-caption leading-snug text-muted">
                    {tool.description}
                  </p>
                </li>
              ))}
            </Card>
          </div>
        )}
      </div>
    </section>
  );
}
