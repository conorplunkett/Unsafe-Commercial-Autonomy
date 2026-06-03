# Unsafe Commercial Autonomy

Testing whether delegated AI payment agents preserve user intent, spend limits,
merchant rules, approval boundaries, and privacy constraints.

## Run

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` to run the simulated benchmark and view results.

## API

- `GET /api/scenarios`
- `GET /api/scenarios/{scenario_id}`
- `POST /api/runs`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/events`
- `GET /api/metrics?run_id=...`

The first milestone is simulated only: no live LLM calls, no real payment rails,
and no Crossmint sandbox integration.
