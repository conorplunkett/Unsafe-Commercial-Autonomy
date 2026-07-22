"""Auto-load `.env` so runs need no manual `export` ritual.

The CLI and the FastAPI app call :func:`load_env_file` at startup, so keys kept
in the repo-root `.env` (gitignored) are available without sourcing anything.
Real environment variables always win over the file, and the test suite sets
``PAYBENCH_SKIP_DOTENV=1`` (see tests/conftest.py) so tests stay hermetic no
matter what a developer keeps in their local `.env`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = ROOT_DIR / ".env"


def load_env_file(path: Optional[Path] = None) -> Dict[str, str]:
    """Load ``KEY=VALUE`` lines from `.env` into ``os.environ``.

    - Variables already set in the environment are never overwritten, so a
      per-shell ``export`` still overrides the file.
    - Blank lines, ``#`` comments, and an optional ``export `` prefix are
      accepted; surrounding single/double quotes on values are stripped.
    - Returns the variables that were actually applied (useful for tests).
    """
    if os.environ.get("PAYBENCH_SKIP_DOTENV"):
        return {}
    env_path = path or DEFAULT_ENV_PATH
    if not env_path.is_file():
        return {}

    applied: Dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        # Skip blanks too: an unfilled `KEY=` template line (as shipped in
        # .env.example) must read as "unset", not as an empty-string value.
        if not key or not value or key in os.environ:
            continue
        os.environ[key] = value
        applied[key] = value
    return applied
