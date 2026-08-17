"""Stitch several sittings of the same gauntlet into one run.

A full Phase 2 grid is often not run in one go: the control conditions get
run on different days, or an axis is added later, leaving several run files
that are one experiment split across sittings. Nothing downstream can read them
as one — the leaderboard pools by model name, but every per-condition breakdown
in ``metrics`` is computed within a single run, so a multi-way split has no
`by_condition_and_framing` cell that compares conditions.

This module pools those sittings' episodes into one new run and recomputes the
metrics from the pooled episodes (``metrics.recompute_run_metrics``), so nothing
is ever an average of averages. Two rules keep that honest:

* The merge refuses unless the sources really are the same experiment — same
  model, same scenario set, same sampling config, and **no episode covered
  twice** (see ``episode_key``). Anything else is a hard stop, not a warning.
* The result records what it is: ``BenchmarkRun.merged_from`` names every source
  run, its date, and what it contributed. A merged run is never mistakable for
  one sitting.

Sources are never modified or deleted — the merged run is a new artifact, in
keeping with the repo's "publishing results is a new version, not an edit" rule.
Merging is manual by design (the ``merge`` CLI command asks before writing);
nothing here runs on its own.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .metrics import distinct_model_names, model_label, recompute_run_metrics
from .models import BenchmarkRun, EvaluationResult, MergeSource


# What an episode is, for the purpose of "did these two runs cover the same
# ground". Same tuple the Phase 2 checkpoint keys on (app/phase2/checkpoint.py)
# plus agent_id, which carries the scripted-agent identity Phase 1 runs use
# where there is no model. Two results with equal keys are the same cell of the
# same grid run twice — never something to silently pool.
EpisodeKey = Tuple[str, str, str, str, str, str, str, int]

# Config that must agree across sources for the merge to describe one
# experiment. `phase` and `answer_key_status` are structural; the rest are
# sampling settings that change what the model does.
_CONFIG_FIELDS = (
    "phase",
    "temperature",
    "reasoning_effort",
    "live",
    "answer_key_status",
)

OVERLAP_POLICIES = ("error", "prefer-newest", "prefer-oldest")

# Sources further apart than this get a warning on the merge report. Not a
# block: a deliberate re-run months later is legitimate, it just has to be a
# choice rather than something noticed after publication.
WIDE_SPREAD_DAYS = 30


class MergeIncompatible(Exception):
    """The named runs are not the same experiment, so pooling them would lie.

    Carries the individual reasons so the CLI can print them as a list rather
    than one run-on sentence.
    """

    def __init__(self, reasons: Sequence[str]):
        self.reasons = list(reasons)
        super().__init__("; ".join(self.reasons))


def episode_key(result: EvaluationResult) -> EpisodeKey:
    """Identity of one episode, for overlap detection and stable ordering.

    Every axis is stringified with a "" (or -1) stand-in for None so results
    from a run that predates an axis still sort and compare — a Phase 1 run
    carries no urgency, and that absence is itself part of the cell's identity.
    """
    return (
        result.agent_id or "",
        model_label(result),
        result.control_condition or "",
        result.framing or "",
        result.urgency or "",
        result.user_availability or "",
        result.scenario_id,
        -1 if result.seed is None else int(result.seed),
    )


def _sorted_sources(runs: Iterable[BenchmarkRun]) -> List[BenchmarkRun]:
    """Sources in a fixed order, so merging is independent of argument order.

    Oldest first, run_id breaking ties, which is also the order events are
    concatenated in — two people merging the same four runs get byte-identical
    files.
    """
    return sorted(runs, key=lambda run: (run.created_at, run.run_id))


def _union(values: Iterable[Iterable[Any]]) -> List[Any]:
    seen: Dict[Any, None] = {}
    for group in values:
        for value in group:
            seen.setdefault(value, None)
    return sorted(seen)


def _spread_days(runs: Sequence[BenchmarkRun]) -> Optional[float]:
    """Days between the oldest and newest source, or None if unparseable."""
    stamps = []
    for run in runs:
        try:
            stamps.append(datetime.fromisoformat(run.created_at.replace("Z", "+00:00")))
        except (ValueError, AttributeError):
            return None
    if len(stamps) < 2:
        return 0.0
    return round((max(stamps) - min(stamps)).total_seconds() / 86400, 1)


def _overlaps(runs: Sequence[BenchmarkRun]) -> Dict[EpisodeKey, List[str]]:
    """Episode keys covered by more than one source -> the run ids covering it."""
    owners: Dict[EpisodeKey, List[str]] = {}
    for run in runs:
        # A source that repeats a key *within itself* is not this function's
        # business — that is one run's own shape, and pooling does not change it.
        for key in {episode_key(result) for result in run.results}:
            owners.setdefault(key, []).append(run.run_id)
    return {key: run_ids for key, run_ids in owners.items() if len(run_ids) > 1}


def compatibility_report(
    runs: Sequence[BenchmarkRun], *, on_overlap: str = "error"
) -> Dict[str, Any]:
    """What merging these runs would mean, and whether it is allowed.

    ``blocking`` is empty exactly when ``merge_runs`` will succeed. ``warnings``
    are things the operator should see and decide about (a wide date spread, a
    resolved overlap) but that do not make the pooled numbers wrong.
    """
    if on_overlap not in OVERLAP_POLICIES:
        raise ValueError(f"Unknown overlap policy {on_overlap!r}; expected one of {OVERLAP_POLICIES}.")

    blocking: List[str] = []
    warnings: List[str] = []

    if len(runs) < 2:
        blocking.append("A merge needs at least two source runs.")
        return {"blocking": blocking, "warnings": warnings, "overlap_count": 0, "spread_days": 0.0}

    run_ids = [run.run_id for run in runs]
    if len(set(run_ids)) != len(run_ids):
        blocking.append("The same run id was given more than once.")

    # Same gauntlet. Compared as sets: the *order* scenarios were run in is not
    # part of the experiment, but a source covering a different subset makes
    # every per-condition denominator a different denominator.
    scenario_sets = {frozenset(run.scenario_ids) for run in runs}
    if len(scenario_sets) > 1:
        sizes = ", ".join(f"{run.run_id} ({len(run.scenario_ids)})" for run in runs)
        blocking.append(f"Sources cover different scenario sets: {sizes}.")

    # Same model. model_names is first-class on the run; a source that predates
    # it falls back to what its episodes say.
    name_sets = {frozenset(run.model_names or distinct_model_names(run.results)) for run in runs}
    if len(name_sets) > 1:
        listed = ", ".join(
            f"{run.run_id} ({'/'.join(run.model_names or distinct_model_names(run.results)) or 'unknown'})"
            for run in runs
        )
        blocking.append(f"Sources are not the same model: {listed}.")

    # Same sampling config.
    for field in _CONFIG_FIELDS:
        values = {getattr(run, field) for run in runs}
        if len(values) > 1:
            listed = ", ".join(f"{run.run_id}={getattr(run, field)!r}" for run in runs)
            blocking.append(f"Sources disagree on {field}: {listed}.")

    overlap = _overlaps(runs)
    if overlap:
        sample = ", ".join(
            "/".join(str(part) for part in key if part not in ("", -1))
            for key in sorted(overlap)[:3]
        )
        more = f" (+{len(overlap) - 3} more)" if len(overlap) > 3 else ""
        if on_overlap == "error":
            blocking.append(
                f"{len(overlap)} episode(s) are covered by more than one source, "
                f"e.g. {sample}{more}. Pooling them would count those cells twice. "
                "Pass --on-overlap=prefer-newest (or prefer-oldest) to keep one copy."
            )
        else:
            keep = "newest" if on_overlap == "prefer-newest" else "oldest"
            warnings.append(
                f"{len(overlap)} episode(s) covered by more than one source; "
                f"keeping the {keep} copy of each and recording the drops."
            )

    spread = _spread_days(runs)
    if spread is None:
        warnings.append("At least one source has an unparseable created_at; date spread unknown.")
    elif spread > WIDE_SPREAD_DAYS:
        warnings.append(
            f"Sources span {spread} days — the same model id can be served by a "
            "different checkpoint over that long."
        )

    return {
        "blocking": blocking,
        "warnings": warnings,
        "overlap_count": len(overlap),
        "spread_days": spread,
    }


def _resolve_overlaps(
    runs: Sequence[BenchmarkRun], on_overlap: str
) -> Tuple[Dict[str, List[EvaluationResult]], Dict[str, int]]:
    """Pick one copy of each episode; return kept results and per-source drops.

    ``runs`` arrives oldest-first, so "prefer-newest" keeps the last source to
    claim a key and "prefer-oldest" keeps the first. Under the default "error"
    policy this is never reached with an actual overlap — the report blocks
    first — so it degrades to a plain pass-through.

    Only *cross-source* duplicates are resolved. A key a single source repeats
    within itself is that run's own shape, and merging must not quietly edit it.
    """
    order = list(runs) if on_overlap != "prefer-newest" else list(reversed(runs))
    claimed: Dict[EpisodeKey, str] = {}
    kept: Dict[str, List[EvaluationResult]] = {run.run_id: [] for run in runs}
    dropped: Dict[str, int] = {run.run_id: 0 for run in runs}
    for run in order:
        for result in run.results:
            key = episode_key(result)
            owner = claimed.get(key)
            if owner is not None and owner != run.run_id:
                dropped[run.run_id] += 1
                continue
            claimed[key] = run.run_id
            kept[run.run_id].append(result)
    return kept, dropped


def merge_runs(
    runs: Sequence[BenchmarkRun],
    *,
    run_id: str,
    created_at: Optional[str] = None,
    merged_at: Optional[str] = None,
    on_overlap: str = "error",
) -> BenchmarkRun:
    """Pool the sources' episodes into one new run, metrics recomputed.

    ``created_at`` defaults to the newest source's, not to now: the pooled data
    is no fresher than its newest episode, and stamping the merge time there
    would make a stitched-together January run look like it happened today.
    The actual merge time is recorded separately as ``merged_at``.

    Raises ``MergeIncompatible`` if the sources are not one experiment.
    """
    report = compatibility_report(runs, on_overlap=on_overlap)
    if report["blocking"]:
        raise MergeIncompatible(report["blocking"])

    ordered = _sorted_sources(runs)
    kept, dropped = _resolve_overlaps(ordered, on_overlap)

    results = sorted(
        (result for run in ordered for result in kept[run.run_id]),
        key=episode_key,
    )
    events = [event for run in ordered for event in run.events]

    sources = [
        MergeSource(
            run_id=run.run_id,
            created_at=run.created_at,
            episode_count=len(kept[run.run_id]),
            control_conditions=list(run.control_conditions),
            framings=list(run.framings),
            urgencies=list(run.urgencies),
            user_availabilities=list(run.user_availabilities),
            seeds=list(run.seeds),
            dropped_overlaps=dropped[run.run_id],
        )
        for run in ordered
    ]

    first = ordered[0]
    merged = BenchmarkRun(
        run_id=run_id,
        created_at=created_at or max(run.created_at for run in ordered),
        phase=first.phase,
        agent_ids=_union(run.agent_ids for run in ordered),
        model_ids=_union(run.model_ids for run in ordered),
        model_names=distinct_model_names(results),
        control_conditions=_union(run.control_conditions for run in ordered),
        framings=_union(run.framings for run in ordered),
        urgencies=_union(run.urgencies for run in ordered),
        user_availabilities=_union(run.user_availabilities for run in ordered),
        seeds=_union(run.seeds for run in ordered),
        temperature=first.temperature,
        reasoning_effort=first.reasoning_effort,
        live=first.live,
        answer_key_status=first.answer_key_status,
        # Identical across sources (the report blocks otherwise), so the first
        # source's order is kept rather than sorting — it is the order the
        # scenario set itself defines.
        scenario_ids=list(first.scenario_ids),
        results=results,
        events=events,
        metrics={},
        merged_from=sources,
        merged_at=merged_at or datetime.now(timezone.utc).isoformat(),
    )
    # Every breakdown, including the phase2 block, from the pooled episodes —
    # the same function `recompute` uses, so a merged run's metrics are computed
    # exactly like a single run's over the same episodes.
    recompute_run_metrics(merged)
    return merged


def superseded_run_ids(runs: Iterable[BenchmarkRun]) -> Dict[str, str]:
    """Map source run_id -> the merged run_id that pooled it.

    Used by the Lab to flag stored runs whose episodes now live inside a merged
    run, and by publish to stamp `superseded_by` on the published rows. A run
    listed by two merged runs reports the newest one.
    """
    superseded: Dict[str, Tuple[str, str]] = {}
    for run in runs:
        for source in run.merged_from:
            existing = superseded.get(source.run_id)
            if existing is None or existing[1] <= run.created_at:
                superseded[source.run_id] = (run.run_id, run.created_at)
    return {run_id: merged_id for run_id, (merged_id, _) in superseded.items()}
