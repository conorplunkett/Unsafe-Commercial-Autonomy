"""Score the Phase 1 web survey export against the pre-registered rules.

Reads a raw response export (the JSON downloaded from the admin dashboard /
Supabase — it contains PII and must NEVER be committed) and writes the
anonymized aggregates that are committed:

- ``data/survey/phase1_results_v1_web_r6.json``
- ``web/lib/surveyResults.ts`` (generated module for the public results page)

Run: ``python scripts/analyze_phase1_survey.py <raw_export.json>``
(optionally ``--out``/``--web-out`` to override the output paths).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.phase1_web_survey import main

if __name__ == "__main__":
    raise SystemExit(main())
