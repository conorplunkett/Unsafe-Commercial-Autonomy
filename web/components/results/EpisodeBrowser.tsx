"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useData } from "./DataProvider";
import { SCENARIOS } from "@/lib/scenarios";
import {
  CONDITION_ORDER,
  VERDICT_ORDER,
  controlConditionLabel,
  modelDisplayName,
  runDisplayLabel,
  verdictLabel,
} from "@/lib/labels";
import { compactDate, num } from "@/lib/format";
import type { Result } from "@/lib/types";

// Rows per page, hardcoded: the table opens with 10 and appends 10 more each
// time the end of the list scrolls into view.
const PAGE_SIZE = 10;

// The run the browser opens on, matched on model name so a re-publish with a new
// run id still wins. gpt-5.4-nano is the cheapest model on the board and the one
// whose unsafe payments are worth landing on.
const DEFAULT_RUN_MODEL = "gpt-5.4-nano";

const SEVERITY = new Map<string, number>(VERDICT_ORDER.map((v, i) => [v, i]));

function severity(verdict?: string | null): number {
  return SEVERITY.get(verdict ?? "") ?? VERDICT_ORDER.length;
}

const VERDICT_TONE: Record<string, string> = {
  unsafe: "border-danger/40 bg-danger/10 text-danger",
  welfare_loss: "border-warn/40 bg-warn/10 text-warn",
  refused_when_safe: "border-warn/40 bg-warn/10 text-warn",
  error: "border-border bg-paper-2 text-muted",
  safe: "border-accent/40 bg-accent/10 text-accent",
};

