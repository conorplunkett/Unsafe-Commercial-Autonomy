"""Stamp existing Phase 2 run files with the current answer-key version.

Runs saved before `answer_key_version` existed carry no version, so the Lab
reads them as "not tracked" and never flags them outdated -- even after the key
later moves. This one-time backfill assumes those runs were scored against the
key as it stands now (i.e. "the runs ran today are stamped for today"), so from
here on a real key change flags them like any freshly stamped run.

Run from the repository root:

    python scripts/backfill_answer_key_version.py            # dry run, lists what would change
    python scripts/backfill_answer_key_version.py --write    # actually stamp them

Only Phase 2 runs missing a version are touched; Phase 1 runs and runs that
already carry a version are left alone. Set RUN_STORAGE_DIR to point at a
non-default run directory.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.answer_key_version import phase2_answer_key_version  # noqa: E402
from app.storage import RunStorage  # noqa: E402


def main(write: bool) -> None:
    version = phase2_answer_key_version()
    root = RunStorage().root
    run_files = sorted(p for p in root.glob("*.json"))
    stamped = 0
    for path in run_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("phase") != "phase2":
            continue
        if payload.get("answer_key_version"):
            continue
        stamped += 1
        print(f"{'stamping' if write else 'would stamp'} {path.name} -> {version}")
        if write:
            payload["answer_key_version"] = version
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    verb = "Stamped" if write else "Would stamp"
    print(f"{verb} {stamped} Phase 2 run(s) with answer-key version {version}.")
    if stamped and not write:
        print("Re-run with --write to apply.")


if __name__ == "__main__":
    main(write="--write" in sys.argv[1:])
