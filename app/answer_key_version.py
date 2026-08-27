"""A content hash of the Phase 2 scoring key, for spotting stale runs.

A stored run records the answer-key version it was scored against. When the
effective keys later change (an authored key edit, or an adopted survey re-key),
the current version no longer matches what an old run carries, so the Lab can
mark that run outdated instead of silently comparing numbers scored against a
key that has since moved.

The version is a sha256 over the frozen projection's `effective_keys` block in
`data/answer_keys/phase2_research_contract.json` — the committed source of truth
for what each scenario is actually scored against (see AGENTS.md, "Sources of
truth"). That file is regenerated (and its drift test forces the regeneration)
whenever the effective keys change, so its hash moves exactly when the scoring
key moves. Sandbox world state lives outside the projection on purpose, so
merchant/offer/tool edits never spuriously mark a run outdated.

The hash is not cached: the file is tiny (226 scenarios) and both callers are
infrequent (once per run at save time; once per Lab refresh), while a cache
would hide a mid-session re-freeze from a long-running Lab server — the exact
change this module exists to surface.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .data import ROOT_DIR

CONTRACT_PATH = ROOT_DIR / "data" / "answer_keys" / "phase2_research_contract.json"


def _hash_effective_keys(effective_keys: Any) -> str:
    # sort_keys makes the digest independent of dict insertion order, so the
    # version tracks the key content and nothing else.
    canonical = json.dumps(effective_keys, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def phase2_answer_key_version() -> str:
    """The current Phase 2 scoring-key version (short sha256 prefix)."""
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return _hash_effective_keys(contract["effective_keys"])[:16]
