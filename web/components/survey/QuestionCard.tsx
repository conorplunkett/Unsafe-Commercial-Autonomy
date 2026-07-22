import type { SurveyQuestion } from "@/lib/surveyResults";

// Consistent color semantics across every item, mirroring the admin dashboard:
// "ask" is always amber, "refuse" is always red, and proceed/act options get
// the site's accent greens by their order in the instrument.
const PROCEED_CLASSES = ["bg-accent", "bg-accent-2"];

function barClass(question: SurveyQuestion, key: string): string {
  const option = question.options.find((o) => o.key === key);
  if (!option || option.category === "ask") return "bg-warn";
  if (option.category === "refuse") return "bg-danger";
  const proceedKeys = question.options
    .filter((o) => o.category === "proceed")
    .map((o) => o.key);
  return PROCEED_CLASSES[proceedKeys.indexOf(key) % PROCEED_CLASSES.length];
}

function pct(numerator: number, denominator: number): string {
  if (!denominator) return "0%";
  return `${((numerator / denominator) * 100).toFixed(1)}%`;
}

export function QuestionCard({
  question,
  stem,
}: {
  question: SurveyQuestion;
  stem: string;
}) {
  const modalCount = question.counts[question.modal] ?? 0;
  return (
    <article className="flex h-full flex-col rounded-xl border border-border bg-paper p-5">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`font-mono text-[0.65rem] uppercase tracking-[0.14em] ${
            question.role === "trap" ? "text-danger" : "text-accent-2"
          }`}
        >
          {question.role}
        </span>
        <span
          className={`ml-auto rounded-full px-2.5 py-0.5 font-mono text-[0.65rem] uppercase tracking-[0.14em] ${
            question.locked
              ? "bg-accent/10 text-accent"
              : "border border-border text-muted"
          }`}
        >
          {question.locked ? "Locked" : "Provisional"}
        </span>
      </div>
      <h3 className="mt-2 font-serif text-lg leading-snug">{question.short}</h3>
      <details className="mt-2 text-sm text-ink/80">
        <summary className="cursor-pointer font-mono text-xs text-muted">
          Full wording as shown to respondents
        </summary>
        <p className="mt-2 leading-relaxed">{question.text}</p>
        <p className="mt-2 italic text-muted">{stem}</p>
      </details>

      <ul className="mt-4 space-y-3">
        {question.options.map((option) => {
          const chose = question.counts[option.key] ?? 0;
          const accept = question.accept_counts[option.key] ?? 0;
          const color = barClass(question, option.key);
          return (
            <li key={option.key}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-sm leading-snug">{option.label}</span>
                <span className="shrink-0 font-mono text-[0.7rem] text-muted">
                  {chose}/{question.n} · also ok {accept}/{question.denom}
                </span>
              </div>
              <div
                className="relative mt-1.5 h-2.5 overflow-hidden rounded-full bg-paper-2"
                role="img"
                aria-label={`${option.label}: chosen by ${chose} of ${question.n}; chosen or marked also acceptable by ${accept} of ${question.denom}`}
              >
                <div
                  className={`absolute inset-y-0 left-0 rounded-full ${color} opacity-30`}
                  style={{ width: pct(accept, question.denom) }}
                />
                <div
                  className={`absolute inset-y-0 left-0 rounded-full ${color}`}
                  style={{ width: pct(chose, question.n) }}
                />
              </div>
            </li>
          );
        })}
      </ul>

      <p className="mt-auto pt-4 text-sm text-ink/85">
        Modal: <strong>{question.modal_vote.replaceAll("_", " ")}</strong> —{" "}
        {pct(modalCount, question.n)} agreement ({modalCount}/{question.n}).
      </p>
    </article>
  );
}
