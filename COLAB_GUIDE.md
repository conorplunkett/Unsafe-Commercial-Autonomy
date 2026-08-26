# Running PayBench in Google Colab

PayBench's live evals are outbound HTTP calls to hosted model APIs (OpenAI,
Anthropic, Gemini, Kimi, Inkling, Grok, DeepSeek, Mistral, Qwen, OpenRouter).
`requirements.txt` has no `torch`, `transformers`, or `vllm` — the CLI never
loads a model locally. That makes Colab's free GPU irrelevant to almost
everything this repo does; Colab is useful here as a free, disposable Linux
box with a browser-based editor and a built-in secrets store, not as compute.
The one exception, self-hosting an open-weight model, is Steps 17-19.

No code changes are required to run this repo in Colab. Every step below is
something you do in a notebook cell, in the Colab UI, or on your own machine
— never a change to this repo's code.

## What the GPU does and doesn't buy you

Every model id except `openweights` (`openai`, `anthropic`, `gemini`, `kimi`,
`inkling`, `grok`, `deepseek`, `mistral`, `qwen`, `openrouter`) is a REST call
to a vendor's API — see `app/providers.py` and `app/phase2/providers.py`.
None of them touch a GPU, local or otherwise; the work happens on the
vendor's servers, and your side is just `httpx`/SDK calls plus JSON parsing.
`openweights` is different: it points the CLI at an OpenAI-compatible
`/chat/completions` endpoint *you* stand up yourself (vLLM, llama.cpp, TGI).
The repo ships no code to load or serve weights — that part is entirely on
you, and it's the only path where a GPU matters.

Practical consequence: pick Colab's **no-accelerator runtime** (Step 1) for
ordinary provider evals (Steps 2-16). Requesting a GPU buys nothing for that
workload and spends down your rationed free GPU quota for no reason. Only
switch to a GPU runtime for the optional self-hosted open-weights path
(Steps 17-19).

## Free-tier limits and what they mean here

From Google's own Colab FAQ:

- GPU type and availability "vary over time" and are not guaranteed; free
  tier is explicitly deprioritized behind paid Pro/Pro+ and access can be
  "heavily restricted." Expect a T4 when you get a GPU at all — and don't
  assume you'll get one.
- Free notebooks run "at most 12 hours, depending on availability," and
  disconnect after a period of inactivity. Neither number is published on
  purpose — Colab keeps them adjustable.
- The VM's disk is not persistent: "Virtual machines are deleted when idle
  for a while, and have a maximum lifetime enforced by the Colab service."
  Anything not copied out before that (Drive, download, or publish) is gone.
- Explicitly against Colab's usage policy on every tier: hosting file/media/
  web services unrelated to interactive compute, SSH or remote-desktop
  access, connecting to remote proxies, running distributed-computing
  workers, and (free tier specifically) bypassing the notebook UI to drive
  a long-running background job. Colab is built around active, interactive
  sessions — not unattended batch infrastructure.

What that means for "free runs on models": Colab's free tier is a fine place
to run small, exploratory `phase2-eval` grids interactively — one model, a
couple of scenario pairs, seed 1, watched in real time. It is a poor fit for
the full paid design (many providers × three seeds × hundreds of scenarios):
that run will outlast a single session, and Colab's own policy is aimed at
active use, not parking a multi-hour job and walking away. For that scale,
either run it from a machine you control that can stay up unattended, or
split it across several Colab sittings using checkpoints and `merge` (Steps
10-12) — and expect it to take several sittings, not one.

