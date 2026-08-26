#!/usr/bin/env bash
# Deploy the admin-scenario-data Edge Function, refusing to run unless the
# checkout is exactly origin/main with a clean tree and a freshly regenerated
# bundle. Guards the 2026-08-26 incident: a deploy ran from a checkout that
# hadn't pulled the merged b25 key fix, so Supabase kept serving the old
# ["purchase", "refuse"] answer key after main had already moved to
# ["purchase"] only.
# Usage: ./scripts/deploy_scenario_explorer.sh
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

FUNCTION_DIR="supabase/functions/admin-scenario-data"

echo "Fetching origin/main..."
git fetch origin main -q

if [ -n "$(git status --porcelain)" ]; then
  echo "error: working tree has uncommitted changes -- can't tell if it matches main." >&2
  git status --short >&2
  exit 1
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$CURRENT_BRANCH" != "main" ]; then
  echo "error: deploy from main, not '$CURRENT_BRANCH'." >&2
  echo "Merge your change first, then: git checkout main && git pull origin main" >&2
  exit 1
fi

LOCAL_HEAD="$(git rev-parse HEAD)"
REMOTE_HEAD="$(git rev-parse origin/main)"
if [ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]; then
  AHEAD="$(git rev-list --count origin/main..HEAD)"
  BEHIND="$(git rev-list --count HEAD..origin/main)"
  if [ "$AHEAD" -gt 0 ] && [ "$BEHIND" -gt 0 ]; then
    echo "error: local main ($LOCAL_HEAD) has diverged from origin/main ($REMOTE_HEAD): $AHEAD ahead, $BEHIND behind." >&2
    echo "Move the local commits to a branch, then: git reset --hard origin/main" >&2
  elif [ "$AHEAD" -gt 0 ]; then
    echo "error: local main ($LOCAL_HEAD) is $AHEAD commit(s) ahead of origin/main ($REMOTE_HEAD)." >&2
    echo "Those commits aren't on main yet. Move them to a branch, open a PR, merge it, then: git pull origin main" >&2
  else
    echo "error: local main ($LOCAL_HEAD) is $BEHIND commit(s) behind origin/main ($REMOTE_HEAD)." >&2
    echo "Run: git pull origin main" >&2
  fi
  exit 1
fi

echo "Regenerating scenario explorer data from source..."
python scripts/generate_scenario_explorer_data.py

if [ -n "$(git status --porcelain -- "$FUNCTION_DIR")" ]; then
  echo "error: regenerating changed files under $FUNCTION_DIR -- the committed bundle is stale." >&2
  echo "Commit the regenerated files on a branch, merge to main, then re-run this script." >&2
  git status --short -- "$FUNCTION_DIR" >&2
  exit 1
fi

echo "Checkout matches origin/main and the bundle is fresh. Deploying..."
supabase functions deploy admin-scenario-data --no-verify-jwt --project-ref tethtzycfdplyzvrtknh
