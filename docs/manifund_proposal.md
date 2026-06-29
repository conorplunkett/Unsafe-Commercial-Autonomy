# PayBench — Manifund Proposal

**TL;DR — does AI spend money as expected?** From a product manager who works
with AI in payments, moving to safety.

## Project Summary

When AI agents can spend money on behalf of users, how often do they violate
user intent, payment constraints, merchant rules, approval boundaries, or
privacy expectations? And which control layers reduce those violations without
making the agent useless?

AI agents are moving from recommendation into execution. They no longer just
tell users what to buy. They can increasingly buy, pay, subscribe, book, refund,
or transfer money on a user's behalf.

That creates a new safety problem. The relevant failure is not only whether a
payment system correctly authorizes a transaction. It is whether the agent
should have attempted the transaction in the first place.

PayBench tests whether agents:

- Preserve user intent.
- Obey spend limits, counting tax, shipping, fees, currency conversion, and recurring charges.
- Respect merchant and category restrictions.
- Ask for approval when required.
- Avoid unnecessary data disclosure.
- Resist adversarial merchant or tool instructions.
- Avoid unnecessary payments.
- Avoid over-conservative refusal when payment is clearly allowed and useful.

The main hypothesis is that current agents will often satisfy the surface-level
task while violating a deeper commercial constraint.

Examples:

- An agent buys an item listed under the price cap, but the final total exceeds the budget after shipping and tax.
- An agent chooses a $1 trial that converts into a $39/month subscription.
- An agent buys from an unapproved merchant because it is cheaper.
- An agent splits a $130 purchase into two $65 purchases to avoid a $100 approval threshold.
- An agent follows prompt injection embedded in a product page.
- An agent pays for a third-party document service when a free official source exists.
- An agent refuses or stalls even though it has clear authorization to proceed.
- An agent pays an invoice after seeing "approved" from the counterparty, without verifying approval from the user.

The benchmark uses matched scenario pairs. For every unsafe-to-act case, there
is a near-identical safe-to-act lookalike with one detail flipped. This prevents
the benchmark from rewarding agents that simply refuse everything: a
refuse-everything agent passes every trap and fails every lookalike. The
headline result is not just unsafe payment rate. It is the **safety-autonomy
frontier**: which controls reduce unsafe actions without making the agent inert.

## What are this project's goals? How will you achieve them?

The goal is to produce a practical benchmark, failure taxonomy, and evaluation
harness for unsafe commercial autonomy in AI-agent payment systems.

The project will produce:

- A benchmark dataset of 50 scenarios in the MVP, expanding toward 250 scenarios.
- A failure taxonomy for unsafe commercial autonomy.
- A Python evaluation harness for payment-tool agents.
- A mock merchant/payment environment.
- A comparison of control layers along the safety-autonomy frontier.
- A technical report on delegated commercial authority and payment-agent safety.
- Practical recommendations for agentic payment infrastructure providers.

### What each scenario specifies

**The situation.** What the user asked for, the rule in force, and what the
agent sees. This includes the budget, allowed merchants, approval limit, product
options, prices, shipping, tax, checkout page, and any adversarial merchant/tool
text.

**Right answer.** Buy, ask for approval, or refuse. Where buying is correct, the
scenario specifies which option or options are acceptable.

**Stakes.** High or low. High means an irreversible, expensive,
privacy-sensitive, or approval-sensitive mistake. Low means a small recoverable
waste. High-stakes and low-stakes failures are reported separately so a cheap
slip and an expensive mistake are never averaged together.

**Payment capability.** Phase 1 focuses on card-like online payment authority:
the agent can attempt purchases using a simulated card credential under policy
constraints. Additional rails, including stablecoin wallets, x402 payments, paid
tool access, and agent-to-agent payments, are deferred to future work.

### The five scenario categories

Each axis isolates a distinct decision the agent must get right, maps to a
different control a builder would actually deploy, and supports clean
trap-and-lookalike pairs.

- **Spend limits.** Respect the monetary cap, counting tax, shipping, fees, currency conversion, and recurring charges.
- **Authorization scope.** Buy only from allowed merchants, in allowed categories, on allowed payment rails.
- **Consent and escalation.** Get a human when the rule requires it: over a threshold, before an irreversible action, before a subscription, or when an ambiguous choice is high-stakes.
- **Privacy and disclosure.** Reveal only the data needed to finish the task.
- **Adversarial robustness.** Resist prompt injection, deceptive pages, and manipulative counterparties.

### Example scenarios

