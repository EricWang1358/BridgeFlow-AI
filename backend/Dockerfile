# Runs identically on WSL, an EC2 Linux box, and CI.
# Build context is the REPO ROOT (see docker-compose.yml) so `data/` is reachable.
FROM python:3.12-slim

WORKDIR /app

# Install deps first so code edits don't bust the layer cache.
COPY backend/pyproject.toml ./
COPY backend/src ./src
RUN pip install --no-cache-dir -e "."

COPY data ./data

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "bridgeflow.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
