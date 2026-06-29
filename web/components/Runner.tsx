"use client";

import { useMemo, useState } from "react";
import { SCENARIOS, type ScenarioCard } from "@/lib/scenarios";
import {
  CATEGORY_ORDER,
  CATEGORY_LABELS,
  CONDITION_LABELS,
  CONDITION_DESCRIPTIONS,
  categoryLabel,
} from "@/lib/labels";
import { pct } from "@/lib/format";

// The three control conditions the hosted runner supports (the same ones the
// scoring path enforces), weakest to strongest.
const RUN_CONDITIONS = ["no_policy", "prompt_policy", "tool_constraints"] as const;

const PROVIDERS = [
  { id: "openai", label: "OpenAI", defaultModel: "gpt-4o-mini" },
  { id: "anthropic", label: "Anthropic", defaultModel: "claude-3-5-haiku-latest" },
] as const;

const MODEL_SUGGESTIONS: Record<string, string[]> = {
  openai: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "o4-mini"],
  anthropic: [
    "claude-3-5-haiku-latest",
    "claude-3-5-sonnet-latest",
    "claude-sonnet-4-5",
  ],
};

type Provider = (typeof PROVIDERS)[number]["id"];

// The harness returns full EvaluationResult dicts; we read the subset we render.
interface CellResult {
  scenario_id: string;
  control_condition: string;
  verdict: "safe" | "unsafe" | "false_refusal" | "welfare_loss";
  unsafe_payment: boolean;
  false_refusal: boolean;
  safe_to_act: boolean | null;
  user_welfare_score: number;
  model_name?: string | null;
  block_reasons?: string[];
  error?: string | null;
  action?: {
    action_type?: string;
    amount?: number | null;
    rationale?: string | null;
  } | null;
}

const VERDICT_META: Record<
  CellResult["verdict"],
  { label: string; cls: string }
> = {
  safe: {
    label: "Safe",
    cls: "border-accent/40 bg-accent/10 text-accent",
  },
  unsafe: {
    label: "Unsafe payment",
    cls: "border-danger/40 bg-danger/10 text-danger",
  },
  false_refusal: {
    label: "False refusal",
    cls: "border-warn/40 bg-warn/10 text-warn",
  },
  welfare_loss: {
    label: "Welfare loss",
    cls: "border-warn/40 bg-warn/10 text-warn",
  },
};

function VerdictBadge({ v }: { v: CellResult["verdict"] }) {
  const m = VERDICT_META[v];
  return (
    <span
      className={`rounded-full border px-2.5 py-0.5 font-mono text-[0.65rem] uppercase tracking-wider ${m.cls}`}
    >
      {m.label}
    </span>
  );
}

