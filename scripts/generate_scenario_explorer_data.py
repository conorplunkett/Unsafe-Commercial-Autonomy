"""Snapshot Phase 2's 113 trap/lookalike pairs for the admin Scenario Explorer.

Reads the merged Scenario records the same way app/main.py's
GET /api/phase2/scenarios does, groups the 226 scenarios into 113
trap/lookalike pairs by pair_id, and writes the result as the JSON assets
bundled into the admin-scenario-data Supabase Edge Function. This script is
the only way that function's data gets refreshed -- re-run it and redeploy
after any change to data/scenario_sets/v2_250_scenarios.md or
data/answer_keys/v2_constraints.json.

Split into many small chunk files (scenario_pairs.NNN.json, each a plain
JSON array of a few pairs) rather than one ~850KB combined file: the
combined file -- and even one file per category -- is too large for some
tooling to read or relay in a single piece. Chunks are packed greedily by
serialized size (CHUNK_SIZE_BUDGET), not by a fixed pair count: pair size
varies a lot (category E's prompt-injection pairs run much longer than a
plain spend-limit pair), so a fixed count doesn't bound file size the way
a size budget does. index.ts imports every chunk in numeric order and
concatenates them; nothing about a pair's category or role depends on
which chunk it landed in, since both are already fields on the pair record
itself.

Pair order is NOT recomputed: it is exactly the first-seen order of pair_id
in load_scenarios() output, i.e. the Markdown file's own row order (category
A to E, ascending pair number within each category, including the numbering
gaps left by the 2026-07-24 twelve-pair cut -- e.g. category B skips to B1,
B3, B4, B5, B10...). Prev/Next in the UI walks this order.

Run from the repo root:  python scripts/generate_scenario_explorer_data.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.data import load_scenarios  # noqa: E402
from app.models import model_to_dict  # noqa: E402
from app.phase2 import PHASE2_SCENARIO_SET  # noqa: E402

OUT_DIR = ROOT / "supabase" / "functions" / "admin-scenario-data"
INDEX_PATH = OUT_DIR / "index.ts"

# Target serialized size (bytes) per chunk file, packed greedily -- see the
# module docstring for why this is a byte budget rather than a pair count.
CHUNK_SIZE_BUDGET = 15_000

# Category order is no longer the file-splitting axis (chunks are sequential
# across the whole 113-pair order, independent of category boundaries), but
# this is still the canonical A-to-E order build_pairs() produces and the
# order Prev/Next walks in the UI.
CATEGORY_ORDER = [
    "spend_limits",
    "authorization_scope",
    "consent_and_escalation",
    "privacy_and_disclosure",
    "adversarial_robustness",
]

EXPECTED_CATEGORY_COUNTS = {
    "spend_limits": 25,
    "authorization_scope": 14,
    "consent_and_escalation": 24,
    "privacy_and_disclosure": 25,
    "adversarial_robustness": 25,
}
EXPECTED_PAIR_COUNT = sum(EXPECTED_CATEGORY_COUNTS.values())


def build_pairs() -> List[Dict[str, Any]]:
    records = [model_to_dict(s) for s in load_scenarios(PHASE2_SCENARIO_SET)]

    grouped: Dict[str, Dict[str, Dict[str, Any]]] = {}
    order: List[str] = []
    for record in records:
        pair_id = record["pair_id"]
        role = record["pair_role"]
        if pair_id not in grouped:
            grouped[pair_id] = {}
            order.append(pair_id)
        if role in grouped[pair_id]:
            raise ValueError(f"Duplicate {role!r} for pair_id {pair_id!r}")
        grouped[pair_id][role] = record

    pairs: List[Dict[str, Any]] = []
    for pair_id in order:
        roles = grouped[pair_id]
        missing = {"trap", "lookalike"} - roles.keys()
        if missing:
            raise ValueError(f"Pair {pair_id!r} is missing role(s): {sorted(missing)}")
        trap = roles["trap"]
        pairs.append(
            {
                "pair_id": pair_id,
                "pair_label": trap["environment"]["pair"],
                "category": trap["category"],
                "trap": trap,
                "lookalike": roles["lookalike"],
            }
        )

    if len(pairs) != EXPECTED_PAIR_COUNT:
        raise ValueError(f"Expected {EXPECTED_PAIR_COUNT} pairs, got {len(pairs)}")

    counts: Dict[str, int] = {}
    for pair in pairs:
        counts[pair["category"]] = counts.get(pair["category"], 0) + 1
    if counts != EXPECTED_CATEGORY_COUNTS:
        raise ValueError(f"Category counts drifted from expectations: {counts}")

    return pairs


def chunk_filename(index: int) -> str:
    return f"scenario_pairs.{index:03d}.json"


def pack_chunks(pairs: List[Dict[str, Any]], budget: int) -> List[List[Dict[str, Any]]]:
    """Greedily group consecutive pairs so each chunk's own serialized size
    stays near `budget`. A single pair larger than the budget still gets its
    own one-pair chunk rather than being split (a pair is never divided)."""
    chunks: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    current_size = 2  # "[]"
    for pair in pairs:
        pair_size = len(json.dumps(pair, indent=2))
        addition = pair_size + 2  # ", " (or the closing bracket, roughly)
        if current and current_size + addition > budget:
            chunks.append(current)
            current, current_size = [], 2
        current.append(pair)
        current_size += addition
    if current:
        chunks.append(current)
    return chunks


def write_chunk_files(pairs: List[Dict[str, Any]], out_dir: Path) -> List[Path]:
    # Clear any chunk files from a previous run with a different chunk count,
    # so a shrinking chunk count never leaves a stale, no-longer-imported
    # file behind for a human to wonder about.
    for stale in out_dir.glob("scenario_pairs.*.json"):
        stale.unlink()

    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for i, chunk in enumerate(pack_chunks(pairs, CHUNK_SIZE_BUDGET)):
        path = out_dir / chunk_filename(i)
        path.write_text(json.dumps(chunk, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def sync_index_chunks(index_path: Path, written: List[Path]) -> None:
    """Keep the Edge Function's imports in step with generated chunk count."""
    source = index_path.read_text(encoding="utf-8")
    imports = "\n".join(
        f'import chunk{i:03d} from "./{path.name}" with {{ type: "json" }};'
        for i, path in enumerate(written)
    )
    spreads = ",\n".join(f"  ...chunk{i:03d}" for i in range(len(written)))
    replacement = f"{imports}\n\nconst SCENARIO_PAIRS = [\n{spreads}\n];"
    updated, count = re.subn(
        r'import chunk000 from .*?\n\nconst SCENARIO_PAIRS = \[.*?\n\];',
        replacement,
        source,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError(f"Could not locate generated chunk block in {index_path}")
    index_path.write_text(updated, encoding="utf-8")


def main(out_dir: Path = OUT_DIR) -> None:
    pairs = build_pairs()
    written = write_chunk_files(pairs, out_dir)
    if out_dir.resolve() == OUT_DIR.resolve():
        sync_index_chunks(INDEX_PATH, written)
    print(f"Wrote {len(pairs)} pairs across {len(written)} chunk files to {out_dir}")


if __name__ == "__main__":
    main()
