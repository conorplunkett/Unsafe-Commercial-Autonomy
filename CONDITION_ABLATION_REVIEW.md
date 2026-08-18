# Phase 2 control-condition review

> [!IMPORTANT]
> **Superseded August 17, 2026.** This historical review recommends the former
> four-condition design. The current Phase 2 grid uses `no_policy`,
> `structured_policy`, and `tool_constraints` only; see `README.md`. The review
> below is preserved unchanged as the rationale for the earlier decision.

## Recommendation

If the Phase 2 grid must lose two conditions, keep:

1. `no_policy`
2. `structured_policy`
3. `required_check` (named `preflight_check` until 2026-08-09; renamed because
   "preflight" also names the live-eval API smoke test, and the condition's
   defining trait is a mandatory check with an advisory verdict)
4. `tool_constraints`

Phase 2 now removes `prompt_policy` and `approval_gate` entirely. Phase 1 keeps
its existing `prompt_policy` condition; this decision changes only the Phase 2
sandbox and its supporting interfaces.

The proposed alternative—cutting `structured_policy` and `tool_constraints`—
would remove the clean baseline for the enforced conditions and the benchmark's
only conventional hard backstop. It would leave four conditions, but not a
coherent four-step mechanism comparison.

## What each contrast identifies

| Contrast | Question it can answer |
| --- | --- |
| `no_policy` → `structured_policy` | Does exposing the policy change the agent's choice? |
| `structured_policy` → `required_check` | Does a required check change behavior when its verdict remains advisory? |
| `structured_policy` → `tool_constraints` | What does actual hard enforcement add over showing the same structured policy? |
| `prompt_policy` → `structured_policy` | Does prose versus JSON presentation matter? |
| `tool_constraints` → `approval_gate` | Does a terminal pause differ from a recoverable block? |

The first three contrasts form the strongest primary ladder: no policy
information, policy information without enforcement, a mandatory procedure,
and hard enforcement. The last two are narrower representation and response
semantics ablations.

## Why `structured_policy` should stay

`structured_policy` is not valuable mainly because JSON might outperform prose.
It is valuable because it is the no-enforcement comparator for every structured
mechanism above it. The prompt shown under `structured_policy`,
`required_check`, and `tool_constraints` contains the same machine-readable
policy. Removing it means a comparison between prompt-only policy and hard
constraints changes policy representation, tool availability, instructions,
and enforcement at once.

If prose-versus-JSON is not a central research question, `prompt_policy` is the
condition to remove. The Phase 1 study already retains the prompt-only condition,
so that question is not lost from the project altogether.

## Why `tool_constraints` should stay

`tool_constraints` is the only condition that tests a normal technical
backstop while still allowing the episode to continue after a rejected payment.
That recovery path matters to the stated safety-autonomy frontier: after a bad
attempt, the agent can choose a compliant offer rather than simply stop.

The condition also supplies the direct comparison against
`structured_policy`: identical policy representation, with hard enforcement
added. Cutting it would leave the study without its clearest measurement of the
incremental value and autonomy cost of enforceable controls.

## Why `approval_gate` is the weaker primary condition

The removed gate and `tool_constraints` used the same policy evaluator and the
same trigger. Their difference happens only after a violation is detected:

- `tool_constraints` returns `blocked` and lets the agent recover;
- `approval_gate` returns `pending_approval`, immediately ends the episode, and
  is assembled as an `ask_approval` action.

That was a real implementation difference, but the gate was not a
simulation of explicit human approval. No human approves or denies the payment,
and the agent cannot recover after the pause. The contrast therefore mixes the
label shown to the model, terminal versus nonterminal tool behavior, and scoring
semantics. A result would not isolate the effect of human oversight.

This condition would become worth restoring if the sandbox modeled
the human response explicitly—for example approve, deny, or request a revised
purchase—and permits the agent to continue after denial. Until then, it is best
treated as a secondary intervention-semantics ablation.

## What `required_check` actually measures

`required_check` is a procedural gate. Before paying a particular offer, the
agent must call `check_policy` for that offer. An unchecked payment is rejected
whether the offer is compliant or not. Once the check has happened, payment can
proceed even when the check returned `block`.

It therefore exposes two observable behaviors:

1. **Procedure compliance:** whether the agent calls the required tool before
   payment.
2. **Verdict adherence:** whether the agent heeds an advisory block after it has
   satisfied the procedure.

It is distinct from hard constraints, but it is not a pure one-variable
intervention. Relative to `structured_policy`, it adds a tool, a mandatory-use
instruction, and a pay-time rejection rule. Results should report procedure
compliance and verdict adherence separately rather than interpret the condition
only through the headline unsafe-payment and false-refusal rates.

If the primary research question is narrowed strictly to the safety-autonomy
frontier, `required_check` is the next condition to demote after
`approval_gate`; it measures workflow obedience more directly than control
effectiveness. If procedural discipline remains a research question, it earns
its place in the four-condition grid.

## Design claims to tighten before publication

The original six conditions were mutually exclusive levels of one categorical
axis, not a factorial design. They could estimate pairwise condition contrasts,
but not an interaction such as “tool constraints plus approval” because there
was no combined `tool_constraints + approval_gate` cell. The four-condition
design no longer makes that interaction claim.

Similarly, “varying one layer at a time” is accurate only for selected
comparisons. In particular, `structured_policy` is the necessary anchor that
makes the hard-enforcement comparison close to a one-layer change.

## Decision summary

- **Right:** cut two conditions to reduce cost and simplify interpretation.
- **Right:** question whether `structured_policy` earns a cell solely as a
  format test.
- **Wrong condition to cut:** retain `structured_policy` as the common
  no-enforcement anchor; cut `prompt_policy`, the actual format-only ablation.
- **Wrong condition to cut:** retain `tool_constraints`, the cleanest and most
  operationally relevant enforced control.
- **Best second cut:** `approval_gate`, because its present implementation is a
  terminal hard block labeled as human review, not a completed human-in-the-loop
  flow.
- **Keep with a reporting caveat:** `required_check`, provided procedure
  compliance and response to the verdict are reported as separate outcomes.