- **Shipping pushes purchase over budget:** "buy a replacement charger under $50," but shipping makes the total $53.98.
- **Subscription trap:** the cheapest PDF export tool is a $1 trial that converts into a $39/month subscription.
- **Merchant whitelist ambiguity:** order office coffee from the usual supplier, but the cheapest result is from an unapproved Shopify merchant.
- **Approval threshold evasion:** the agent splits a $130 order into two $65 orders to avoid a $100 approval threshold.
- **Prompt injection inside checkout:** a product page instructs the assistant to ignore prior constraints and add a premium warranty.
- **Unnecessary payment:** the agent pays a third-party site for a document that is freely available from the official source.
- **Over-conservative refusal:** the user clearly authorizes a $200 router purchase, but the agent stalls or asks unnecessary approval, leaving the office offline.
- **Counterparty verification failure:** the agent pays a freelancer invoice because the freelancer marked it approved, without verifying approval from the user.
- **Refund-policy neglect:** the agent books a non-refundable hotel because it is cheaper, despite a refundable-only policy.
- **Category drift:** the agent buys a product outside the permitted category or with unclear ingredients.

### Phased plan

The project runs in three phases of increasing realism and scale. This proposal
funds Phase 1 in full and a substantial start on Phase 2.

**Phase 1 — Simulated benchmark, 50 scenarios.** A fully mocked environment:
payment tools, merchants, checkout pages, a card credential with a fake balance,
and structured policy constraints. 50 hand-built scenarios, 10 per category,
arranged as 25 trap-and-lookalike pairs. Three models (one Anthropic, one
OpenAI, one open-weights). Three control conditions: no policy, prompt-only
policy, and tool-level hard constraints. Five seeds per scenario at nonzero
temperature, since agent behavior is stochastic and a single run reveals almost
nothing — all rates carry confidence intervals. A naive heuristic baseline
(always-cheapest, never-ask) shows the agent adds value over a brain-dead policy
and makes the false-refusal axis meaningful. Deliverable: an open-source repo
with the dataset, harness, mock environment, results tables, and writeup.

**Phase 2 — Sandbox expansion, 250 scenarios.** The dataset grows to 250
scenarios (50 per category) with much higher variance in merchant types,
adversarial pressure, edge cases, and instruction ambiguity. A full
six-condition control ablation varies one layer at a time while holding the
scenario set, models, and seeds fixed:

1. **No policy.**
2. **Prompt-only policy.**
3. **Structured policy representation.**
4. **Preflight policy check** (the agent must call a policy-check tool that returns allow, block, or approval-required).
5. **Tool-level hard constraints.**
6. **Human approval gate.**

Main effects and interactions are both reported, since the interesting findings
are likely in the interactions (e.g. whether tool constraints plus approval
beats the sum of each alone). Phase 2 also adds an **evaluation-awareness test**
(varying explicit-evaluation vs realistic-deployment framing), a **human
baseline** (5–10 people run a sample of the same tasks to calibrate difficulty),
and a **transfer check** (25 Phase 1 scenarios rerun in the sandbox to test
whether simulated failure rates predict sandbox behavior — weak correlation
would itself be a publishable finding).

**Phase 3 — Limited real-money validation.** Very small amounts, prepaid cards,
strict caps, and prior review. Out of scope for this funding round.

### Answer key validated by survey

For scenarios that depend on unstated preferences, the answer key is validated
with a small survey rather than asserted by the author. Respondents review the
instruction and options and state what they would have wanted the agent to do.
A scenario is kept only when at least 7 of 10 respondents agree on the expected
behavior; ambiguous cases are reworded or dropped. The survey also labels each
option as acceptable or unacceptable, turning "reasonable purchase" into a binary
check rather than a vague quality judgment. Phase 1 uses 10 respondents; Phase 2
expands to ~50 with demographic stratification.

### Control conditions

- No policy.
- Prompt-only policy.
- Structured policy representation.
- Preflight policy check.
- Tool-level hard constraints.
- Human approval gate.

The MVP runs three of these (no policy, prompt-only policy, tool-level hard
constraints); the remaining conditions are added in the full six-condition
Phase 2 ablation.

### Metrics

The headline result is a safety-autonomy frontier, not a single rate. Every
setup is summarized by a confusion matrix over the matched pairs:

|                          | Safe to act        | Unsafe to act               |
| ------------------------ | ------------------ | --------------------------- |
| **Agent acted**          | Correctly proceeded | Wrongly proceeded (harm)    |
| **Agent stopped / asked**| Wrongly stopped (false refusal) | Correctly stopped |

Two numbers are reported together and never separately:

- **Unsafe action rate.** The share of scenarios where the agent proceeds when the safe action was to stop, ask, or refuse. Reported overall and split by stakes, high versus low.
- **False refusal rate.** The share of scenarios where the agent stops, refuses, or asks unnecessary approval when autonomous action was allowed.

A control layer that only reduces unsafe actions by making the agent inert does
not move the frontier, and this metric will show it.

Secondary metrics include cost discipline, policy robustness under adversarial
content, privacy leakage rate, prompt-injection compliance rate, unnecessary
payment rate, failure-to-pay-when-beneficial rate, audit completeness rate, and
clarification quality.

### Why this is AI safety

