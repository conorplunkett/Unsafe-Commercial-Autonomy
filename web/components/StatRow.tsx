"use client";

import { useData } from "./DataProvider";
import { summarize, distinct, modelLabel } from "@/lib/metrics";
import { pct, num } from "@/lib/format";

function tone(t?: string) {
  if (t === "danger") return "text-danger";
  if (t === "warn") return "text-warn";
  if (t === "accent") return "text-accent";
  return "text-ink";
}

export function StatRow() {
  const { results } = useData();
  const s = summarize(results);
  const stats = [
    { label: "Unsafe payment", value: pct(s.unsafePaymentRate), t: "danger" },
    { label: "False refusal", value: pct(s.falseRefusalRate), t: "warn" },
    { label: "User welfare", value: pct(s.userWelfareScore), t: "accent" },
    { label: "Scenarios", value: num(distinct(results, (r) => r.scenario_id)) },
    { label: "Models", value: num(distinct(results, modelLabel)) },
    { label: "Conditions", value: num(distinct(results, (r) => r.control_condition)) },
  ];
  return (
    <div className="mt-12 grid grid-cols-2 gap-y-6 border-y border-border py-6 sm:grid-cols-3 md:grid-cols-6">
      {stats.map((st) => (
        <div key={st.label} className="border-l border-border pl-4 first:border-l-0 first:pl-0 md:border-l md:first:border-l-0">
          <p className="label">{st.label}</p>
          <p className={`mt-1 font-mono text-[1.7rem] leading-none ${tone(st.t)}`}>
            {st.value}
          </p>
        </div>
      ))}
    </div>
  );
}
