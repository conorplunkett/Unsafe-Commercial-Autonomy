"""The Lab's FAILURE_META is mirrored from FAILURE_LABELS by hand.

static/lab.js declares "Kept in sync by hand — the backend list is the source
of truth", but nothing enforced it: over_refusal_axis (and the 2026-08
gate/fabricate labels) drifted silently until the 2026-08-26 review. This pins
the invariant: every backend failure label renders with a curated short label
in the Lab, never the de-underscored fallback.
"""

import re
from pathlib import Path

from app.policies import FAILURE_LABELS

LAB_JS = Path(__file__).resolve().parents[1] / "static" / "lab.js"


def _failure_meta_keys() -> set:
    source = LAB_JS.read_text(encoding="utf-8")
    match = re.search(r"const FAILURE_META = \{(.*?)\n\};", source, re.DOTALL)
    assert match, "FAILURE_META block not found in static/lab.js"
    return set(re.findall(r"^\s*([a-z_]+):\s*\[", match.group(1), re.MULTILINE))


def test_lab_failure_meta_covers_every_backend_failure_label():
    missing = set(FAILURE_LABELS) - _failure_meta_keys()
    assert not missing, (
        f"static/lab.js FAILURE_META is missing backend failure codes: {sorted(missing)} "
        "— add them (short label + full sentence) to keep the hand-mirrored map honest"
    )
