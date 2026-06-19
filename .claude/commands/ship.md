Full pre-ship checklist for the CPG Sales Intelligence project: lint → tests → Docker build → health verification → git status.

Run this before merging any branch or sharing a demo.

## Steps

1. **Lint** — Run `python3 -m flake8 src/ tests/ --max-line-length=100`. Stop and report if any errors.

2. **Tests** — Run `python3 -m pytest tests/ -q`. Stop and report if any failures.

3. **Docker build** — Run `docker compose build`. Stop and report if the build fails.

4. **Start container** — Run `docker compose up -d`, then wait up to 45 seconds for `(healthy)` status.

5. **Smoke test the API** — Hit these three endpoints and confirm all succeed:
   - `GET /health` → status must be "ok"
   - `GET /data-quality` → clean_rows must be > 0
   - `GET /sales-summary` → total_revenue must be > 0

6. **Git status** — Show `git log --oneline -8` and `git status`. Flag any uncommitted changes.

7. **Final report** — Print a pass/fail summary for each of the 6 steps above. If all pass, print the demo URLs:
   - Dashboard: http://localhost:8501
   - API docs: http://localhost:8000/docs

If $ARGUMENTS is a branch name, also show `git diff main...$ARGUMENTS --stat` so the user can see what's included in the branch.