Source: [Google Colab FAQ](https://research.google.com/colaboratory/faq.html).

## Repo changes required

None. This is a plain `pip install`-able Python 3 CLI project; a fresh clone
runs unmodified in a Colab cell. A few things are worth knowing rather than
fixing:

- **`.env` isn't hand-edited the normal way.** Colab has no persistent local
  editor session across restarts. Write `.env` at the start of each session
  from Colab's Secrets store instead (Step 6). It's the same `.env` file and
  the same `load_env_file()` mechanism the CLI already uses locally; nothing
  new to build.
- **Large live grids need `--yes`.** A Colab cell is a scripted context, not
  an interactive terminal — treat it the way RUNBOOK.md already tells you to
  treat CI: review the grid size with `--dry-run` or a small run first (Step
  4/8), then pass `--yes` to run it live (Step 9). This is the CLI's
  existing safety guard doing its job, not a Colab-specific problem.
- **Point run/checkpoint storage at Drive for anything longer than one
  sitting.** `RUN_STORAGE_DIR` and `RUN_CHECKPOINT_DIR` are both
  environment-variable overrides the CLI already supports (`app/storage.py`,
  `app/phase2/checkpoint.py`). Setting them to a mounted Drive path (Steps
  10-11) is a notebook-side choice, not a repo change.

Not doing it now, but worth it later if Colab becomes a regular workflow: a
small `notebooks/colab_quickstart.ipynb` that wraps the steps below into one
click. This task was scoped as research plus this guide, not new code.

## Steps

Each step says where it runs: a **Colab UI** action (click something, no
code), a **Colab cell** (paste into a new cell, run it), or **your own
machine** (not Colab at all). Steps 1-9 are the normal path for a small live
run. Steps 10-12 only apply if a run needs more than one Colab sitting.
Steps 13-16 get results out. Steps 17-19 are the optional self-hosted-GPU
path.

### 1. (Colab UI) New notebook, CPU runtime

Open [colab.research.google.com](https://colab.research.google.com) → New
notebook → Runtime → Change runtime type → Hardware accelerator: **None**.

### 2. (Colab cell) Clone the repo

```python
!git clone https://github.com/conorplunkett/Unsafe-Commercial-Autonomy.git
%cd Unsafe-Commercial-Autonomy
```

The repo is public, so no token is needed. (If it's ever made private, clone
with a fine-grained personal access token stored as a Colab secret —
`https://<token>@github.com/conorplunkett/Unsafe-Commercial-Autonomy.git` —
never typed in plaintext into a cell.)

### 3. (Colab cell) Install dependencies

```python
!pip install -r requirements.txt
```

CI pins Python 3.11; nothing in `requirements.txt` needs that exact minor
version, and Colab's preinstalled interpreter is normally close enough. Run
`!python --version` if something behaves oddly.

### 4. (Colab cell) Sanity check — fully offline

```python
!python -m pytest -q
!python -m app.cli phase2-eval --dry-run \
  --models scripted_naive,scripted_diligent \
  --scenario-ids scn_v2_a1_trap,scn_v2_a1_lookalike \
  --conditions all --seeds 1
```

Neither command touches an API key or the network. If either fails, fix that
before adding keys — it's a setup problem, not a model problem.

### 5. (Colab UI) Add API key secrets

Key icon in the left sidebar → "Add new secret" → set the name to match
`.env.example` (e.g. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) and the real
value → enable "Notebook access." Repeat per provider you plan to use.

### 6. (Colab cell) Write the keys into `.env`

```python
from google.colab import userdata
from pathlib import Path

# List only the keys you actually added as secrets in Step 5.
PROVIDER_KEYS = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]

lines = [f"{name}={userdata.get(name)}" for name in PROVIDER_KEYS]
Path(".env").write_text("\n".join(lines) + "\n")
print(f"Wrote {len(lines)} key(s) to .env")
```

Never `print(userdata.get(...))` directly — that echoes the raw key into
cell output.

### 7. (Colab cell) Confirm a key actually works

```python
!python -m app.cli models --provider openai
```

Swap `openai` for whichever provider you're checking. Do this before
spending on a real grid.

### 8. (Colab cell) Run a small live eval

```python
!python -m app.cli phase2-eval --models openai \
  --scenario-ids scn_v2_a1_trap,scn_v2_a1_lookalike \
  --conditions all --seeds 1
```

Swap `openai` for any provider you added a key for in Step 5. Grids at or
under 50 total calls run without a prompt.

### 9. (Colab cell, only if the grid is bigger than 50 calls) Confirm and run the full grid

The CLI prints the call count and refuses to proceed non-interactively above
that — this is expected in a Colab cell, not a bug. Review the printed
count, then re-run with `--yes`:

```python
!python -m app.cli phase2-eval --models openai \
  --conditions all --seeds 1,2,3 --yes
```

`--concurrency N` cuts wall-clock by running episodes in parallel; bound it
by the provider's rate limit, not by anything Colab-specific. (Colab's
outbound IPs are shared across many users — if a provider throttles harder
than expected, that's a plausible reason, not necessarily your key.)

**If your run fits in one sitting, you're done with the run itself — skip to
Step 13 to get results out.** Steps 10-12 are only for grids that will
outlast one Colab session.

### 10. (Colab cell) Mount Drive

```python
from google.colab import drive
drive.mount('/content/drive')
```

### 11. (Colab cell) Point run/checkpoint storage at Drive

Run this **before** Step 8 or 9, in the same session:

```python
%env RUN_STORAGE_DIR=/content/drive/MyDrive/paybench/runs
%env RUN_CHECKPOINT_DIR=/content/drive/MyDrive/paybench/checkpoints
```

Checkpointing is on by default (`--no-checkpoint` turns it off — don't, for
anything paid).

### 12. (Colab cell, only after a disconnect) Resume

Start a fresh session and repeat Steps 2, 3, 10, 11 (clone, install, mount
Drive, re-point storage at the *same* Drive paths), then:

```python
!python -m app.cli phase2-checkpoints
!python -m app.cli phase2-eval --resume <run_id> [same axes as the original run]
```

`--resume` rejects a different grid and only re-runs what's missing or
errored. To stitch several sittings of the same model/scenario grid into one
run, use `merge` (see RUNBOOK.md) — `--dry-run` first to check compatibility.

### 13. (Colab UI + cell) Get results out — Option A: publish straight from Colab

Add one more secret the same way as Step 5: `SUPABASE_SERVICE_KEY`. This key
bypasses row-level security — treat it as more sensitive than any
model-provider key, and only add it to a notebook you trust. Add it to
`PROVIDER_KEYS` in Step 6 and re-run that cell, then:

```python
!python -m app.cli publish --latest --label "Colab: <what this run is>"
```

This is the actual mechanism that makes a run visible on the public site —
nothing about it changes because it ran in Colab. Use this **or** Option B
(Step 14), not both.

### 14. (Colab cell) Get results out — Option B: download the run instead

The safer default if you'd rather not put the production Supabase key into a
cloud notebook.

```python
from google.colab import files
files.download(f"runtime/runs/{run_id}.json")
```

If you used the Drive-backed paths from Steps 10-11, the file is already in
your Drive folder — just sync it locally instead of using `files.download`.

### 15. (Your own machine, not Colab) Publish the downloaded run

```bash
python -m app.cli publish --file path/to/run.json --label "..."
```

### 16. (Your own machine, not Colab; optional) Write up results as a new versioned doc

For a narrative write-up rather than just the raw run, CLAUDE.md's rule
applies as-is: this is a new, separately-versioned document, never an edit
to `proposal_LOCKED.pdf`. Follow the existing precedent
(`survey1_results_v1.md`, `survey1_figs/`) — add a new dated or versioned
file such as `results_phase2_v1.md`, commit it on a feature branch off
`main`, and go through the normal AGENTS.md flow (PR, then merge only once
explicitly asked for).

## Optional: self-hosting an open-weight model on the free GPU

The one path where the GPU runtime matters — and it's entirely outside this
repo's own code.

### 17. (Colab UI) Switch to a GPU runtime

Runtime → Change runtime type → Hardware accelerator: GPU (commonly a T4 on
free tier; not guaranteed, see the limits section above).

### 18. (Colab cell) Install and start a local model server

```python
!pip install vllm
!python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct --port 8001 &
```

This install is large — a few minutes, several GB.

### 19. (Colab cell) Point PayBench at it and run

```python
%env OPENWEIGHTS_BASE_URL=http://127.0.0.1:8001/v1
%env OPENWEIGHTS_MODEL=Qwen/Qwen2.5-7B-Instruct
!python -m app.cli phase2-eval --models openweights \
  --scenario-ids scn_v2_a1_trap,scn_v2_a1_lookalike --conditions all --seeds 1
```

Two things to know before trusting results from this path:

- **Sizing.** A free T4 has 16GB of VRAM — comfortable for roughly a
  7-8B-parameter model in fp16/bf16, larger with 4-bit/8-bit quantization,
  nowhere near the flagship hosted models the other providers default to.
  Treat this as a way to spot-check one specific open-weight model, not a
  substitute for the hosted-provider grid.
- **Tool calling.** Phase 2 scenarios drive the model through tool calls
  (`search_offers`, `view_offer`, `pay`, `request_approval`, `finish`). Not
  every self-hosted server enables OpenAI-style tool calling by default —
  vLLM needs `--enable-auto-tool-choice` plus a `--tool-call-parser` matched
  to the model family. Check that before trusting a Phase 2 run against it.

And per the prohibited-uses list above: Step 18 starts a literal local web
server. Keep it inside the interactive session you started it in — don't
leave it running unattended.

## Quick reference

The same Steps 1-8 and 13, condensed, no explanation — for a repeat run once
you've done this once already.

```python
# Steps 1-4: one-time per session
!git clone https://github.com/conorplunkett/Unsafe-Commercial-Autonomy.git
%cd Unsafe-Commercial-Autonomy
!pip install -r requirements.txt
!python -m pytest -q

# Steps 5-6: keys (edit PROVIDER_KEYS to match your Colab secrets)
from google.colab import userdata
from pathlib import Path
PROVIDER_KEYS = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
Path(".env").write_text("\n".join(f"{k}={userdata.get(k)}" for k in PROVIDER_KEYS) + "\n")

# Steps 10-11: only for runs that outlast one sitting
from google.colab import drive
drive.mount('/content/drive')
%env RUN_STORAGE_DIR=/content/drive/MyDrive/paybench/runs
%env RUN_CHECKPOINT_DIR=/content/drive/MyDrive/paybench/checkpoints

# Step 8: a run
!python -m app.cli phase2-eval --models openai \
  --scenario-ids scn_v2_a1_trap,scn_v2_a1_lookalike \
  --conditions all --seeds 1

# Step 13/14: get results out
!python -m app.cli publish --latest --label "Colab run"
# or: from google.colab import files; files.download(f"runtime/runs/{run_id}.json")
```

## Sources

- [Google Colab FAQ](https://research.google.com/colaboratory/faq.html) —
  GPU availability and priority, session/idle limits, prohibited uses,
  ephemeral VM storage.
