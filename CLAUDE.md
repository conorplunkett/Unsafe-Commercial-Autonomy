# Project memory

## Git / merge workflow (IMPORTANT)

- **Never commit straight to `main`.**
- When the user says "merge" (or asks to land/ship work), always follow this flow:
  1. Create a new branch off the latest `main`.
  2. Commit the work to that branch and push it.
  3. Open a pull request.
  4. Merge the pull request.
- Only push directly to a feature branch; `main` is updated exclusively through merged PRs.

@AGENTS.md
