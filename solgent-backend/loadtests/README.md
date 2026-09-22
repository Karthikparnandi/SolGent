# Load testing /chat/stream

## Prerequisites
Bring up the full stack locally first — do not point this at a shared
Supabase project without knowing every simulated user writes real rows:

    docker compose up --build

Confirm the backend answers before load-testing it:

    curl http://localhost:8000/health

## Install
    pip install -r solgent-backend/requirements-loadtest.txt

## Run (interactive web UI)
    cd solgent-backend/loadtests
    locust -f locustfile.py --host http://localhost:8000

Open http://localhost:8089, set user count and spawn rate, start the test.

## Run (headless, for capturing numbers to put in the README)
    locust -f locustfile.py --host http://localhost:8000 \
      --headless -u 50 -r 5 -t 3m \
      --csv=results/run1

- `-u 50`: 50 concurrent simulated users
- `-r 5`: ramp up 5 users/second
- `-t 3m`: run for 3 minutes
- `--csv`: writes results/run1_stats.csv with p50/p95/p99 per named metric

## Reading the output
Two rows matter:
- `/chat/stream [ttfb]` — time to first byte. This is the "does it feel
  instant" number.
- `/chat/stream [total]` — full stream completion time. Expected to scale
  with response length; compare (total - ttfb) / avg_token_count across
  runs at different concurrency levels to see whether Groq's per-token
  rate holds steady under load or degrades.

Increase `-u` across successive runs (10 → 50 → 100 → 200) and watch where
p95 ttfb starts climbing non-linearly — that inflection point is your
practical concurrency ceiling on this deployment, and it's the number
worth putting in the README, not a single "it's fast" run at low load.