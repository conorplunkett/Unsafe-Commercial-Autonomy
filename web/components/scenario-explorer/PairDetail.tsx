import { categoryLabel } from "@/lib/labels";
import type { ScenarioPair, ScenarioReview } from "@/lib/scenarioExplorer";
import { ScenarioSide } from "./ScenarioSide";

// A pair is off-limits the moment either side is on the preference survey --
// almost always just the trap (the lookalike is never the surveyed one), but
// once its wording is on the instrument its pair-mate is frozen too, since
// the two are graded as a matched comparison.
function pairIsLocked(pair: ScenarioPair): boolean {
  return pair.trap.semantic_only || pair.lookalike.semantic_only;
}

// Status badges in the Experiment Lab's language (see static/lab.css
// `.phase-badge`): a soft filled pill for an active state, a hollow neutral
// pill for its absence -- sentence case in the sans face, not the mono
// uppercase tags used elsewhere in the explorer.
const BADGE_BASE =
  "inline-flex items-center rounded-full px-2.5 py-1 text-caption";
const BADGE_GOOD = "bg-accent/10 font-semibold text-accent";
const BADGE_NEUTRAL = "border border-border font-medium text-muted";
const BADGE_ALERT = "bg-danger/10 font-semibold text-danger";

function EditabilityPill({ pair }: { pair: ScenarioPair }) {
  if (pairIsLocked(pair)) {
    return (
      <span
        title="On the preference survey -- never edit this scenario or its pair-mate"
        className={`${BADGE_BASE} ${BADGE_ALERT}`}
      >
        Locked
      </span>
    );
  }
  return (
    <span
      title="Not on the preference survey -- safe to edit"
      className={`${BADGE_BASE} ${BADGE_NEUTRAL}`}
    >
      Editable
    </span>
  );
}

// Whether the survey has actually run and locked this pair's key -- distinct
// from EditabilityPill above, which only says the key is *subject to* the
// survey, not that the survey has concluded it yet (see the answer_key_status
// values: a pair can be semantic_only and still sit at "awaiting_survey").
function isSurveyKeyed(pair: ScenarioPair): boolean {
  return (
    pair.trap.answer_key_status === "survey_locked_70" ||
    pair.lookalike.answer_key_status === "survey_locked_70"
  );
}

function EnforcedPill({ pair }: { pair: ScenarioPair }) {
  // in_enforced_arm is uniform across a pair by construction: a reachable
  // trap brings its lookalike in with it (app/phase2/scope.py), so either
  // side names the same answer.
  const enforced = pair.trap.enforcement.in_enforced_arm;
  return (
    <span
      title={
        enforced
          ? "tool_constraints runs this pair -- the rail can refuse a payment somewhere in it"
          : "tool_constraints skips this pair -- no structured field its world offers trips the rail"
      }
      className={`${BADGE_BASE} ${enforced ? BADGE_GOOD : BADGE_NEUTRAL}`}
    >
      {enforced ? "Tool constraints" : "No tool constraints"}
    </span>
  );
}

function SurveyKeyedPill({ pair }: { pair: ScenarioPair }) {
  const keyed = isSurveyKeyed(pair);
  return (
    <span
      title={
        keyed
          ? "The preference survey has concluded and locked this pair's answer key"
          : "The preference survey has not locked this pair's answer key yet"
      }
      className={`${BADGE_BASE} ${keyed ? BADGE_GOOD : BADGE_NEUTRAL}`}
    >
      {keyed ? "Survey keyed" : "Not survey keyed"}
    </span>
  );
}

export function PairDetail({
  pair,
  reviews,
  onToggleReview,
}: {
  pair: ScenarioPair;
  reviews?: Record<string, ScenarioReview>;
  onToggleReview?: (scenarioId: string, next: boolean, contentHash: string) => void;
}) {
  return (
    <div>
      <div className="border-b border-border pb-3">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <span className="font-mono text-caption uppercase tracking-wider text-muted">
            {pair.pair_label} · {categoryLabel(pair.category)}
          </span>
          <span className="text-small">
            <span className="text-muted">Right answer: </span>
            <span className="text-accent">{pair.trap.right_answer ?? "—"}</span>
          </span>
        </div>

        <div className="mt-2 flex flex-wrap gap-2">
          <EditabilityPill pair={pair} />
          <SurveyKeyedPill pair={pair} />
          <EnforcedPill pair={pair} />
        </div>

        {pair.trap.failure_tested && (
          <p className="mt-2 font-mono text-caption text-muted">
            tests: {pair.trap.failure_tested}
          </p>
        )}
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <ScenarioSide
          scenario={pair.trap}
          review={reviews?.[pair.trap.scenario_id]}
          onToggleReview={
            onToggleReview &&
            ((next) => onToggleReview(pair.trap.scenario_id, next, pair.trap.content_hash))
          }
        />
        <ScenarioSide
          scenario={pair.lookalike}
          review={reviews?.[pair.lookalike.scenario_id]}
          onToggleReview={
            onToggleReview &&
            ((next) =>
              onToggleReview(pair.lookalike.scenario_id, next, pair.lookalike.content_hash))
          }
        />
      </div>
    </div>
  );
}
