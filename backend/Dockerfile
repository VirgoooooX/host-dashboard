FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ──────────────────────────────────────────────────────

FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY app/ ./app/

# Create data directory for SQLite
RUN mkdir -p /app/data

# Non-root user
RUN addgroup --system --gid 1001 dashboard && \
    adduser --system --uid 1001 --ingroup dashboard dashboard && \
    chown -R dashboard:dashboard /app
USER dashboard

EXPOSE 8000

# Single worker — in-memory rate limit + SQLite WAL
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
