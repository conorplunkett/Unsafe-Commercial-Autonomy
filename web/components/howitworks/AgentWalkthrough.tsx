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
const FADE_MS = 200;

const VERDICT_TONE: Record<"danger" | "neutral", string> = {
  danger: "border-danger/40 bg-danger/10 text-danger",
  neutral: "border-border bg-paper-2 text-muted",
};

// A premature click reacts to what was actually clicked, not a generic nudge.
const TOO_EARLY: Record<string, string> = {
  view_offer: "Ok, which one? Let's search them first.",
  pay: "Pay for what? You haven't checked the price.",
  request_approval: "What are we requesting approval for?",
  finish: "You sure? You didn't do anything.",
};

function headlineFor(stage: Stage, done: boolean): string {
  if (stage === "landing") {
    return "Imagine you are an agent with access to your human’s credit card.";
  }
  if (stage === "system") return "Your system prompt";
  if (stage === "task") return "Your task";
  if (done) return "Your outcome";
  return "You see your toolkit.";
}

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

// capped=true (default) scrolls a long block inside itself instead of
// stretching the screen -- used for tool-call JSON. The system prompt reads
// in full instead: capped=false.
function Block({
  children,
  capped = true,
}: {
  children: ReactNode;
  capped?: boolean;
}) {
  return (
    <pre
      className={`whitespace-pre-wrap rounded-lg border border-border bg-paper-2 p-4 font-mono text-caption leading-relaxed ${
        capped ? "max-h-56 overflow-y-auto" : ""
      }`}
    >
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
  const [visible, setVisible] = useState(true);
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fadeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (flashTimer.current) clearTimeout(flashTimer.current);
      if (fadeTimer.current) clearTimeout(fadeTimer.current);
    },
    [],
  );

  // Every screen change fades the current screen out, swaps its content,
  // then fades the new one in -- a real transition, not just a fade-in of
  // whatever gets appended.
  function transition(update: () => void) {
    setVisible(false);
    if (fadeTimer.current) clearTimeout(fadeTimer.current);
    fadeTimer.current = setTimeout(() => {
      update();
      setVisible(true);
    }, FADE_MS);
  }

  function pickTool(name: string) {
    const expected = CALLED_BY_STEP[calledCount];
    if (name !== expected) {
      if (flashTimer.current) clearTimeout(flashTimer.current);
      setFlash(TOO_EARLY[name] ?? "Woah, a bit early for that.");
      flashTimer.current = setTimeout(() => setFlash(null), FLASH_MS);
      return;
    }
    setFlash(null);
    transition(() => {
      const next = calledCount + 1;
      setCalledCount(next);
      if (next === TOTAL_CALLS) setUnlocked(true);
    });
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

  const outcome = OUTCOMES[condition];
  const done = calledCount === TOTAL_CALLS;
  const fadeClass = `transition-opacity duration-200 motion-reduce:transition-none ${
    visible ? "opacity-100" : "opacity-0"
  }`;

  return (
    <section className="max-w-2xl">
      {unlocked && stage !== "landing" && (
        <div className="mb-6">
          <p className="label mb-3">Try a different policy</p>
          <Card as="ol" tone="bare" pad="none" className="overflow-hidden">
            {CONDITIONS.map((id, i) => {
              const selected = id === condition;
              return (
                <li key={id}>
                  <button
                    type="button"
                    onClick={() => transition(() => replay(id))}
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

      <div className={fadeClass}>
        <h1 className="text-h1 tracking-tight">{headlineFor(stage, done)}</h1>

        {stage === "landing" && (
          <div className="mt-8">
            <ContinueButton onClick={() => transition(() => setStage("system"))}>
              Ok, what do I do?
            </ContinueButton>
          </div>
        )}

        {stage === "system" && (
          <Card tone="raised" className="mt-6">
            <Block capped={false}>{outcome.systemPrompt}</Block>
            <div className="mt-4">
              <ContinueButton onClick={() => transition(() => setStage("task"))}>
                What should I do?
              </ContinueButton>
            </div>
          </Card>
        )}

        {stage === "task" && (
          <Card tone="raised" className="mt-6">
            <p className="text-ui">{USER_PROMPT}</p>
            <div className="mt-4">
              <ContinueButton onClick={() => transition(() => setStage("toolkit"))}>
                What now?
              </ContinueButton>
            </div>
          </Card>
        )}

        {stage === "toolkit" && done && (
          <Card tone="raised" className="mt-6">
            {callResult("finish", condition)}
          </Card>
        )}

        {stage === "toolkit" && !done && (
          <Card tone="raised" className="mt-6">
            {calledCount > 0 && (
              <div className="mb-4">{callResult(CALLED_BY_STEP[calledCount - 1], condition)}</div>
            )}
            <Card as="ol" tone="bare" pad="none" className="overflow-hidden">
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
          </Card>
        )}
      </div>

      {stage !== "landing" && (
        <div className="mt-6">
          <button
            type="button"
            onClick={() => transition(goBack)}
            className="tap text-small text-muted/60 transition-colors hover:text-muted"
          >
            Back
          </button>
        </div>
      )}
    </section>
  );
}
