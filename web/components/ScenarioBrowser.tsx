"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { SCENARIOS, type ScenarioCard } from "@/lib/scenarios";
import { CATEGORY_ORDER, CATEGORY_LABELS, categoryLabel } from "@/lib/labels";
import { Card } from "@/components/ui/Card";

type RoleFilter = "all" | "trap" | "lookalike";

const PAGE_SIZE = 25;

function RoleBadge({ role }: { role: ScenarioCard["pair_role"] }) {
  const trap = role === "trap";
  return (
    <span
      className={`rounded-full border px-2.5 py-0.5 font-mono text-caption uppercase tracking-wider ${
        trap
          ? "border-danger/40 bg-danger/10 text-danger"
          : "border-accent/40 bg-accent/10 text-accent"
      }`}
    >
      {trap ? "Trap" : "Lookalike"}
    </span>
  );
}

function ScenarioTile({ s }: { s: ScenarioCard }) {
  return (
    <Card className="flex flex-col">
      <div className="flex flex-col items-start gap-1.5">
        <div className="flex items-center gap-2">
          <RoleBadge role={s.pair_role} />
          <span className="whitespace-nowrap font-mono text-caption uppercase tracking-wider text-muted">
            · {s.stakes} stakes
          </span>
        </div>
        <span className="font-mono text-caption uppercase tracking-wider text-muted">
          {categoryLabel(s.category)}
        </span>
      </div>
      <p className="mt-3 grow text-ui leading-snug text-ink/90">
        {s.situation}
      </p>
      <div className="mt-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-t border-border pt-3">
        <span className="text-small">
          <span className="text-muted">Right answer: </span>
          <span className="text-accent">{s.right_answer ?? "—"}</span>
        </span>
        {s.failure_tested && (
          <span className="font-mono text-caption text-muted">
            tests: {s.failure_tested}
          </span>
        )}
      </div>
    </Card>
  );
}

export function ScenarioBrowser({ teaser = false }: { teaser?: boolean }) {
  const [category, setCategory] = useState<string>("all");
  const [role, setRole] = useState<RoleFilter>("all");
  const [page, setPage] = useState(1);
  const listTop = useRef<HTMLParagraphElement>(null);

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

  // Clamp rather than trust `page`: a filter that shrinks the result set can
  // strand it past the end, which would render an empty grid.
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount);
  const start = (current - 1) * PAGE_SIZE;
  const shown = filtered.slice(start, start + PAGE_SIZE);

  function goTo(next: number) {
    setPage(next);
    listTop.current?.scrollIntoView({ block: "start" });
  }

  if (teaser) {
    return (
      <div className="mt-6">
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {teaserCards.map((s) => (
            <ScenarioTile key={s.scenario_id} s={s} />
          ))}
        </div>
        <Link
          href="/scenarios"
          className="mt-6 inline-block font-serif text-prose text-accent hover:underline"
        >
          Browse all {SCENARIOS.length} Phase-1 scenarios →
        </Link>
      </div>
    );
  }

  const chip =
    "rounded-full border px-3 py-1 font-mono text-caption transition-colors";
  const on = "border-accent bg-accent/10 text-accent";
  const off = "border-border text-muted hover:text-ink";

  return (
    <div className="mt-6">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <button
            className={`${chip} ${category === "all" ? on : off}`}
            onClick={() => { setCategory("all"); setPage(1); }}
          >
            All categories
          </button>
          {CATEGORY_ORDER.map((c) => (
            <button
              key={c}
              className={`${chip} ${category === c ? on : off}`}
              onClick={() => { setCategory(c); setPage(1); }}
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
              onClick={() => { setRole(r); setPage(1); }}
            >
              {r === "all" ? "Trap + lookalike" : r}
            </button>
          ))}
        </div>
      </div>

      <p
        ref={listTop}
        className="mt-5 scroll-mt-20 font-mono text-caption text-muted"
      >
        {pageCount > 1
          ? `${start + 1}–${start + shown.length} of ${filtered.length} scenarios`
          : `${filtered.length} of ${SCENARIOS.length} scenarios`}
      </p>

      <div className="mt-3 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {shown.map((s) => (
          <ScenarioTile key={s.scenario_id} s={s} />
        ))}
      </div>

      {pageCount > 1 && (
        <nav
          aria-label="Scenario pages"
          className="mt-8 flex flex-wrap items-center gap-2"
        >
          <button
            className={`${chip} ${off} disabled:opacity-40 disabled:hover:text-muted`}
            onClick={() => goTo(current - 1)}
            disabled={current === 1}
          >
            ← Prev
          </button>
          {Array.from({ length: pageCount }, (_, i) => i + 1).map((n) => (
            <button
              key={n}
              className={`${chip} ${n === current ? on : off} tabular-nums`}
              aria-current={n === current ? "page" : undefined}
              onClick={() => goTo(n)}
            >
              {n}
            </button>
          ))}
          <button
            className={`${chip} ${off} disabled:opacity-40 disabled:hover:text-muted`}
            onClick={() => goTo(current + 1)}
            disabled={current === pageCount}
          >
            Next →
          </button>
        </nav>
      )}
    </div>
  );
}
