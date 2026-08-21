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

type Stage = "landing" | "system" | "task" | "toolkit";

const TOTAL_CALLS = CALLED_BY_STEP.length;
const FLASH_MS = 1800;

const VERDICT_TONE: Record<"danger" | "neutral", string> = {
  danger: "border-danger/40 bg-danger/10 text-danger",
  neutral: "border-border bg-paper-2 text-muted",
};

function ArrowRight() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-5 w-5 shrink-0"
      aria-hidden="true"
    >
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

function ContinueButton({
  onClick,
  children,
}: {
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="tap flex items-center gap-2 rounded-lg bg-accent px-5 text-ui text-paper transition-colors hover:bg-ink"
    >
      {children}
      <ArrowRight />
    </button>
  );
}

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
  const [stage, setStage] = useState<Stage>("landing");
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
    if (stage === "toolkit") {
      if (calledCount > 0) {
        setCalledCount((c) => c - 1);
      } else {
        setStage("task");
      }
      return;
    }
    if (stage === "task") {
      setStage("system");
      return;
    }
    if (stage === "system") {
      setStage("landing");
    }
  }

  function replay(nextCondition: ConditionId) {
    setCondition(nextCondition);
    setCalledCount(0);
    setStage("toolkit");
    setFlash(null);
  }

  if (stage === "landing") {
    return (
      <section className="mt-14">
        <ContinueButton onClick={() => setStage("system")}>
          Ok, what do I do?
        </ContinueButton>
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
          {stage === "system" && (
            <div className="mt-4">
              <ContinueButton onClick={() => setStage("task")}>
                What should I do?
              </ContinueButton>
            </div>
          )}
        </RevealStep>

        {(stage === "task" || stage === "toolkit") && (
          <RevealStep key={`task-${condition}`}>
            <p className="text-ui text-muted">Then you are given a task:</p>
            <p className="mt-1.5 text-ui">{USER_PROMPT}</p>
            {stage === "task" && (
              <div className="mt-4">
                <ContinueButton onClick={() => setStage("toolkit")}>
                  Ok, so what do I do with this task?
                </ContinueButton>
              </div>
            )}
          </RevealStep>
        )}

        {stage === "toolkit" &&
          CALLED_BY_STEP.slice(0, calledCount).map((name) => (
            <RevealStep key={`${condition}-${name}`}>{callResult(name, condition)}</RevealStep>
          ))}
      </div>

      {stage === "toolkit" && !done && (
        <div className="mt-8">
          <p className="text-ui text-muted">
            So you look at your toolkit. What can you do?
          </p>
          <Card as="ol" tone="bare" pad="none" className="mt-4 overflow-hidden">
            {TOOLS.map((tool) => {
              const toolDoneIndex = CALLED_BY_STEP.indexOf(tool.name);
              const toolDone = toolDoneIndex !== -1 && toolDoneIndex < calledCount;
              const isNext = tool.name === CALLED_BY_STEP[calledCount];
              return (
                <li key={tool.name}>
                  <button
                    type="button"
                    onClick={() => pickTool(tool.name)}
                    disabled={toolDone}
                    className={`tap flex w-full flex-col items-start border-l-4 px-3.5 py-3 text-left transition-colors disabled:cursor-default ${
                      toolDone
                        ? "border-l-transparent bg-accent/[0.06]"
                        : isNext
                          ? "border-l-accent bg-accent/10"
                          : "border-l-transparent bg-paper-2 hover:bg-paper"
                    }`}
                  >
                    <span
                      className={`font-mono text-small ${
                        toolDone || isNext ? "text-accent" : "text-muted"
                      }`}
                    >
                      {tool.name}
                    </span>
                    <span
                      className={`mt-0.5 text-caption leading-snug ${
                        isNext ? "text-ink/70" : "text-muted"
                      }`}
                    >
                      {tool.short}
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
            {flash || " "}
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
