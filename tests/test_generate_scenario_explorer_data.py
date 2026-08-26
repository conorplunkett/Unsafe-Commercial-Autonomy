"""The scenario-explorer data snapshot must stay complete and stable."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_CATEGORY_COUNTS = {
    "spend_limits": 25,
    "authorization_scope": 14,
    "consent_and_escalation": 24,
    "privacy_and_disclosure": 25,
    "adversarial_robustness": 25,
}


def _load_generator():
    path = ROOT / "scripts" / "generate_scenario_explorer_data.py"
    spec = importlib.util.spec_from_file_location("generate_scenario_explorer_data", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = _load_generator()


def test_build_pairs_has_113_complete_pairs():
    pairs = gen.build_pairs()

    assert len(pairs) == 113
    for pair in pairs:
        assert pair["trap"]["pair_role"] == "trap"
        assert pair["lookalike"]["pair_role"] == "lookalike"
        assert pair["trap"]["pair_id"] == pair["pair_id"]
        assert pair["lookalike"]["pair_id"] == pair["pair_id"]
        for scenario in (pair["trap"], pair["lookalike"]):
            for offer in scenario["environment"]["sandbox"]["offers"]:
                assert offer["page_url"].startswith("https://")

    counts = {}
    for pair in pairs:
        counts[pair["category"]] = counts.get(pair["category"], 0) + 1
    assert counts == EXPECTED_CATEGORY_COUNTS


def test_pair_records_carry_the_enforcement_scope_projection():
    """Each side's `enforcement` block comes from the committed scope
    projection, not a second computation -- see
    data/answer_keys/phase2_enforcement_scope.json."""
    import json

    scope = json.loads((ROOT / "data" / "answer_keys" / "phase2_enforcement_scope.json").read_text())
    pairs = gen.build_pairs()
    by_id = {}
    for pair in pairs:
        by_id[pair["trap"]["scenario_id"]] = pair["trap"]
        by_id[pair["lookalike"]["scenario_id"]] = pair["lookalike"]

    for scenario_id, record in by_id.items():
        expected = scope["scenarios"][scenario_id]
        assert record["enforcement"] == {field: expected[field] for field in gen.ENFORCEMENT_FIELDS}

    assert by_id["scn_v2_a1_trap"]["enforcement"]["rail_reachable"] is True
    assert by_id["scn_v2_a1_trap"]["enforcement"]["in_enforced_arm"] is True
    assert by_id["scn_v2_a1_lookalike"]["enforcement"]["rail_reachable"] is False
    assert by_id["scn_v2_a1_lookalike"]["enforcement"]["in_enforced_arm"] is True
    assert by_id["scn_v2_c10_trap"]["enforcement"]["in_enforced_arm"] is False


def test_content_hash_is_present_and_deterministic():
    """Every scenario record carries a content_hash, and re-running the
    generator against the same source data reproduces it exactly -- otherwise
    an unchanged scenario would spuriously read as edited."""
    pairs = gen.build_pairs()
    again = gen.build_pairs()

    for pair, pair_again in zip(pairs, again):
        for role in ("trap", "lookalike"):
            record, record_again = pair[role], pair_again[role]
            content_hash = record["content_hash"]
            assert isinstance(content_hash, str) and content_hash
            assert content_hash == record_again["content_hash"]


def test_content_hash_changes_when_any_field_changes():
    """A hash computed on a scenario record must change if any field --
    answer key, page text, whatever -- changes, since this is what the
    Scenario Explorer compares against a stored review to detect an edit."""
    pairs = gen.build_pairs()
    trap = pairs[0]["trap"]

    edited_text = json.loads(json.dumps(trap))
    edited_text["title"] = edited_text["title"] + " (edited)"
    assert gen.compute_content_hash(edited_text) != gen.compute_content_hash(trap)

    edited_key = json.loads(json.dumps(trap))
    edited_key["right_answer"] = "a different answer"
    assert gen.compute_content_hash(edited_key) != gen.compute_content_hash(trap)

    assert gen.compute_content_hash(trap) == gen.compute_content_hash(
        json.loads(json.dumps(trap))
    )


def test_pair_order_matches_first_seen_loader_order():
    from app.data import load_scenarios
    from app.models import model_to_dict
    from app.phase2 import PHASE2_SCENARIO_SET

    records = [model_to_dict(s) for s in load_scenarios(PHASE2_SCENARIO_SET)]
    expected_order = []
    for record in records:
        if record["pair_id"] not in expected_order:
            expected_order.append(record["pair_id"])

    pairs = gen.build_pairs()
    assert [p["pair_id"] for p in pairs] == expected_order


def _read_pair_files(out_dir):
    paths = sorted(out_dir.glob("scenario_pairs.*.json"))
    return paths, [json.loads(p.read_text(encoding="utf-8")) for p in paths]


def test_each_pair_file_is_named_by_the_pair_it_contains(tmp_path):
    pairs = gen.build_pairs()
    written = gen.write_pair_files(pairs, tmp_path)

    assert [p.name for p in written] == [gen.pair_filename(p["pair_id"]) for p in pairs]
    for pair, path in zip(pairs, written):
        assert json.loads(path.read_text(encoding="utf-8")) == pair


def test_pair_files_stay_under_a_safe_relay_size(tmp_path):
    gen.main(out_dir=tmp_path)
    paths, _ = _read_pair_files(tmp_path)

    assert len(paths) == 113  # actually split, not one big file
    for path in paths:
        assert path.stat().st_size < 25_000


def test_main_output_is_idempotent(tmp_path):
    gen.main(out_dir=tmp_path)
    first = {
        p.name: p.read_text(encoding="utf-8") for p in sorted(tmp_path.glob("*.json"))
    }

    gen.main(out_dir=tmp_path)
    second = {
        p.name: p.read_text(encoding="utf-8") for p in sorted(tmp_path.glob("*.json"))
    }

    assert first == second
    _, all_pairs = _read_pair_files(tmp_path)
    assert len(all_pairs) == 113
    counts = {}
    for pair in all_pairs:
        counts[pair["category"]] = counts.get(pair["category"], 0) + 1
    assert counts == EXPECTED_CATEGORY_COUNTS


def test_editing_one_pair_changes_exactly_one_file(tmp_path):
    """The whole point of identity-named files: a single scenario edit must
    diff as a single pair file, never re-flow neighbours into other files."""
    pairs = gen.build_pairs()
    before_dir, after_dir = tmp_path / "before", tmp_path / "after"
    gen.write_pair_files(pairs, before_dir)

    edited = json.loads(json.dumps(pairs))
    edited[40]["trap"]["title"] += " (edited)"
    gen.write_pair_files(edited, after_dir)

    before = {p.name: p.read_text() for p in before_dir.glob("*.json")}
    after = {p.name: p.read_text() for p in after_dir.glob("*.json")}
    assert set(before) == set(after)
    changed = [name for name in before if before[name] != after[name]]
    assert changed == [gen.pair_filename(pairs[40]["pair_id"])]


def test_removed_pair_leaves_no_stale_file(tmp_path):
    gen.main(out_dir=tmp_path)
    pairs = gen.build_pairs()
    dropped = pairs.pop()
    gen.write_pair_files(pairs, tmp_path)

    names = set(p.name for p in tmp_path.glob("*.json"))
    assert gen.pair_filename(dropped["pair_id"]) not in names
    assert names == {gen.pair_filename(p["pair_id"]) for p in pairs}


def test_sync_index_imports_updates_imports_and_entries(tmp_path):
    index_path = tmp_path / "index.ts"
    index_path.write_text(
        'before\nimport pair_v2_a1 from "./scenario_pairs.v2_a1.json" with { type: "json" };\n\n'
        "const SCENARIO_PAIRS = [\n  pair_v2_a1\n];\nafter\n"
    )
    pairs = [{"pair_id": pair_id} for pair_id in ("v2_a1", "v2_a2", "v2_b3")]

    gen.sync_index_imports(index_path, pairs)

    result = index_path.read_text()
    assert 'import pair_v2_b3 from "./scenario_pairs.v2_b3.json"' in result
    assert "  pair_v2_b3\n" in result
    assert result.startswith("before\n") and result.endswith("after\n")
