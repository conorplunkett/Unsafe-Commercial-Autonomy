# Agent rules

Repo-wide rules for AI agents working in this repository. This file is the single
source of truth for agent rules; the root `CLAUDE.md` just imports it so Claude
Code picks it up. (The `web/` app has its own scoped `AGENTS.md` for Next.js
work; this file governs the repository as a whole.) Read this before making
changes.

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

## Source of truth for scope

For benchmark scope and README claims, the research plan described in `README.md`
remains the working source of truth for ongoing implementation. The locked
proposal is the historical record of the funding proposal, not a live spec —
when the two differ, follow the README/research plan for code, and leave the
locked PDF untouched.
