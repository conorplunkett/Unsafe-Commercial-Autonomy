"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { SCENARIOS, type ScenarioCard } from "@/lib/scenarios";
import { CATEGORY_ORDER, CATEGORY_LABELS, categoryLabel } from "@/lib/labels";

type RoleFilter = "all" | "trap" | "lookalike";

function RoleBadge({ role }: { role: ScenarioCard["pair_role"] }) {
  const trap = role === "trap";
  return (
    <span
      className={`rounded-full border px-2.5 py-0.5 font-mono text-[0.65rem] uppercase tracking-wider ${
        trap
          ? "border-danger/40 bg-danger/10 text-danger"
          : "border-accent/40 bg-accent/10 text-accent"
      }`}
    >
      {trap ? "Trap" : "Lookalike"}
    </span>
  );
}

function Card({ s }: { s: ScenarioCard }) {
  return (
    <div className="flex flex-col rounded-xl border border-border bg-paper-2/40 p-5">
      <div className="flex flex-wrap items-center gap-2">
        <RoleBadge role={s.pair_role} />
        <span className="font-mono text-[0.65rem] uppercase tracking-wider text-muted">
          {categoryLabel(s.category)}
        </span>
        <span className="font-mono text-[0.65rem] uppercase tracking-wider text-muted">
          · {s.stakes} stakes
        </span>
      </div>
      <p className="mt-3 grow text-[1.02rem] leading-snug text-ink/90">
        {s.situation}
      </p>
      <div className="mt-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-t border-border pt-3">
        <span className="text-sm">
          <span className="text-muted">Right answer: </span>
          <span className="text-accent">{s.right_answer ?? "—"}</span>
        </span>
        {s.failure_tested && (
          <span className="font-mono text-[0.7rem] text-muted">
            tests: {s.failure_tested}
          </span>
        )}
      </div>
    </div>
  );
}

export function ScenarioBrowser({ teaser = false }: { teaser?: boolean }) {
  const [category, setCategory] = useState<string>("all");
  const [role, setRole] = useState<RoleFilter>("all");

  const teaserCards = useMemo(
    () =>
      CATEGORY_ORDER.map((c) =>
        SCENARIOS.find((s) => s.category === c && s.pair_role === "trap"),
      ).filter((s): s is ScenarioCard => s != null),
    [],
  );

  const filtered = useMemo(
    () =>
      SCENARIOS.filter(
        (s) =>
          (category === "all" || s.category === category) &&
          (role === "all" || s.pair_role === role),
      ),
    [category, role],
  );

  if (teaser) {
    return (
      <div className="mt-6">
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {teaserCards.map((s) => (
            <Card key={s.scenario_id} s={s} />
          ))}
        </div>
        <Link
          href="/scenarios"
          className="mt-6 inline-block font-serif text-lg text-accent hover:underline"
        >
          Browse all {SCENARIOS.length} Phase-1 scenarios →
        </Link>
      </div>
    );
  }

  const chip =
    "rounded-full border px-3 py-1 font-mono text-xs transition-colors";
  const on = "border-accent bg-accent/10 text-accent";
  const off = "border-border text-muted hover:text-ink";

  return (
    <div className="mt-6">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <button
            className={`${chip} ${category === "all" ? on : off}`}
            onClick={() => setCategory("all")}
          >
            All categories
          </button>
          {CATEGORY_ORDER.map((c) => (
            <button
              key={c}
              className={`${chip} ${category === c ? on : off}`}
              onClick={() => setCategory(c)}
            >
              {CATEGORY_LABELS[c]}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {(["all", "trap", "lookalike"] as RoleFilter[]).map((r) => (
            <button
              key={r}
              className={`${chip} ${role === r ? on : off}`}
              onClick={() => setRole(r)}
            >
              {r === "all" ? "Trap + lookalike" : r}
            </button>
          ))}
        </div>
      </div>

      <p className="mt-5 font-mono text-xs text-muted">
        {filtered.length} of {SCENARIOS.length} scenarios
      </p>

      <div className="mt-3 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((s) => (
          <Card key={s.scenario_id} s={s} />
        ))}
      </div>
    </div>
  );
}
