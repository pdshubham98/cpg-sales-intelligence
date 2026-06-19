Start and verify the CPG Sales Intelligence application using Docker.

## Steps

1. Check Docker is running (`docker info`). If not, tell the user to start Docker Desktop and stop.

2. Check if the container is already running (`docker ps`). If it is and status is `(healthy)`, report the URLs and stop — no rebuild needed.

3. If not running or unhealthy:
   - Run `docker compose build` to build the image
   - Run `docker compose up -d` to start in detached mode
   - Wait up to 45 seconds for the health check to pass, polling every 5 seconds with `docker ps`

4. Call `curl -s http://localhost:8000/health` and show the parsed JSON response (status + db_rows).

5. Call `curl -s http://localhost:8000/data-quality` and show the ingestion report (raw_rows, clean_rows, dropped_rows).

6. Report the two URLs clearly:
   - Streamlit dashboard: http://localhost:8501
   - FastAPI docs: http://localhost:8000/docs

If anything fails at any step, show the last 30 lines of container logs with `docker compose logs --tail=30`.
