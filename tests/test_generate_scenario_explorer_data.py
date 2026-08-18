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

    counts = {}
    for pair in pairs:
        counts[pair["category"]] = counts.get(pair["category"], 0) + 1
    assert counts == EXPECTED_CATEGORY_COUNTS


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


def _read_chunks(out_dir):
    paths = sorted(out_dir.glob("scenario_pairs.*.json"))
    chunks = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    for chunk in chunks:
        assert 1 <= len(chunk)
    return paths, chunks


def test_pack_chunks_never_exceeds_the_size_budget_by_much():
    pairs = gen.build_pairs()
    chunks = gen.pack_chunks(pairs, gen.CHUNK_SIZE_BUDGET)

    assert sum(len(c) for c in chunks) == len(pairs)
    for chunk in chunks:
        size = len(json.dumps(chunk, indent=2))
        # A lone pair bigger than the budget still gets its own chunk (never
        # split mid-pair), so allow some slack over the nominal budget --
        # this asserts the packing is actually doing its job, not that every
        # chunk is under the budget no matter what.
        assert size < gen.CHUNK_SIZE_BUDGET * 2


def test_chunk_files_stay_under_a_safe_relay_size(tmp_path):
    gen.main(out_dir=tmp_path)
    paths, _ = _read_chunks(tmp_path)

    assert len(paths) > 1  # actually split, not one big file
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
    _, chunks = _read_chunks(tmp_path)
    all_pairs = [pair for chunk in chunks for pair in chunk]
    assert len(all_pairs) == 113
    counts = {}
    for pair in all_pairs:
        counts[pair["category"]] = counts.get(pair["category"], 0) + 1
    assert counts == EXPECTED_CATEGORY_COUNTS


def test_chunk_files_concatenate_to_build_pairs_order(tmp_path):
    gen.main(out_dir=tmp_path)
    _, chunks = _read_chunks(tmp_path)

    concatenated = [pair["pair_id"] for chunk in chunks for pair in chunk]
    assert concatenated == [p["pair_id"] for p in gen.build_pairs()]


def test_shrinking_chunk_count_removes_stale_files(tmp_path, monkeypatch):
    gen.main(out_dir=tmp_path)
    before = set(p.name for p in tmp_path.glob("*.json"))
    assert len(before) > 5

    monkeypatch.setattr(gen, "CHUNK_SIZE_BUDGET", 10_000_000)  # collapses to one chunk
    gen.main(out_dir=tmp_path)
    after = set(p.name for p in tmp_path.glob("*.json"))

    assert after == {gen.chunk_filename(0)}
    assert before - after  # the old, now-stale chunk files were deleted