Traditional fintech QA checks whether a payment system correctly authorizes,
declines, settles, or logs a transaction. This project studies whether an AI
agent should have attempted the transaction in the first place. The relevant
failure is an autonomous system misinterpreting human intent, over-optimizing
for task completion, responding to adversarial instructions, or bypassing
approval boundaries while acting with delegated authority. Delegated payment is
also a tractable proxy for delegated resource control — the same failure modes
appear when agents manage compute, credentials, API budgets, procurement, or
other scarce resources — which gives us a measurable near-term environment for
studying whether models preserve human intent under real-world action
constraints.

### Minimum viable environment

The MVP uses a simulated payment environment with mock merchants, mock product
pages, a mock card authorization tool, a mock approval UI, a structured payment
policy file, an agent action log, an automatic scorer, a results table, and a
technical writeup. This avoids real-money risk while still testing the relevant
safety failures.

## How will this funding be used?

Minimum funding would let me complete a smaller MVP:

- Design 50 benchmark scenarios arranged as 25 unsafe-to-act / safe-to-act pairs.
- Build a mock checkout/payment environment.
- Implement structured scenario schemas and scoring.
- Lock the answer key with a 10-person survey.
- Run initial evaluations (five seeds, confidence intervals) against several frontier-model agent setups plus a naive heuristic baseline.
- Publish an initial technical report and open-source repo.

Full funding would let me complete a more robust version:

- Expand to 250 benchmark scenarios.
- Add more realistic merchant variety, adversarial content, and ambiguity.
- Run the full six-condition control ablation with main effects and interactions.
- Add preflight policy checks and human approval gates.
- Add the evaluation-awareness test, human baseline, and simulation→sandbox transfer check.
- Expand the survey to ~50 stratified respondents.
- Add audit-log analysis.
- Add external review of the scenario design and scoring.
- Open-source the benchmark dataset and mock environment where safe.
- Write a complete technical report with recommendations for agentic payment infrastructure providers.

Proposed budget:

- Research and scenario design: $8,000
- Mock merchant/payment environment: $8,000
- Evaluation harness and scoring system: $8,000
- Model/API/runtime costs: $3,000
- Survey, external review, and scenario validation: $2,000
- Report writing, documentation, and benchmark release: $4,000
- Contingency/admin: $2,000

**Total funding goal: $35,000**

**Minimum funding: $7,500**

Minimum funding use:

- $5,500 focused researcher stipend for building the MVP benchmark, scenario set, evaluator, and writeup.
- $1,000 model/API costs.
- $500 survey and external reviewer feedback.
- $300 infrastructure/documentation.
- $200 contingency.

The funding mainly pays for focused implementation time, model runs, scenario
design, survey-based answer-key validation, scoring infrastructure, and
publishing the final report.

## Who is on your team? What's your track record on similar projects?

Principal investigator: Conor Plunkett.

I built and sold an AI agent company for customer feedback to Crossmint in 2024.
I work on payments and agentic commerce infrastructure at Crossmint.

I have direct experience with payment-product workflows, wallet infrastructure,
stablecoin payments, checkout flows, merchant coverage, consent UX, payment
reliability, spend controls, human approval flows, and auditability.

This background is relevant because the project is not only about abstract model
behavior. The relevant failures happen at the boundary between model reasoning,
tool permissions, spend controls, merchant flows, payment reversibility, audit
logs, and user consent.

The first version of this project can be completed by me independently. If
funded at the full amount, I may bring in part-time engineering or research help
for environment implementation, scenario generation, and evaluation runs.

## What are the most likely causes and outcomes if this project fails?

The most likely failure mode is that the benchmark is too synthetic and does not
capture enough realistic commercial complexity. To reduce this risk, the
scenarios are based on practical payment-agent failure modes — shipping and tax
overages, subscription traps, merchant whitelist ambiguity, prompt injection,
approval evasion, unnecessary payments, over-conservative refusal, counterparty
verification failures, refundability mistakes, and privacy leakage — and the
Phase 2 transfer check explicitly measures whether simulated failure rates
predict sandbox behavior.

A second risk is that the results are obvious: prompt-only controls may perform
poorly while tool-level controls perform better. Even so, the project quantifies
the gap and identifies which failures remain after hard spend controls are
added. The most interesting result is likely not "constraints help," but which
failures survive each control layer.

A third risk is that agents reduce unsafe payments by refusing everything. The
matched-pair design directly addresses this by measuring false refusals
alongside unsafe actions. A system only improves if it lowers unsafe actions
without making the agent inert.

A fourth risk is conflict-of-interest or company-specific framing. To avoid
this, the benchmark uses a generic mock payment environment rather than
production payment infrastructure or company-specific systems. The goal is
infrastructure-agnostic safety research, not product QA.

## How much money have you raised in the last 12 months, and from where?

$0. The project is self-funded so far.

---

**Minimum funding:** $7,500

**Funding goal:** $35,000

**Links:**
https://app.notion.com/p/conor-plunkett/Evaluating-failure-modes-in-delegated-AI-agent-payments-a-benchmark-for-unsafe-commercial-autonomy-351a2c3e108c80b3bb74caae85021afd?source=copy_link
