import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Isolate run storage so the test suite never writes BenchmarkRun JSON files
# into the shared runtime/runs/ directory that the live app and CLI read from.
# This must happen before any `app.*` module is imported, since app.main binds
# a module-level RunStorage() at import time.
_RUN_STORAGE_TMPDIR = tempfile.mkdtemp(prefix="uca-test-runs-")
os.environ.setdefault("RUN_STORAGE_DIR", _RUN_STORAGE_TMPDIR)

