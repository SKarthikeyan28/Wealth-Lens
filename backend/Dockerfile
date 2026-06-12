FROM python:3.12-slim

WORKDIR /app

# `make` is our task runner but slim images omit it; install it explicitly.
RUN apt-get update && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/*

# Paths are relative to the build context, which is the repo root (see compose).
COPY backend/requirements.txt backend/requirements.txt
COPY requirements-dev.txt requirements-dev.txt
RUN pip install --no-cache-dir -r backend/requirements.txt -r requirements-dev.txt

COPY . .

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
