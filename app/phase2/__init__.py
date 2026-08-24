"""Phase 2: sandbox benchmark with three-condition control ablation.

Never imported by Phase 1 modules; app/cli.py imports it lazily inside the
phase2-* command handlers only.
"""

from .checkpoint import (  # noqa: F401
    CheckpointMismatch,
    CheckpointMissing,
    CheckpointStore,
    list_checkpoints,
)
from .runner import (  # noqa: F401
    DEFAULT_PHASE2_SEEDS,
    PHASE2_SCENARIO_SET,
    run_phase2_evaluation,
)
from .sandbox import FRAMINGS, PHASE2_CONTROL_CONDITIONS, rail_reachable  # noqa: F401
from .scope import (  # noqa: F401
    DEFAULT_ENFORCEMENT_SCOPE,
    ENFORCED_CONDITIONS,
    ENFORCEMENT_SCOPES,
    enforcement_scope_ids,
    scenarios_by_condition,
)
