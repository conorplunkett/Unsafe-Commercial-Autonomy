"""The v2 constraints generator must never overwrite manual edits."""
import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_JSON = ROOT / "data" / "answer_keys" / "v2_constraints.json"


def _load_generator():
    path = ROOT / "scripts" / "generate_v2_constraints.py"
    spec = importlib.util.spec_from_file_location("generate_v2_constraints", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = _load_generator()


def test_merge_preserving_keeps_existing_values():
    existing = {"a": 1, "nested": {"x": 10}, "offers": [{"total": 42.0}]}
    generated = {"a": 999, "b": 2, "nested": {"x": 999, "y": 20}, "offers": [{"total": 1.0}]}

    merged = gen._merge_preserving(existing, generated)

    assert merged["a"] == 1  # existing scalar wins
    assert merged["b"] == 2  # missing key filled from generated
    assert merged["nested"] == {"x": 10, "y": 20}  # deep-merge, existing leaf wins
    assert merged["offers"] == [{"total": 42.0}]  # existing list preserved atomically
    # A brand-new entry (no existing) takes the generated value as-is.
    assert gen._merge_preserving(None, {"k": 1}) == {"k": 1}


def test_generator_never_overwrites_manual_offer_edits(tmp_path):
    work = tmp_path / "v2_constraints.json"
    shutil.copy(SRC_JSON, work)
    data = json.loads(work.read_text())
    data["scn_v2_a1_trap"]["environment"]["offers"][0]["total"] = 4242.42
    data["scn_v2_a1_trap"]["max_total_spend"] = 9999.0
    work.write_text(json.dumps(data, indent=2) + "\n")

    gen.main(out_path=work)

    after = json.loads(work.read_text())
    assert after["scn_v2_a1_trap"]["environment"]["offers"][0]["total"] == 4242.42
    assert after["scn_v2_a1_trap"]["max_total_spend"] == 9999.0


def test_generator_run_is_idempotent_on_scenario_data(tmp_path):
    work = tmp_path / "v2_constraints.json"
    shutil.copy(SRC_JSON, work)
    before = json.loads(work.read_text())

    gen.main(out_path=work)

    after = json.loads(work.read_text())
    # Every scenario entry (everything but the generator's own _meta) is untouched.
    before.pop("_meta", None)
    after.pop("_meta", None)
    assert after == before


def test_generator_fails_loudly_on_a_deleted_environment_with_no_spec(tmp_path):
    # All 226 v2 scenarios are already scaffolded and all five *_SPECS dicts
    # are now empty (2026-08-19; see the module docstring) -- there is no spec
    # left that could regenerate a1's environment if it went missing, so the
    # generator must say so loudly (`main`'s `missing` check) rather than
    # silently writing back a broken/incomplete entry.
    work = tmp_path / "v2_constraints.json"
    shutil.copy(SRC_JSON, work)
    data = json.loads(work.read_text())
    del data["scn_v2_a1_trap"]["environment"]
    work.write_text(json.dumps(data, indent=2) + "\n")

    try:
        gen.main(out_path=work)
        assert False, "expected SystemExit: no spec exists to regenerate a1 from"
    except SystemExit as exc:
        assert "scn_v2_a1_trap" in str(exc)
