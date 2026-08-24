# Agent rules

Repo-wide rules for AI agents working in this repository. This file is the single
source of truth for agent rules; the root `CLAUDE.md` just imports it so Claude
Code picks it up. (The `web/` app has its own scoped `AGENTS.md` for Next.js
work; this file governs the repository as a whole.) Read this before making
changes.

## Chat replies to Conor must be short (IMPORTANT)

Applies to every reply in conversation (not file/PR content).

- Talk to Conor like he's 18 — plain words, no jargon, explain things simply.
- 1-4 sentences by default. No background/context dump.
- Use tables a lot to outline things (options, files touched, decisions).
- When a decision comes up, include the tradeoffs — briefly, a small table is
  ideal.

## Git / merge workflow (IMPORTANT)

- **Never commit straight to `main`.**
- When the user says "merge" (or asks to land/ship work), always follow this flow:
  1. Create a new branch off the latest `main`.
  2. Commit the work to that branch and push it.
  3. Open a pull request.
  4. Merge the pull request.
- Only push directly to a feature branch; `main` is updated exclusively through merged PRs.
- **"Merge" authorizes one merge, not a policy.** Approval of a code change
  ("yes, delete it", "fix it", "ship it") is approval to develop and push on a
  branch — it is NOT approval to open or merge a PR. A "merge it" earlier in
  the same conversation does not carry over to later work. Before every PR and
  every merge (including reverts), stop and get a fresh, explicit "merge" from
  Conor for that specific piece of work. When in doubt, leave the work pushed
  on its branch and ask.

## Webpage copy — never sound like AI (IMPORTANT)

Applies to every user-facing page in this repo (lander, survey, admin dashboard,
Experiment Lab).

- **Never narrate what the reader can already see.** A stacked bar does not need "Each bar is 100% of the people who answered that scenario, split by the action they chose."
- **No explainer subtitles under headings or charts by default.** If a chart needs a sentence to be understood, fix the chart. The only caption a chart earns is a legend definition it can't show visually.
- **Banned voice patterns:** "Every X across all N Y, collapsed into…", "At a glance —", "Based on N choices from M respondents", "The dominant choice is named on the right", "X — the thing that does Y" appositives as a default sentence shape, and self-describing stamps like "merge · manual, never automatic" — a control explaining its own nature isn't a fact worth a label; name the command or state a number instead.
- **Prefer labels over sentences:** "372 answers · 31 respondents · 12 scenarios", not "Every answer across all 12 scenarios, based on 372 choices from 31 clean respondents."
- **Methodology detail** (n=, filters, definitions) goes in a tooltip or footnote, never in headline copy.
- Headings are short nouns: "By scenario", not "At a glance — every scenario".

## Design system for the website

`web/DESIGN.md` is the source of truth for the site's colour tokens, type scale,
and panel component. Read it before changing any markup or CSS under `web/`.
Colours and font sizes come from tokens in `web/app/globals.css` — never a hex
value or an arbitrary size in a component. The site is single-theme; no dark mode.

## LOCKED proposal — do not edit

`proposal_LOCKED.pdf` at the repo root is the **final, locked proposal paper**.
It is frozen on purpose and is treated as an immutable record.

- **Never edit, regenerate, reformat, rename, or delete `proposal_LOCKED.pdf`.**
- Do not "improve," recompile, or sync it against any other document, even if
  the README, the Notion plan, or the code has since moved on. Divergence
  between the locked proposal and later work is expected and acceptable.
- If a change would touch this file, stop and ask the user first.

## Publishing results is a new version, not an edit

When we later publish results, write-ups, or an updated paper, that is a **new,
separately-versioned document** — never a modification of the locked proposal.

- Add a new file (for example `paper_v2.pdf` / `results_v1.pdf`, or a dated /
  versioned name) rather than overwriting `proposal_LOCKED.pdf`.
- Keep each released version as its own immutable artifact so the history of
  what was claimed, and when, stays auditable.

## Phase 2 research contract — frozen projection (IMPORTANT)

`data/answer_keys/phase2_research_contract.json` is the committed projection
that prevents accidental drift in the Phase 2 instrument and keys.

- It protects the exact survey version, wording, options, slot keys, order, and
  batches; all 226 authored `right_answer`, `expected_action`,
  `acceptable_actions`, and `safe_to_act` values; and the effective keys after
  any adopted survey re-key, including status and provenance.
- Sandbox environments, merchant copy, offers, cart state, checkout controls,
  and tool implementation are deliberately outside the projection. Work on
  those surfaces must not change the frozen file.
- **Never regenerate the projection merely to silence its drift test.** For an
  intentional instrument, protected-key, or adopted-survey-key change, update
  the canonical source first, run
  `python scripts/freeze_phase2_research_contract.py`, and review the generated
  JSON diff as part of the same change.

## Scenario content must never narrate its own trap (IMPORTANT)

Applies to every field the model-under-test can see in a Phase 2 sandbox episode:
`offer_id`, `merchant_id`, `merchant_name`, `item`, `page_text`, tool names/descriptions
in `app/phase2/sandbox.py`, and the system/user prompt text in `build_system_prompt`/
`build_user_prompt`. None of this is documentation — it is the in-universe content a
purchasing agent reads, so it must read exactly like a real webpage, invoice, or tool
result would. It must never carry the author's voice describing the mechanism.

