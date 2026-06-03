from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .models import Scenario, parse_model


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_scenarios(path: Optional[Path] = None) -> List[Scenario]:
    raw_scenarios = load_json(path or DATA_DIR / "scenarios.json")
    return [parse_model(Scenario, item) for item in raw_scenarios]


def load_catalog(path: Optional[Path] = None) -> Dict:
    return load_json(path or DATA_DIR / "catalog.json")


def get_scenario(scenario_id: str, scenarios: Optional[List[Scenario]] = None) -> Scenario:
    for scenario in scenarios or load_scenarios():
        if scenario.scenario_id == scenario_id:
            return scenario
    raise KeyError(f"Scenario {scenario_id} not found")


def search_catalog(query: str, catalog: Optional[Dict] = None) -> List[Dict]:
    normalized = query.lower().strip()
    results: List[Dict] = []
    for merchant_id, merchant_data in (catalog or load_catalog()).get("merchants", {}).items():
        for product in merchant_data.get("inventory", []):
            if normalized in product.get("name", "").lower():
                results.append(
                    {
                        "merchant_id": merchant_id,
                        "merchant_name": merchant_data.get("name", merchant_id),
                        "merchant_trusted": merchant_data.get("trusted", False),
                        **product,
                    }
                )
    return results

