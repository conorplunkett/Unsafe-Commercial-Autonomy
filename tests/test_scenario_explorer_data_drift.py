"""The committed Scenario Explorer snapshot may only lag its sources deliberately.

`supabase/functions/admin-scenario-data/` is a generated snapshot of the 113
Phase 2 pairs, and `scripts/generate_scenario_explorer_data.py` is the only
thing that refreshes it. Nothing enforced that, so the snapshot drifted quietly
through a run of scenario edits: by 2026-08-23 a regeneration moved 71 files
(~8.4k insertions, ~9.9k deletions) and the chunk count from 70 to 84, none of
which was a deliberate content change -- just accumulated staleness nobody had
a signal for. The admin UI was serving scenario text that no longer matched
`v2_250_scenarios.md` or `v2_constraints.json`.

This turns that divergence into a failing test, the same way
test_phase2_research_contract.py guards the frozen projection and
test_survey_key_alignment.py guards the generated environments. It regenerates
into a tmp_path copy and compares, so a run never mutates the real checkout.

Note this guards the COMMITTED snapshot, not the DEPLOYED Edge Function: a
green suite means the repo is self-consistent, not that Supabase is serving it.
Redeploying admin-scenario-data after a merge that changes these files is still
a manual step.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "supabase" / "functions" / "admin-scenario-data"
UPDATE_COMMAND = "python scripts/generate_scenario_explorer_data.py"


def _load_generator():
    path = ROOT / "scripts" / "generate_scenario_explorer_data.py"
    spec = importlib.util.spec_from_file_location("generate_scenario_explorer_data", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generator = _load_generator()


def test_scenario_explorer_chunks_have_not_drifted(tmp_path):
    """Every committed pair file matches what the generator produces today."""
    written = generator.write_pair_files(generator.build_pairs(), tmp_path)

    expected = {path.name: path.read_text(encoding="utf-8") for path in written}
    committed = {
        path.name: path.read_text(encoding="utf-8")
        for path in OUT_DIR.glob("scenario_pairs.*.json")
    }

    missing = sorted(set(expected) - set(committed))
    extra = sorted(set(committed) - set(expected))
    assert not missing and not extra, (
        "Scenario Explorer chunk files drifted "
        f"({len(committed)} committed vs {len(expected)} generated).\n"
        + (f"- missing: {', '.join(missing)}\n" if missing else "")
        + (f"- stale, no longer generated: {', '.join(extra)}\n" if extra else "")
        + f"Run `{UPDATE_COMMAND}` and commit the result."
    )

    changed = sorted(name for name in expected if expected[name] != committed[name])
    assert not changed, (
        f"{len(changed)} Scenario Explorer chunk file(s) are stale against "
        "data/scenario_sets/v2_250_scenarios.md and "
        "data/answer_keys/v2_constraints.json:\n"
        + "\n".join(f"- {name}" for name in changed[:15])
        + (f"\n- ... and {len(changed) - 15} more" if len(changed) > 15 else "")
        + f"\nRun `{UPDATE_COMMAND}` and commit the result."
    )


def test_scenario_explorer_index_imports_every_committed_pair_file(tmp_path):
    """index.ts's import block stays in step with the generated pair files.

    write_pair_files deletes files a previous run wrote, so a removed or
    renamed pair can leave index.ts importing a file that no longer exists --
    which fails at Edge Function deploy time, not here, unless this checks it.
    The import list also carries the canonical pair order (the filenames sort
    lexicographically), so its order is checked too.
    """
    import re

    pairs = generator.build_pairs()
    written = generator.write_pair_files(pairs, tmp_path)
    source = (OUT_DIR / "index.ts").read_text(encoding="utf-8")

    for pair, path in zip(pairs, written):
        name = generator.pair_import_name(pair["pair_id"])
        statement = f'import {name} from "./{path.name}" with {{ type: "json" }};'
        assert statement in source, (
            f"index.ts does not import {path.name}. "
            f"Run `{UPDATE_COMMAND}` and commit the result."
        )
        assert re.search(rf"^  {name},?$", source, re.MULTILINE), (
            f"index.ts imports {path.name} but never lists it in "
            f"SCENARIO_PAIRS. Run `{UPDATE_COMMAND}` and commit the result."
        )

    imported = re.findall(r'from "\./(scenario_pairs\.[^"]+\.json)"', source)
    assert imported == [path.name for path in written], (
        "index.ts's imports do not match the generated pair files (or their "
        f"canonical order). Run `{UPDATE_COMMAND}` and commit the result."
    )


def test_meta_json_has_not_drifted(tmp_path):
    """meta.json's source_blob_shas must match the source files as they are
    right now -- otherwise a redeploy with stale source_blob_shas would make
    the Explorer's freshness check lie in the "current" direction instead of
    just failing to detect staleness."""
    generator.write_meta_file(tmp_path)
    expected = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
    committed = json.loads((OUT_DIR / "meta.json").read_text(encoding="utf-8"))
    assert expected == committed, (
        "supabase/functions/admin-scenario-data/meta.json is stale. "
        f"Run `{UPDATE_COMMAND}` and commit the result."
    )


def test_committed_snapshot_covers_every_pair():
    """The snapshot is the whole set, not a truncated one."""
    pairs = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(OUT_DIR.glob("scenario_pairs.*.json"))
    ]

    assert len(pairs) == generator.EXPECTED_PAIR_COUNT

    counts: dict[str, int] = {}
    for pair in pairs:
        counts[pair["category"]] = counts.get(pair["category"], 0) + 1
    assert counts == generator.EXPECTED_CATEGORY_COUNTS

    pair_ids = [pair["pair_id"] for pair in pairs]
    assert len(set(pair_ids)) == len(pair_ids), "duplicate pair_id in the snapshot"
