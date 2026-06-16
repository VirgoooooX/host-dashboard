#!/usr/bin/env python3
"""
host-metrics-exporter

Minimal read-only HTTP metrics exporter for Fleetge.
One endpoint: GET /metrics/json → host CPU/memory/disk/network/load/uptime.

Metrics are collected by a background thread on a fixed interval so HTTP
handlers never block on I/O (especially psutil.cpu_percent(interval=1)).

Environment:
  PORT            - listen port (default: 8000)
  DISK_PATHS      - comma-separated mount points to monitor (default: /)
  COLLECT_INTERVAL- background collection interval in seconds (default: 5)
  METRICS_USER    - optional Basic Auth username (omit = no auth)
  METRICS_PASS    - optional Basic Auth password

Usage:
  python exporter.py
"""

import json
import os
import platform
import signal
import sys
import threading
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
COLLECT_INTERVAL = float(os.environ.get("COLLECT_INTERVAL", "5"))
METRICS_USER = os.environ.get("METRICS_USER", "")
METRICS_PASS = os.environ.get("METRICS_PASS", "")
HOSTNAME = platform.node() or "unknown"

# ---------------------------------------------------------------------------
# Background metrics cache — thread-safe, never blocks HTTP handlers
# ---------------------------------------------------------------------------

_cache_lock = threading.Lock()
_cached_metrics: dict = {}
_last_collect_ok: bool = True


def _safe_float(val, default=0.0) -> float:
    """Return val as float, or default on any error."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _collect_once() -> dict:
    """Perform one full metrics collection (may block up to ~1.5 s).

    Called ONLY from the background thread — never from an HTTP handler.
    """
    # CPU — interval=1 blocks here, which is why this runs in a bg thread
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

    # Network — cumulative counters since boot (sum of all NICs)
    net = psutil.net_io_counters()

    # Disk I/O — cumulative counters since boot
    try:
        disk_io = psutil.disk_io_counters()
        disk_read_bytes = disk_io.read_bytes
        disk_write_bytes = disk_io.write_bytes
    except Exception:
        disk_read_bytes = 0
        disk_write_bytes = 0

    # Load average
    load_raw = psutil.getloadavg()
    load_avg = [round(x, 2) for x in load_raw]

    # Uptime (seconds since boot)
    uptime = int(time.time() - psutil.boot_time())

    # Timestamp (ISO 8601 with milliseconds)
    now_dt = datetime.now(timezone.utc)
    timestamp = now_dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now_dt.microsecond // 1000:03d}Z"

    result: dict = {
        "hostname": HOSTNAME,
        "timestamp": timestamp,
        "cpuPercent": round(cpu, 1),
        "memoryUsed": mem.used,
        "memoryTotal": mem.total,
        "diskUsed": disk_used,
        "diskTotal": disk_total,
        "networkRxBytes": net.bytes_recv,
        "networkTxBytes": net.bytes_sent,
        "diskReadBytes": disk_read_bytes,
        "diskWriteBytes": disk_write_bytes,
        "loadavg": load_avg,
        "uptime": uptime,
    }

    if disk_failures:
        result["_warnings"] = {"diskPathsNotFound": disk_failures}

    return result


def _collector_loop() -> NoReturn:
    """Background thread: collect metrics every COLLECT_INTERVAL seconds."""
    global _cached_metrics, _last_collect_ok

    # First call: prime cpu_percent so subsequent calls have a baseline
    psutil.cpu_percent(interval=None)

    while True:
        try:
            snapshot = _collect_once()
            with _cache_lock:
                _cached_metrics = snapshot
                _last_collect_ok = True
        except Exception as exc:
            with _cache_lock:
                _last_collect_ok = False
            print(f"[exporter] collection failed: {exc}", file=sys.stderr)

        time.sleep(COLLECT_INTERVAL)


def get_cached_metrics() -> dict:
    """Return the most recent snapshot (never blocks on I/O)."""
    with _cache_lock:
        if not _cached_metrics:
            raise RuntimeError("No metrics collected yet — wait for first collection cycle")
        return dict(_cached_metrics)  # shallow copy so caller can't mutate cache


# ---------------------------------------------------------------------------
# HTTP handler — only reads cached metrics, never blocks
# ---------------------------------------------------------------------------


class MetricsHandler(BaseHTTPRequestHandler):
    """Single-endpoint HTTP server returning JSON metrics from cache."""

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
            data = get_cached_metrics()
            self._send_json(200, data)
        except RuntimeError as exc:
            self._send_json(503, {"error": "not_ready", "message": str(exc)})

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
        """Send JSON response. Silently ignores client-disconnect errors."""
        body = json.dumps(data, indent=2, ensure_ascii=False)
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body.encode())
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Client disconnected before or while we responded — not our problem.
            pass

    # -- silence default logging (too noisy) -------------------------------

    def log_message(self, fmt: str, *args) -> None:
        pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> NoReturn:
    # Start background collector
    collector = threading.Thread(target=_collector_loop, daemon=True, name="metrics-collector")
    collector.start()

    # Wait for the first collection to complete so we don't serve empty data
    for _ in range(int(COLLECT_INTERVAL * 2 + 5)):
        with _cache_lock:
            if _cached_metrics:
                break
        time.sleep(0.5)
    else:
        print("[exporter] WARNING: first collection not ready after waiting, starting anyway",
              file=sys.stderr)

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
        f"disk_paths={DISK_PATHS} interval={COLLECT_INTERVAL}s "
        f"auth={'yes' if METRICS_USER else 'no'}",
        file=sys.stderr,
    )

    server.serve_forever()


if __name__ == "__main__":
    main()
