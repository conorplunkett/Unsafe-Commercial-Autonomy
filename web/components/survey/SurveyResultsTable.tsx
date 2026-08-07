"use client";

import { useMemo, useState } from "react";
import type { SurveyQuestion } from "@/lib/surveyResults";
import { Card } from "@/components/ui/Card";

const VOTE_LABELS: Record<string, string> = {
  buy: "buy",
  buy_compliant_alternative: "buy compliant alternative",
  use_free_source: "use free source",
  ask: "ask",
  refuse: "refuse",
};

function pct1(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

function voteLabel(vote: string): string {
  return VOTE_LABELS[vote] ?? vote.replaceAll("_", " ");
}

type SortKey = "item" | "role" | "vote" | "agreement" | "status";
type SortDir = "asc" | "desc";
type RoleFilter = "all" | "trap" | "lookalike";
type StatusFilter = "all" | "locked" | "provisional";

// Locked items sort ahead of provisional when ascending.
const STATUS_RANK: Record<string, number> = { locked: 0, provisional: 1 };

function compare(a: SurveyQuestion, b: SurveyQuestion, key: SortKey): number {
  switch (key) {
    case "item":
      return a.short.localeCompare(b.short);
    case "role":
      return a.role.localeCompare(b.role);
    case "vote":
      return voteLabel(a.modal_vote).localeCompare(voteLabel(b.modal_vote));
    case "agreement":
      return a.agreement - b.agreement;
    case "status":
      return (
        (STATUS_RANK[a.locked ? "locked" : "provisional"] ?? 0) -
        (STATUS_RANK[b.locked ? "locked" : "provisional"] ?? 0)
      );
  }
}

const HEAD_CLASS =
  "px-4 py-2.5 font-mono text-caption uppercase tracking-[0.14em] text-muted";

function SortHeader({
  label,
  colKey,
  sortKey,
  sortDir,
  onSort,
  align = "left",
}: {
  label: string;
  colKey: SortKey;
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (key: SortKey) => void;
  align?: "left" | "right";
}) {
  const active = sortKey === colKey;
  return (
    <th
      className={HEAD_CLASS}
      aria-sort={
        active ? (sortDir === "asc" ? "ascending" : "descending") : "none"
      }
    >
      <button
        type="button"
        onClick={() => onSort(colKey)}
        className={`tap flex w-full items-center gap-1 uppercase tracking-[0.14em] transition-colors hover:text-ink ${
          align === "right" ? "justify-end" : ""
        } ${active ? "text-ink" : ""}`}
      >
        {label}
        <span aria-hidden className={active ? "opacity-100" : "opacity-25"}>
          {active ? (sortDir === "asc" ? "▲" : "▼") : "▲"}
        </span>
      </button>
    </th>
  );
}

function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="label">{label}</span>
      <div className="inline-flex rounded-lg border border-border bg-paper p-0.5">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`tap rounded-lg px-3 py-1 font-mono text-caption transition-colors ${
              value === opt.value
                ? "bg-accent/10 text-accent"
                : "text-muted hover:text-ink"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function SurveyResultsTable({
  questions,
}: {
  questions: SurveyQuestion[];
}) {
  const [role, setRole] = useState<RoleFilter>("all");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [vote, setVote] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("item");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const voteOptions = useMemo(() => {
    const votes = Array.from(new Set(questions.map((q) => q.modal_vote)));
    votes.sort((a, b) => voteLabel(a).localeCompare(voteLabel(b)));
    return votes;
  }, [questions]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = questions.filter((item) => {
      if (role !== "all" && item.role !== role) return false;
      if (status === "locked" && !item.locked) return false;
      if (status === "provisional" && item.locked) return false;
      if (vote !== "all" && item.modal_vote !== vote) return false;
      if (
        q &&
        !item.short.toLowerCase().includes(q) &&
        !item.text.toLowerCase().includes(q)
      )
        return false;
      return true;
    });
    const dir = sortDir === "asc" ? 1 : -1;
    return filtered.sort((a, b) => {
      const primary = compare(a, b, sortKey) * dir;
      return primary !== 0 ? primary : a.short.localeCompare(b.short);
    });
  }, [questions, role, status, vote, query, sortKey, sortDir]);

  function onSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      // Percentages and status read most useful high-to-low first.
      setSortDir(key === "agreement" || key === "status" ? "desc" : "asc");
    }
  }

  const filtered =
    role !== "all" || status !== "all" || vote !== "all" || query.trim() !== "";

  function reset() {
    setRole("all");
    setStatus("all");
    setVote("all");
    setQuery("");
  }

  return (
    <div className="mt-6">
      <div className="flex flex-wrap items-end gap-x-6 gap-y-4">
        <Segmented
          label="Role"
          value={role}
          onChange={setRole}
          options={[
            { value: "all", label: "all" },
            { value: "trap", label: "trap" },
            { value: "lookalike", label: "lookalike" },
          ]}
        />
        <Segmented
          label="Status"
          value={status}
          onChange={setStatus}
          options={[
            { value: "all", label: "all" },
            { value: "locked", label: "locked" },
            { value: "provisional", label: "provisional" },
          ]}
        />
        <div className="flex flex-col gap-1.5">
          <label htmlFor="vote-filter" className="label">
            Modal vote
          </label>
          <select
            id="vote-filter"
            value={vote}
            onChange={(e) => setVote(e.target.value)}
            className="tap rounded-lg border border-border bg-paper px-3 py-1.5 font-mono text-caption text-ink"
          >
            <option value="all">all votes</option>
            {voteOptions.map((v) => (
              <option key={v} value={v}>
                {voteLabel(v)}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-1 flex-col gap-1.5">
          <label htmlFor="item-search" className="label">
            Search
          </label>
          <input
            id="item-search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="item or wording"
            className="tap min-w-[10rem] rounded-lg border border-border bg-paper px-3 py-1.5 text-small text-ink placeholder:text-muted"
          />
        </div>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <span className="label">
          {rows.length} of {questions.length} items
        </span>
        {filtered && (
          <button
            type="button"
            onClick={reset}
            className="font-mono text-caption text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent"
          >
            reset
          </button>
        )}
      </div>

      <Card tone="bare" pad="none" className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-small">
          <thead>
            <tr className="border-b border-border bg-paper-2 text-left">
              <SortHeader
                label="Item"
                colKey="item"
                sortKey={sortKey}
                sortDir={sortDir}
                onSort={onSort}
              />
              <SortHeader
                label="Role"
                colKey="role"
                sortKey={sortKey}
                sortDir={sortDir}
                onSort={onSort}
              />
              <SortHeader
                label="Modal vote"
                colKey="vote"
                sortKey={sortKey}
                sortDir={sortDir}
                onSort={onSort}
              />
              <SortHeader
                label="Agreement"
                colKey="agreement"
                sortKey={sortKey}
                sortDir={sortDir}
                onSort={onSort}
              />
              <SortHeader
                label="Status"
                colKey="status"
                sortKey={sortKey}
                sortDir={sortDir}
                onSort={onSort}
              />
              <th className={HEAD_CLASS}>Acceptable (&ge;70%)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((q) => {
              const modalCount = q.counts[q.modal] ?? 0;
              return (
                <tr key={q.id} className="border-b border-border/60">
                  <td className="px-4 py-2.5">{q.short}</td>
                  <td
                    className={`px-4 py-2.5 font-mono text-caption uppercase ${
                      q.role === "trap" ? "text-danger" : "text-accent-2"
                    }`}
                  >
                    {q.role}
                  </td>
                  <td className="px-4 py-2.5">{voteLabel(q.modal_vote)}</td>
                  <td className="px-4 py-2.5 font-mono text-caption tabular-nums">
                    {modalCount}/{q.n} ({pct1(q.agreement)})
                  </td>
                  <td className="px-4 py-2.5">
                    {q.locked ? (
                      <span className="rounded-full bg-accent/10 px-2 py-0.5 font-mono text-caption uppercase tracking-wider text-accent">
                        Locked
                      </span>
                    ) : (
                      <span className="rounded-full border border-border px-2 py-0.5 font-mono text-caption uppercase tracking-wider text-muted">
                        Provisional
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    {q.acceptable_actions.length
                      ? q.acceptable_actions
                          .map((k) =>
                            voteLabel(
                              q.options.find((o) => o.key === k)?.vote ?? k,
                            ),
                          )
                          .join(", ")
                      : "none reaches 70%"}
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  className="px-4 py-8 text-center text-small text-muted"
                >
                  No items match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
