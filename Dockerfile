# Virtual AHU — single-container FastAPI app
FROM python:3.12-slim

WORKDIR /srv

# Install the app (deps resolved from pyproject; no dev extras in the image)
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

# SQLite trend history is ephemeral on a PaaS: keep it in /tmp so nothing
# assumes it survives a restart or redeploy.
ENV AHU_DB_PATH=/tmp/ahu_history.db

EXPOSE 8000

# PaaS platforms (Sevalla included) inject PORT; fall back to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
