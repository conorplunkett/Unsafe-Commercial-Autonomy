"""Phase 2: sandbox benchmark with six-condition control ablation.

Never imported by Phase 1 modules; app/cli.py imports it lazily inside the
phase2-* command handlers only.
"""

from .runner import (  # noqa: F401
    DEFAULT_PHASE2_SEEDS,
    PHASE2_SCENARIO_SET,
    run_phase2_evaluation,
)
from .sandbox import FRAMINGS, PHASE2_CONTROL_CONDITIONS  # noqa: F401
