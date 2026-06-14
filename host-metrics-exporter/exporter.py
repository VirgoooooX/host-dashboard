#!/usr/bin/env python3
"""
host-metrics-exporter

Minimal read-only HTTP metrics exporter for Docker Dashboard.
One endpoint: GET /metrics/json → host CPU/memory/disk/load/uptime.

Environment:
  PORT          - listen port (default: 8000)
  DISK_PATHS    - comma-separated mount points to monitor (default: /)
  METRICS_USER  - optional Basic Auth username (omit = no auth)
  METRICS_PASS  - optional Basic Auth password

Usage:
  python exporter.py
"""

import json
import os
import platform
import signal
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
from typing import NoReturn

try:
    import psutil
except ImportError:
    print("ERROR: psutil is required. Install with: pip install psutil", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PORT = int(os.environ.get("PORT", "8000"))
DISK_PATHS = [p.strip() for p in os.environ.get("DISK_PATHS", "/").split(",") if p.strip()]
METRICS_USER = os.environ.get("METRICS_USER", "")
METRICS_PASS = os.environ.get("METRICS_PASS", "")
HOSTNAME = platform.node() or "unknown"

# ---------------------------------------------------------------------------
# Metrics collection
# ---------------------------------------------------------------------------


def collect() -> dict:
    """Return a snapshot of host metrics."""
    # CPU
    cpu = psutil.cpu_percent(interval=1)

    # Memory
    mem = psutil.virtual_memory()

    # Disk — sum usage across configured mount points
    disk_used: int = 0
    disk_total: int = 0
    disk_failures: list[str] = []
    for path in DISK_PATHS:
        try:
            usage = psutil.disk_usage(path)
            disk_used += usage.used
            disk_total += usage.total
        except FileNotFoundError:
            disk_failures.append(path)

    # Load average
    load_raw = psutil.getloadavg()
    load_avg = [round(x, 2) for x in load_raw]

    # Uptime (seconds since boot)
    uptime = int(time.time() - psutil.boot_time())

    # Timestamp (ISO 8601 with milliseconds)
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"

    result: dict = {
        "hostname": HOSTNAME,
        "timestamp": timestamp,
        "cpuPercent": round(cpu, 1),
        "memoryUsed": mem.used,
        "memoryTotal": mem.total,
        "diskUsed": disk_used,
        "diskTotal": disk_total,
        "loadavg": load_avg,
        "uptime": uptime,
    }

    if disk_failures:
        result["_warnings"] = {"diskPathsNotFound": disk_failures}

    return result


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


class MetricsHandler(BaseHTTPRequestHandler):
    """Single-endpoint HTTP server returning JSON metrics."""

    def do_GET(self) -> None:
        if self.path != "/metrics/json":
            self._send_json(404, {"error": "not_found", "message": f"Unknown path: {self.path}"})
            return

        # Basic Auth check
        if METRICS_USER or METRICS_PASS:
            if not self._check_auth():
                self._send_auth_required()
                return

        try:
            data = collect()
            self._send_json(200, data)
        except Exception as exc:
            self._send_json(500, {"error": "collection_failed", "message": str(exc)})

    def do_HEAD(self) -> None:
        """Health-check via HEAD /metrics/json — returns only headers."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    # -- helpers -----------------------------------------------------------

    def _check_auth(self) -> bool:
        """Validate Basic Auth header against METRICS_USER / METRICS_PASS."""
        import base64

        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
            user, _, pw = decoded.partition(":")
            return user == METRICS_USER and pw == METRICS_PASS
        except Exception:
            return False

    def _send_auth_required(self) -> None:
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="metrics"')
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "unauthorized"}).encode())

    def _send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data, indent=2, ensure_ascii=False)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body.encode())

    # -- silence default logging (too noisy) -------------------------------

    def log_message(self, fmt: str, *args) -> None:
        pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> NoReturn:
    server = HTTPServer(("0.0.0.0", PORT), MetricsHandler)

    # Graceful shutdown
    def shutdown(sig, frame) -> None:
        print(f"\n[exporter] Received signal {sig}, shutting down.", file=sys.stderr)
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    print(
        f"[exporter] host={HOSTNAME} listening on 0.0.0.0:{PORT} "
        f"disk_paths={DISK_PATHS} auth={'yes' if METRICS_USER else 'no'}",
        file=sys.stderr,
    )

    server.serve_forever()


if __name__ == "__main__":
    main()
