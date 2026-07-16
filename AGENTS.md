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
