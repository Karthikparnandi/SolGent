# ---- Stage 1: builder ---------------------------------------------------
# Compiles wheels in a full build environment so the runtime stage never
# needs gcc, build headers, or pip's build cache.
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Stage 2: runtime ----------------------------------------------------
FROM python:3.11-slim AS runtime

# Create a non-root user. Running as root in a container is a real,
# exploitable attack-surface increase (container breakout escalates to
# host root) for zero operational benefit.
RUN useradd --create-home --shell /bin/bash solgent

WORKDIR /app

# Pull only the installed packages from the builder stage — not gcc,
# not pip's cache, not the requirements build artifacts.
COPY --from=builder /install /usr/local

COPY app/ ./app/

RUN chown -R solgent:solgent /app
USER solgent

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

# Uvicorn directly, not via `python -m app.main` + app.run(): this keeps
# worker count, host binding, and reload behavior fully controlled by the
# container's CMD/ENV rather than hardcoded in application code, which is
# what lets the same image run identically in docker-compose, ECS, and
# Cloud Run.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]