export function Runner() {
  const [provider, setProvider] = useState<Provider>("openai");
  const [model, setModel] = useState<string>(PROVIDERS[0].defaultModel);
  const [apiKey, setApiKey] = useState("");
  const [category, setCategory] = useState<string>("all");
  const [scenarioId, setScenarioId] = useState<string>("random");
  const [conditions, setConditions] = useState<Set<string>>(
    new Set(RUN_CONDITIONS),
  );
  const [temperature, setTemperature] = useState<string>("0.7");
  const [reasoningEffort, setReasoningEffort] = useState<string>("");

  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number }>({
    done: 0,
    total: 0,
  });
  const [ranScenario, setRanScenario] = useState<ScenarioCard | null>(null);
  const [results, setResults] = useState<CellResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const scenarioPool = useMemo(
    () =>
      SCENARIOS.filter((s) => category === "all" || s.category === category),
    [category],
  );

  function pickProvider(p: Provider) {
    setProvider(p);
    const def = PROVIDERS.find((x) => x.id === p)?.defaultModel ?? "";
    setModel(def);
  }

  function toggleCondition(c: string) {
    setConditions((prev) => {
      const next = new Set(prev);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });
  }

  const selectedConditions = RUN_CONDITIONS.filter((c) => conditions.has(c));
  const canRun =
    !running &&
    apiKey.trim().length > 0 &&
    model.trim().length > 0 &&
    selectedConditions.length > 0 &&
    scenarioPool.length > 0;

  async function run() {
    setError(null);
    setResults([]);
    setProgress({ done: 0, total: selectedConditions.length });

    // Resolve the scenario (one at a time; "random" draws from the filtered pool).
    const chosen =
      scenarioId === "random"
        ? scenarioPool[Math.floor(Math.random() * scenarioPool.length)]
        : SCENARIOS.find((s) => s.scenario_id === scenarioId);
    if (!chosen) {
      setError("Pick a scenario to run.");
      return;
    }
    setRanScenario(chosen);
    setRunning(true);

    const acc: CellResult[] = [];
    try {
      for (const condition of selectedConditions) {
        const res = await fetch("/api/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            provider,
            model: model.trim(),
            apiKey: apiKey.trim(),
            scenarioId: chosen.scenario_id,
            condition,
            temperature: Number(temperature),
            reasoningEffort: reasoningEffort || undefined,
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          setError(data?.error || `Request failed (${res.status}).`);
          break;
        }
        const cell = data.result as CellResult;
        if (cell?.error) {
          // Provider-level failure (e.g. bad key/model) — fails every cell, so stop.
          setError(cell.error);
          break;
        }
        acc.push(cell);
        setResults([...acc]);
        setProgress((p) => ({ ...p, done: p.done + 1 }));
      }
    } catch (e) {
      setError(`Network error: ${(e as Error).message}`);
    } finally {
      setRunning(false);
    }
  }

  const label = "block font-mono text-[0.7rem] uppercase tracking-wider text-muted";
  const field =
    "mt-1.5 w-full rounded-md border border-border bg-paper px-3 py-2 font-mono text-sm text-ink outline-none focus:border-accent";
  const chip = "rounded-full border px-3 py-1 font-mono text-xs transition-colors";
  const on = "border-accent bg-accent/10 text-accent";
  const off = "border-border text-muted hover:text-ink";

  return (
    <div className="mt-8">
      {/* Controls */}
      <div className="rounded-2xl border border-border bg-paper-2/40 p-5 sm:p-6">
        <div className="grid gap-5 sm:grid-cols-2">
          {/* Provider */}
          <div>
            <span className={label}>Provider</span>
            <div className="mt-1.5 flex gap-2">
              {PROVIDERS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => pickProvider(p.id)}
                  className={`${chip} ${provider === p.id ? on : off}`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Model */}
          <div>
            <label className={label} htmlFor="rn-model">
              Model
            </label>
            <input
              id="rn-model"
              className={field}
              value={model}
              list="rn-model-suggestions"
              spellCheck={false}
              autoComplete="off"
              onChange={(e) => setModel(e.target.value)}
              placeholder={PROVIDERS.find((p) => p.id === provider)?.defaultModel}
            />
            <datalist id="rn-model-suggestions">
              {(MODEL_SUGGESTIONS[provider] ?? []).map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>
          </div>

          {/* API key */}
          <div className="sm:col-span-2">
            <label className={label} htmlFor="rn-key">
              Your {provider === "openai" ? "OpenAI" : "Anthropic"} API key
            </label>
            <input
              id="rn-key"
              className={field}
              type="password"
              value={apiKey}
              spellCheck={false}
              autoComplete="off"
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={provider === "openai" ? "sk-..." : "sk-ant-..."}
            />
            <p className="mt-1.5 text-xs text-muted">
              Sent once to score this run, then discarded — never stored or
              logged. You pay your provider for the calls. Or run the whole
              benchmark locally from the repo.
            </p>
          </div>

          {/* Category + scenario */}
          <div>
            <label className={label} htmlFor="rn-category">
              Category
            </label>
            <select
              id="rn-category"
              className={field}
              value={category}
              onChange={(e) => {
                setCategory(e.target.value);
                setScenarioId("random");
              }}
            >
              <option value="all">All categories</option>
              {CATEGORY_ORDER.map((c) => (
                <option key={c} value={c}>
                  {CATEGORY_LABELS[c]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={label} htmlFor="rn-scenario">
              Scenario
            </label>
            <select
              id="rn-scenario"
              className={field}
              value={scenarioId}
              onChange={(e) => setScenarioId(e.target.value)}
            >
              <option value="random">🎲 Random in selection</option>
              {scenarioPool.map((s) => (
                <option key={s.scenario_id} value={s.scenario_id}>
                  {s.title}
                </option>
              ))}
            </select>
          </div>

          {/* Conditions */}
          <div className="sm:col-span-2">
            <span className={label}>Control conditions</span>
            <div className="mt-2 flex flex-wrap gap-2">
              {RUN_CONDITIONS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => toggleCondition(c)}
                  title={CONDITION_DESCRIPTIONS[c]}
                  className={`${chip} ${conditions.has(c) ? on : off}`}
                >
                  {CONDITION_LABELS[c]}
                </button>
              ))}
            </div>
            <p className="mt-1.5 text-xs text-muted">
              Each selected condition is one model call. The scenario runs once
              per condition (1 seed).
            </p>
          </div>

          {/* Advanced */}
          <div>
            <label className={label} htmlFor="rn-temp">
              Temperature
            </label>
            <input
              id="rn-temp"
              className={field}
              type="number"
              min="0"
              max="2"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(e.target.value)}
            />
          </div>
          <div>
            <label className={label} htmlFor="rn-effort">
              Reasoning effort
            </label>
            <select
              id="rn-effort"
              className={field}
              value={reasoningEffort}
              onChange={(e) => setReasoningEffort(e.target.value)}
            >
              <option value="">Default</option>
              <option value="minimal">Minimal</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={run}
            disabled={!canRun}
            className="rounded-md bg-ink px-5 py-2 font-serif text-[1.05rem] text-paper transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-40"
          >
            {running ? "Running…" : "Run benchmark"}
          </button>
          {running && (
            <span className="font-mono text-xs text-muted">
              {progress.done}/{progress.total} conditions
            </span>
          )}
        </div>

        {/* Progress bar — fills as each condition completes */}
        {(running || (progress.total > 0 && progress.done > 0)) && (
          <div className="mt-4">
            <div className="flex items-center justify-between font-mono text-[0.7rem] text-muted">
              <span>
                {running
                  ? `Running ${selectedConditions[progress.done] ? CONDITION_LABELS[selectedConditions[progress.done]] : "…"}`
                  : "Done"}
              </span>
              <span>
                {progress.total > 0
                  ? `${Math.round((progress.done / progress.total) * 100)}%`
                  : "0%"}
              </span>
            </div>
            <div
              className="mt-1.5 h-2 w-full overflow-hidden rounded-full border border-border bg-paper"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={progress.total}
              aria-valuenow={progress.done}
            >
              <div
                className={`h-full rounded-full bg-accent transition-all duration-500 ease-out ${running ? "animate-pulse" : ""}`}
                style={{
                  width:
                    progress.total > 0
                      ? `${(progress.done / progress.total) * 100}%`
                      : "0%",
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mt-5 rounded-xl border border-danger/40 bg-danger/10 p-4 text-sm text-danger">
          {error}
        </div>
      )}

      {/* Scenario context */}
      {ranScenario && (
        <div className="mt-6 rounded-xl border border-border bg-paper-2/40 p-5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[0.65rem] uppercase tracking-wider text-muted">
              {categoryLabel(ranScenario.category)} · {ranScenario.pair_role} ·{" "}
              {ranScenario.stakes} stakes
            </span>
          </div>
          <p className="mt-3 text-[1.05rem] leading-snug text-ink/90">
            {ranScenario.situation}
          </p>
          <p className="mt-3 border-t border-border pt-3 text-sm">
            <span className="text-muted">Safe answer: </span>
            <span className="text-accent">{ranScenario.right_answer ?? "—"}</span>
            {ranScenario.failure_tested && (
              <span className="ml-3 font-mono text-[0.7rem] text-muted">
                tests: {ranScenario.failure_tested}
              </span>
            )}
          </p>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="mt-6 space-y-3">
          {results.map((r) => {
            const correct = !r.unsafe_payment && !r.false_refusal;
            return (
              <div
                key={r.control_condition}
                className="rounded-xl border border-border bg-paper p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-serif text-lg">
                    {CONDITION_LABELS[r.control_condition] ?? r.control_condition}
                  </span>
                  <div className="flex items-center gap-2">
                    <VerdictBadge v={r.verdict} />
                    <span
                      className={`font-mono text-[0.7rem] ${correct ? "text-accent" : "text-danger"}`}
                    >
                      {correct ? "✓ matched" : "✗ failed"}
                    </span>
                  </div>
                </div>
                {r.action && (
                  <p className="mt-2 font-mono text-xs text-muted">
                    action: {r.action.action_type ?? "—"}
                    {r.action.amount != null && ` · $${r.action.amount}`}
                  </p>
                )}
                {r.action?.rationale && (
                  <p className="mt-2 text-sm leading-snug text-ink/80">
                    “{r.action.rationale}”
                  </p>
                )}
                {r.block_reasons && r.block_reasons.length > 0 && (
                  <p className="mt-2 font-mono text-[0.7rem] text-warn">
                    blocked by tools: {r.block_reasons.join(", ")}
                  </p>
                )}
              </div>
            );
          })}

          {results.length > 1 && (
            <p className="pt-1 font-mono text-xs text-muted">
              {results.filter((r) => !r.unsafe_payment && !r.false_refusal).length}
              /{results.length} conditions handled correctly
              {(() => {
                const welfare =
                  results.reduce((s, r) => s + (r.user_welfare_score ?? 0), 0) /
                  results.length;
                return ` · mean welfare ${pct(welfare)}`;
              })()}
            </p>
          )}
        </div>
      )}

      {!running && !error && results.length === 0 && (
        <p className="mt-6 font-mono text-xs text-muted">
          Pick a model, paste your key, choose a scenario, and run. Results
          appear here as each condition completes.
        </p>
      )}
    </div>
  );
}
