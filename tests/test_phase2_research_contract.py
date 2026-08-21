"""The Phase 2 instrument and answer keys may only change deliberately."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, List

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "data" / "answer_keys" / "phase2_research_contract.json"
UPDATE_COMMAND = "python scripts/freeze_phase2_research_contract.py"


def _load_generator():
    path = ROOT / "scripts" / "freeze_phase2_research_contract.py"
    spec = importlib.util.spec_from_file_location("freeze_phase2_research_contract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generator = _load_generator()


def _differences(expected: Any, actual: Any, path: str = "root") -> List[str]:
    if type(expected) is not type(actual):
        return [
            f"{path}: type changed from {type(expected).__name__} "
            f"to {type(actual).__name__}"
        ]
    if isinstance(expected, dict):
        differences: List[str] = []
        expected_keys = set(expected)
        actual_keys = set(actual)
        for key in sorted(expected_keys - actual_keys):
            differences.append(f"{path}.{key}: removed")
        for key in sorted(actual_keys - expected_keys):
            differences.append(f"{path}.{key}: added")
        for key in sorted(expected_keys & actual_keys):
            differences.extend(_differences(expected[key], actual[key], f"{path}.{key}"))
        return differences
    if isinstance(expected, list):
        differences = []
        if len(expected) != len(actual):
            differences.append(f"{path}: length changed from {len(expected)} to {len(actual)}")
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            differences.extend(
                _differences(expected_item, actual_item, f"{path}[{index}]")
            )
        return differences
    if expected != actual:
        return [f"{path}: {expected!r} -> {actual!r}"]
    return []


def test_phase2_research_contract_has_not_drifted():
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    actual = generator.build_projection()
    differences = _differences(expected, actual)

    assert not differences, (
        "Phase 2 research contract drifted:\n"
        + "\n".join(f"- {difference}" for difference in differences[:25])
        + (f"\n- ... and {len(differences) - 25} more" if len(differences) > 25 else "")
        + f"\nIf intentional, run `{UPDATE_COMMAND}` and review the generated diff."
    )


def test_projection_scope_excludes_mutable_sandbox_content():
    projection = generator.build_projection()

    assert len(projection["authored_keys"]) == 226
    assert len(projection["effective_keys"]) == 226
    assert set(next(iter(projection["authored_keys"].values()))) == set(
        generator.AUTHORED_KEY_FIELDS
    )
    assert set(next(iter(projection["effective_keys"].values()))) == set(
        generator.EFFECTIVE_KEY_FIELDS
    )
    assert projection["_meta"]["not_protected"] == [
        "sandbox environments",
        "merchant and page copy",
        "offers and cart state",
        "checkout controls and tool implementation",
    ]
