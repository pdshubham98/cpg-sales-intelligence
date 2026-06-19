Run the full test suite and lint check for the CPG Sales Intelligence project.

## Steps

1. Run flake8 lint first:
   ```
   python3 -m flake8 src/ tests/ --max-line-length=100
   ```
   If there are errors, list them clearly and stop — do not run tests until lint passes.

2. Run the full pytest suite with coverage:
   ```
   python3 -m pytest tests/ -v --tb=short 2>&1
   ```

3. Report a summary:
   - Total tests passed / failed / errored
   - Any failing test names and the error message
   - Whether lint was clean

4. If $ARGUMENTS contains "fix", attempt to auto-fix any lint errors found in step 1 before re-running.

## Context

- Tests are in `tests/` — 52 tests covering API, forecasting, ingestion, and LLM layers
- All LLM calls are mocked; no API keys required to run tests
- The test database is a temp SQLite file (tmp_path); never touches db/sales.db
- flake8 max line length is 100 characters
