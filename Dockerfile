FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .

RUN pip install --no-cache-dir -r requirements-docker.txt

COPY ingestion ./ingestion
COPY experimentation ./experimentation
COPY ai ./ai
COPY orchestration ./orchestration
COPY analytics ./analytics
COPY tests ./tests

CMD ["python", "-m", "pytest", "-v"]
