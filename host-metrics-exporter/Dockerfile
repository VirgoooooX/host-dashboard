FROM python:3.12-slim

WORKDIR /app

# Install only psutil — no build deps needed for pure wheels on amd64/arm64
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY exporter.py .

EXPOSE 8000

# Run as non-root
RUN addgroup --system --gid 1001 exporter && \
    adduser --system --uid 1001 --ingroup exporter exporter && \
    chown exporter:exporter /app
USER exporter

HEALTHCHECK --interval=30s --timeout=5s --retries=2 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/metrics/json')" || exit 1

ENTRYPOINT ["python", "exporter.py"]
