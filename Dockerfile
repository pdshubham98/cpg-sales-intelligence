FROM python:3.11-slim

WORKDIR /app

# Install system deps for pandas/scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p db && chmod +x docker-entrypoint.sh

ENV DB_PATH=db/sales.db \
    API_BASE_URL=http://localhost:8000 \
    PYTHONPATH=/app

EXPOSE 8000 8501

ENTRYPOINT ["./docker-entrypoint.sh"]
