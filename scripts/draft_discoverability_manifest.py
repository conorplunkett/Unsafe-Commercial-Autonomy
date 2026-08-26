"""Draft data/answer_keys/discoverability.json entries for human review.

Read-only authoring helper for the discoverability sidecar: for every v2 trap
it proposes `deciding_fact` patterns — the rule clause the task itself states
plus the in-world evidence keyword(s) — by checking candidates against the
actual no_policy surface (app/phase2/sandbox.no_policy_surface). Traps where
no confident candidate survives are emitted with "REVIEW" so the author reads
the scenario instead of trusting the heuristic. The committed manifest is the
reviewed output of this script, never its raw dump; the surface test in
tests/test_discoverability.py is what the committed file must satisfy.

Usage: python scripts/draft_discoverability_manifest.py > /tmp/draft.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data import DATA_DIR, load_scenarios  # noqa: E402
from app.phase2.sandbox import no_policy_surface  # noqa: E402

V2_SET = DATA_DIR / "scenario_sets" / "v2_250_scenarios.md"

# Words from prohibited-category tokens that also appear as in-world evidence
# on the relevant merchant pages (e.g. "refurbished" both names the category
# and is printed on the trap listing). Generic glue words never qualify.
STOPWORDS = {"the", "a", "an", "of", "and", "or", "third", "party", "non", "items"}


def instruction_rule_clause(instruction: str) -> str | None:
    """The constraint clause the task itself states, if it states one."""
    for separator in (";", " — "):
        if separator in instruction:
            clause = instruction.split(separator, 1)[1].strip().rstrip(".")
            if clause:
                return clause
    match = re.search(
        r"((?:under|budget|max|limit|cap|up to|about|needs?|no)\b[^.;]*\$[\d,.]+[^.;]*)",
        instruction,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return None


def category_keywords(policy: dict, surface_lower: str) -> list[str]:
    keywords: list[str] = []
    for token in policy.get("prohibited_categories") or []:
        for word in str(token).split("_"):
            if len(word) > 3 and word not in STOPWORDS and word in surface_lower:
                keywords.append(word)
    return sorted(set(keywords))


def main() -> None:
    draft: dict[str, dict] = {}
    for scenario in load_scenarios(V2_SET):
        if scenario.pair_role != "trap":
            continue
        surface = no_policy_surface(scenario)
        surface_lower = surface.lower()
        patterns: list[str] = []
        clause = instruction_rule_clause(scenario.user_instruction)
        if clause and clause.lower() in surface_lower:
            patterns.append(clause)
        patterns.extend(category_keywords(scenario.payment_policy, surface_lower))
        entry: dict = {"deciding_fact": patterns}
        if not patterns:
            entry = {"REVIEW": "no candidate found — read the scenario", "deciding_fact": []}
        draft[scenario.scenario_id] = entry
    json.dump(draft, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
