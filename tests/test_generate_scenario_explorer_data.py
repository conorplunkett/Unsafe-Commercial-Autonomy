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


def test_main_output_is_idempotent(tmp_path):
    out_path = tmp_path / "scenario_pairs.json"

    gen.main(out_path=out_path)
    first = out_path.read_text(encoding="utf-8")

    gen.main(out_path=out_path)
    second = out_path.read_text(encoding="utf-8")

    assert first == second
    payload = json.loads(second)
    assert payload["count"] == 113
    assert len(payload["pairs"]) == 113
