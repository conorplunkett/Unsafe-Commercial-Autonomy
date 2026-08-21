"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
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

const TOTAL_CALLS = CALLED_BY_STEP.length;
const FLASH_MS = 1800;

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

function callResult(toolName: string, condition: ConditionId): ReactNode {
  const outcome = OUTCOMES[condition];
  switch (toolName) {
    case "search_offers":
      return (
        <>
          <p className="mb-1.5 font-mono text-small text-muted">
            {SEARCH_OFFERS_CALL}
          </p>
          <Block>{SEARCH_OFFERS_RESULT}</Block>
        </>
      );
    case "view_offer":
      return (
        <>
          <p className="mb-1.5 font-mono text-small text-muted">
            {VIEW_OFFER_CALL}
          </p>
          <Block>{VIEW_OFFER_RESULT}</Block>
        </>
      );
    case "pay":
      return (
        <>
          <p className="mb-1.5 font-mono text-small text-muted">{PAY_CALL}</p>
          <Block>{outcome.payResult}</Block>
        </>
      );
    case "finish":
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
  const [calledCount, setCalledCount] = useState(0);
  const [unlocked, setUnlocked] = useState(false);
  const [condition, setCondition] = useState<ConditionId>("no_policy");
  const [flash, setFlash] = useState<string | null>(null);
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (flashTimer.current) clearTimeout(flashTimer.current);
    },
    [],
  );

  function pickTool(name: string) {
    const expected = CALLED_BY_STEP[calledCount];
    if (flashTimer.current) clearTimeout(flashTimer.current);
    if (name !== expected) {
      setFlash("Woah, a bit early for that.");
      flashTimer.current = setTimeout(() => setFlash(null), FLASH_MS);
      return;
    }
    setFlash(null);
    const next = calledCount + 1;
    setCalledCount(next);
    if (next === TOTAL_CALLS) setUnlocked(true);
  }

  function goBack() {
    setFlash(null);
    if (calledCount > 0) {
      setCalledCount((c) => c - 1);
      return;
    }
    setStarted(false);
  }

  function replay(nextCondition: ConditionId) {
    setCondition(nextCondition);
    setCalledCount(0);
    setFlash(null);
  }

  if (!started) {
    return (
      <section className="mt-14">
        <button
          type="button"
          onClick={() => setStarted(true)}
          className="tap rounded-lg border border-ink px-5 text-ui transition-colors hover:bg-ink hover:text-paper"
        >
          Ok, what do I do?
        </button>
      </section>
    );
  }

  const outcome = OUTCOMES[condition];
  const done = calledCount === TOTAL_CALLS;

  return (
    <section className="mt-14 max-w-2xl">
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
                    onClick={() => replay(id)}
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

      <div className="space-y-5">
        <RevealStep key={`system-${condition}`}>
          <p className="text-ui text-muted">You receive this initial system prompt:</p>
          <div className="mt-1.5">
            <Block>{outcome.systemPrompt}</Block>
          </div>
        </RevealStep>

        <RevealStep key={`task-${condition}`}>
          <p className="text-ui text-muted">Then you are given a task:</p>
          <p className="mt-1.5 text-ui">{USER_PROMPT}</p>
        </RevealStep>

        {CALLED_BY_STEP.slice(0, calledCount).map((name) => (
          <RevealStep key={`${condition}-${name}`}>{callResult(name, condition)}</RevealStep>
        ))}
      </div>

      {!done && (
        <div className="mt-8">
          <p className="text-ui text-muted">
            So you look at your toolkit. What can you do?
          </p>
          <p className="label mb-2 mt-4">What would you pick?</p>
          <Card as="ol" tone="bare" pad="none" className="overflow-hidden">
            {TOOLS.map((tool) => {
              const toolDoneIndex = CALLED_BY_STEP.indexOf(tool.name);
              const toolDone = toolDoneIndex !== -1 && toolDoneIndex < calledCount;
              return (
                <li key={tool.name}>
                  <button
                    type="button"
                    onClick={() => pickTool(tool.name)}
                    disabled={toolDone}
                    className={`tap flex w-full flex-col items-start px-4 py-3 text-left transition-colors disabled:cursor-default ${
                      toolDone ? "bg-accent/[0.06]" : "bg-paper-2 hover:bg-paper"
                    }`}
                  >
                    <span
                      className={`font-mono text-small ${toolDone ? "text-accent" : "text-ink"}`}
                    >
                      {tool.name}
                    </span>
                    <span className="mt-0.5 text-caption leading-snug text-muted">
                      {tool.description}
                    </span>
                  </button>
                </li>
              );
            })}
          </Card>
          <p
            aria-live="polite"
            className={`mt-3 text-small text-muted transition-opacity duration-300 ${
              flash ? "opacity-100" : "opacity-0"
            }`}
          >
            {flash || " "}
          </p>
        </div>
      )}

      <div className="mt-6">
        <button
          type="button"
          onClick={goBack}
          className="tap rounded-lg border border-border px-4 text-small text-muted transition-colors hover:text-ink"
        >
          Back
        </button>
      </div>
    </section>
  );
}
