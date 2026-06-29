# Changelog

## [2026-06-29] Phase 1 methodology fixes

### Fixed
- **Control conditions now differ (Flaw A).** `build_messages` injects the structured
  payment policy per condition: none for `no_policy`, natural-language for `prompt_policy`,
  natural-language + an enforcement note for `tool_constraints` (reusing the shared
  `render_policy_text`). Previously the three conditions shared a byte-identical prompt and
  the policy was never shown to the model.
- **`tool_constraints` enforces the action, not the answer key (Flaw B).** `apply_tool_constraints`
  now blocks only when the model's proposed action actually violates a hard limit
  (via `collect_policy_failures`), instead of blocking every payment on a labelled trap.
  This removes the manufactured false refusals on the b1–b5 authorization traps.

### Changed
- Moved `render_policy_text` / `structured_policy_json` / `PROMPTABLE_POLICY_FIELDS` from
  `app/phase2/sandbox.py` to a shared `app/policy_text.py` so Phase 1 can reuse them without
  importing Phase 2.

### Known limitation (unchanged, documented)
- Phase 1 still grades the model's self-reported action fields, so for the 11 `safe_to_act=True`
  traps a model can take the unsafe action yet report neutral fields and score "safe."
  Removing this requires authored per-scenario world data; the Phase 2 sandbox
  (`phase2-eval`) is the offer-grounded path that does not rely on self-report.

### Files
- `app/providers.py`, `app/policies.py`, `app/policy_text.py` (new), `app/phase2/sandbox.py`
  (imports only), `README.md`, `COMMANDS.md`, tests under `tests/`.