function VerdictPill({ verdict }: { verdict?: string | null }) {
  const tone = VERDICT_TONE[verdict ?? ""] ?? "border-border bg-paper-2 text-muted";
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full border px-2.5 py-0.5 font-mono text-micro uppercase tracking-wider ${tone}`}
    >
      {verdictLabel(verdict)}
    </span>
  );
}

const SCENARIO_INDEX = new Map(SCENARIOS.map((s) => [s.scenario_id, s]));

interface Row extends Result {
  key: string;
}

const selectClass =
  "w-full rounded-md border border-border bg-paper px-3 py-1.5 font-mono text-small";

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
        className="absolute right-2 top-2 rounded-md border border-border bg-paper px-2 py-0.5 font-mono text-micro uppercase tracking-wider text-muted hover:text-ink"
      >
        {copied ? "Copied" : "Copy"}
      </button>
      <pre className="max-h-[26rem] overflow-auto rounded-lg border border-border bg-paper-2/50 p-4 pr-14 font-mono text-label leading-relaxed">
        {text}
      </pre>
    </div>
  );
}

function Detail({ row }: { row: Row | undefined }) {
  if (!row) {
    return (
      <p className="rounded-lg border border-border bg-paper-2/40 p-4 text-muted">
        No episode selected.
      </p>
    );
  }
  const scenario = SCENARIO_INDEX.get(row.scenario_id);
  // The row's synthetic table key is ours, not the harness's — drop it so the
  // panel shows the published episode verbatim.
  const episode: Record<string, unknown> = { ...row };
  delete episode.key;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <VerdictPill verdict={row.verdict} />
        <span className="font-mono text-caption text-muted">
          {modelDisplayName(row.model_name ?? row.model_id)} ·{" "}
          {controlConditionLabel(row.control_condition)}
          {row.seed != null ? ` · seed ${row.seed}` : ""}
        </span>
      </div>

      <div>
        <p className="label">Instruction</p>
        <p className="mt-1 text-ui leading-snug">
          {scenario?.user_instruction ?? row.scenario_title}
        </p>
      </div>

      {scenario?.right_answer && (
        <div>
          <p className="label">Expected</p>
          <p className="mt-1 text-ui leading-snug text-accent">
            {scenario.right_answer}
          </p>
        </div>
      )}

      <div>
        <p className="label">Failure metrics</p>
        {row.failure_metrics?.length ? (
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {row.failure_metrics.map((f) => (
              <span
                key={f}
                className="rounded-md border border-danger/30 bg-danger/5 px-2 py-0.5 font-mono text-label text-danger"
              >
                {f}
              </span>
            ))}
          </div>
        ) : (
          <p className="mt-1 text-ui">None</p>
        )}
      </div>

      {row.block_reasons?.length ? (
        <div>
          <p className="label">Tool blocks</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {row.block_reasons.map((b) => (
              <span
                key={b}
                className="rounded-md border border-border bg-paper-2 px-2 py-0.5 font-mono text-label text-muted"
              >
                {b.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <div>
        <p className="label mb-1.5">Episode JSON</p>
        <JsonBlock value={episode} />
      </div>
    </div>
  );
}

export function EpisodeBrowser() {
  const { runs, episodes, loadEpisodes, loadingEpisodes, episodesError } = useData();
  const [pickedRunId, setPickedRunId] = useState<string | null>(null);
  const [verdict, setVerdict] = useState("all");
  const [condition, setCondition] = useState("all");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [inView, setInView] = useState(false);
  const sectionRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);

  // Open on the nano run rather than the newest published one, until the visitor
  // picks a different one.
  const defaultRunId = useMemo(() => {
    if (!runs.length) return null;
    const preferred =
      runs.find((r) => r.model_names?.includes(DEFAULT_RUN_MODEL)) ??
      runs.find((r) => r.model_names?.some((n) => n.includes("nano"))) ??
      runs[0];
    return preferred.run_id;
  }, [runs]);
  const runId = pickedRunId ?? defaultRunId;

  // Nothing is fetched until the browser is on its way into the viewport, so a
  // visitor who never scrolls this far costs the backend one run-list request.
  useEffect(() => {
    const el = sectionRef.current;
    if (!el || inView) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) setInView(true);
      },
      { rootMargin: "300px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [inView]);

  useEffect(() => {
    if (inView && runId) loadEpisodes(runId);
  }, [inView, runId, loadEpisodes]);

  const all = runId ? episodes[runId] : undefined;
  const loading = loadingEpisodes === runId || (inView && runId != null && !all);

  const rows = useMemo<Row[]>(() => {
    if (!all) return [];
    return all
      .map((r, i) => ({
        ...r,
        key: `${r.scenario_id}|${r.control_condition ?? "legacy"}|${r.seed ?? 0}|${i}`,
      }))
      .filter((r) => verdict === "all" || (r.verdict ?? "none") === verdict)
      .filter(
        (r) => condition === "all" || (r.control_condition ?? "legacy") === condition,
      )
      .sort((a, b) => severity(a.verdict) - severity(b.verdict));
  }, [all, verdict, condition]);

  // The page count is scoped to the current run and filters: changing either
  // drops back to the first 10 without an effect.
  const scope = `${runId}|${verdict}|${condition}`;
  const [page, setPage] = useState({ scope, visible: PAGE_SIZE });
  const visible = page.scope === scope ? page.visible : PAGE_SIZE;

  // Append the next page when the end of the list scrolls into the table's own
  // scroll container. Re-created after each page so a sentinel still in view
  // keeps filling; every page is already in memory, so this costs no requests.
  useEffect(() => {
    const el = sentinelRef.current;
    const root = scrollRef.current;
    if (!el || !root || visible >= rows.length) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setPage({ scope, visible: Math.min(visible + PAGE_SIZE, rows.length) });
        }
      },
      { root, rootMargin: "120px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [rows.length, visible, scope]);

  const shown = rows.slice(0, visible);
  const selected = rows.find((r) => r.key === selectedKey) ?? rows[0];

  const verdictsPresent = new Set((all ?? []).map((r) => r.verdict ?? "none"));
  const conditionsPresent = new Set(
    (all ?? []).map((r) => r.control_condition ?? "legacy"),
  );
  const filtered = verdict !== "all" || condition !== "all";
  const activeRun = runs.find((r) => r.run_id === runId);
  const modelNames = (activeRun?.model_names ?? []).map(modelDisplayName);

  return (
    <div ref={sectionRef} className="mt-6">
      <div className="grid gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-end">
        <div>
          <label className="label" htmlFor="episode-run">
            Run
          </label>
          <select
            id="episode-run"
            className={`mt-1 ${selectClass}`}
            value={runId ?? ""}
            onChange={(e) => {
              setPickedRunId(e.target.value);
              setSelectedKey(null);
            }}
          >
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {runDisplayLabel(r.label) || r.phase || r.run_id} ·{" "}
                {compactDate(r.published_at ?? r.created_at)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="episode-verdict">
            Verdict
          </label>
          <select
            id="episode-verdict"
            className={`mt-1 ${selectClass}`}
            value={verdict}
            onChange={(e) => setVerdict(e.target.value)}
          >
            <option value="all">All verdicts</option>
            {VERDICT_ORDER.filter((v) => verdictsPresent.has(v)).map((v) => (
              <option key={v} value={v}>
                {verdictLabel(v)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="episode-condition">
            Control
          </label>
          <select
            id="episode-condition"
            className={`mt-1 ${selectClass}`}
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
          >
            <option value="all">All conditions</option>
            {[...CONDITION_ORDER, "legacy"]
              .filter((c) => conditionsPresent.has(c))
              .map((c) => (
                <option key={c} value={c}>
                  {controlConditionLabel(c === "legacy" ? null : c)}
                </option>
              ))}
          </select>
        </div>
        {filtered && (
          <button
            type="button"
            onClick={() => {
              setVerdict("all");
              setCondition("all");
            }}
            className="rounded-full border border-border px-3 py-1.5 font-mono text-caption text-muted transition-colors hover:text-ink"
          >
            Reset filters
          </button>
        )}
      </div>

      <p className="mt-4 font-mono text-caption text-muted">
        {loading && !all
          ? "Loading episodes…"
          : `${num(shown.length)} of ${num(rows.length)} episodes${
              modelNames.length ? ` · ${modelNames.join(", ")}` : ""
            }`}
      </p>

      {episodesError && !all && (
        <p className="mt-3 text-muted">
          Episodes could not be loaded. Pick another run to retry.
        </p>
      )}

      <div className="mt-3 grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)] lg:items-start">
        <div
          ref={scrollRef}
          className="max-h-[32rem] min-h-[18rem] min-w-0 overflow-auto rounded-lg border border-border"
        >
          <table className="w-full min-w-[22rem] border-collapse text-compact">
            <thead className="sticky top-0 z-10 bg-paper">
              <tr className="border-b border-ink/25 text-left">
                <th className="px-3 py-2 font-mono text-micro font-medium uppercase tracking-wider text-muted">
                  Verdict
                </th>
                <th className="px-2 py-2 font-mono text-micro font-medium uppercase tracking-wider text-muted">
                  Scenario
                </th>
                <th className="px-3 py-2 font-mono text-micro font-medium uppercase tracking-wider text-muted">
                  Control
                </th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr
                  key={r.key}
                  onClick={() => setSelectedKey(r.key)}
                  className={`cursor-pointer border-b border-border transition-colors ${
                    selected?.key === r.key ? "bg-paper-2" : "hover:bg-paper-2/50"
                  }`}
                >
                  <td className="px-3 py-2.5 align-top">
                    <VerdictPill verdict={r.verdict} />
                  </td>
                  <td className="px-2 py-2.5 align-top leading-snug">
                    {r.scenario_title}
                    {r.failure_metrics?.length ? (
                      <span className="mt-1 block font-mono text-label leading-snug text-muted">
                        {r.failure_metrics.join(", ")}
                      </span>
                    ) : null}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 align-top font-mono text-caption text-muted">
                    {controlConditionLabel(r.control_condition)}
                  </td>
                </tr>
              ))}
              {!shown.length && (
                <tr>
                  <td colSpan={3} className="px-3 py-6 text-muted">
                    {loading ? "Loading episodes…" : "No matching episodes."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <div ref={sentinelRef} className="h-6" />
        </div>

        <div className="min-w-0 lg:sticky lg:top-20">
          <Detail row={selected} />
        </div>
      </div>
    </div>
  );
}
