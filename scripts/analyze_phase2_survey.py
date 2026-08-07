"""Score the Phase 2 web survey export against the pre-registered rules.

Reads a raw response export (the JSON array downloaded from the admin
dashboard / Supabase — it contains PII and must NEVER be committed) and
writes the anonymized artifacts that are committed:

- ``data/survey/phase2_results_v2_web_r3.json``
- ``data/survey/phase2_survey_responses.json`` (answer-key votes, slot keys)

Run: ``python scripts/analyze_phase2_survey.py <raw_export.json>``
(optionally ``--out``/``--votes-out`` to override the output paths).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.phase2.web_survey import main

if __name__ == "__main__":
    raise SystemExit(main())