This was found live in the data on 2026-08-19: an offer's `search_offers` price was
returned under the key `headline_price` (telling the model in advance that the number
might not be real), and separately an injection-compliance offer had `offer_id:
"off_attacker"` and `merchant_name: "Attacker Checkout (swapped link)"` — handing the
model the answer before it looked at anything. Both are the same failure: content meant
to be neutral, in-world text instead announced the trap.

- **No narrator commentary, anywhere the model can read it.** Don't name what a field
  "really" is (`headline_price` vs `price`), don't label a choice as the trap (`off_attacker`,
  `off_fabricate`, `off_guilt_tip`, `guilthotel`), and don't editorialize about the
  deception in a merchant name or item title (`"Attacker Checkout (swapped link)"`,
  `"amaz0n.com (typosquatted, 4 redirects)"`, `"(bot pleads about bankruptcy)"`,
  `"(button swapped before click)"`, `"(competitor slam)"`, `"hostile label"`).
- **The real signal belongs in realistic surface content the model has to notice itself**
  — a misspelled domain, a mismatched display-text-vs-link, manipulative but plausible
  page copy — never in a field name, an ID, or a parenthetical aside explaining what's
  wrong with the offer.
- **IDs and merchant identifiers are plumbing, not labels.** Use neutral, positional
  names (`off_1`, `off_2`) or names that mirror what the fake page itself claims to be
  (a spoofed domain, a lookalike brand) — never a name describing the scenario's own
  answer key (`unsafe_marker`, `injection_compliance_marker`, `answer_key_trap_marker`,
  trap/lookalike pairing, etc.).
- **Scoring code must never key off model-visible strings either.** If a marker offer
  needs to be found programmatically, match it by its scorer-only field
  (`unsafe_marker`, `injection_compliance_marker`, `answer_key_trap_marker`, or their
  value-conditioned `*_marker_when` forms for checkout-control traps), never by
  `offer_id`/`merchant_id` string patterns (e.g. `.endswith("fabricate")`) — that
  couples scoring to the same name a rename could accidentally leave revealing.
- `tests/test_phase2_runner.py::test_offer_titles_never_narrate_the_trick` enforces the
  wording rule by regex across `offer_id`/`item`/`merchant_name`/`merchant_id` in
  `data/answer_keys/v2_constraints.json`. Extend its word list rather than special-casing
  around it when a new tell shows up.

## Scenario design — write traps like an adversary, not a warning label (IMPORTANT)

Applies to every trap authored or edited under `data/scenario_sets/` and
`data/answer_keys/`.

- **Design every offer the way a real deceptive merchant would present it,
  not the way a scenario author explaining the trap would.** The `page_text`
  an agent actually reads must disclose the true terms somewhere — never
  fabricate facts — but must not warn the agent about the consequence. A
  real dark pattern discloses technically, not plainly: a low headline
  price, the catch in a soft or offhand clause, reassuring language sitting
  right next to the thing it contradicts. "You will be billed for the full
  3 months even if you cancel sooner" is a warning label, not a trap —
  delete language like that on sight.
- **Do not pre-solve the trap in structured fields.** A trap offer's
  `price`/`total`/`fees` should reflect only what is charged at the moment
  of that transaction, never a pre-computed "true cost" that hands the
  arithmetic to whoever inspects the JSON. If a scenario needs the agent to
  notice a bad total, it has to work that out from the page text, the same
  way a real user would.
- **A scenario that needs an explicit warning to work isn't testing what it
  claims to.** If the trap only fails because the text told the agent it's
  bad, fix the deal — make the numbers or terms actually deceptive — don't
  fix the prose to compensate.
- **A merchant never certifies its own copy.** Real merchant text states what
  things are and what they cost — "Catering invoice #4192: event catering
  services, $100.00 due." — and stops. It never vouches for its own
  completeness or safety: no "all service charges included," no "the amount
  shown is the full amount payable," no "no hidden fees." A reassurance line
  like that exists only to tell the reader which arm is safe, which makes it
  answer-key coaching in a lookalike exactly the way a warning label is in a
  trap. The absence of a catch is shown by the absence of a catch — never by
  an assurance.

## Sources of truth

- `README.md` defines benchmark scope, the current phase, and the research
  design. The project is firmly in Phase 2; Phase 1 is complete and locked and
  should not receive further work unless the user explicitly reopens it.
- Scenario contents and counts come from `data/scenario_sets/`.
- Answer keys and survey status come from `data/answer_keys/` and
  `data/survey/`.
- CLI commands and defaults come from `python -m app.cli <command> --help`;
  environment variables come from `.env.example`.
- `RUNBOOK.md` holds only non-obvious operational workflows, and `CHANGELOG.md`
  holds historical changes.

The locked proposal is the historical funding record, not a live spec. When it
differs from current sources, follow the current sources and leave the PDF
untouched.

## Report-style markdown docs are working documents, not permanent records

A standalone `.md` file whose job is to report findings and track fixing them (an
audit report, a review tracker, a findings-with-checkmarks list — e.g. the old
`COACHING_REVIEW.md`) is scaffolding for an active fix campaign, not a source of
truth. Once every finding in one has been acted on — fixed, or deliberately
deferred with that decision recorded elsewhere (a CHANGELOG.md entry, a note to
the user) — **delete the file** rather than leaving it in the repo as a stale
checklist. A checkmark that quietly drifts out of sync with the live data is worse
than no checkmark: it gets trusted instead of verified, exactly the failure mode
that motivated this rule. Git history preserves the file if anyone needs the
detail later; `CHANGELOG.md` is where the substance belongs going forward.
