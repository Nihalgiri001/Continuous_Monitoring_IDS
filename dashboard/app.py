"""
dashboard/app.py — Flask Dashboard API + SSE Server

Endpoints:
  GET  /                   → Dashboard HTML
  GET  /api/status         → Live system stats (latest snapshot)
  GET  /api/threats        → Paginated threat history
  GET  /api/vulnerabilities → Latest scanner results
  GET  /api/intel-stats    → Threat intelligence counts
  GET  /api/stream         → Server-Sent Events stream (live threat feed)
  POST /api/scan           → Trigger on-demand vulnerability scan
  POST /api/export         → Export report (JSON + CSV)
"""

import json
import logging
import time
import threading
from pathlib import Path
from queue import Queue, Empty

from flask import Flask, jsonify, render_template, request, Response, stream_with_context
from flask_cors import CORS

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DASHBOARD_HOST, DASHBOARD_PORT, DASHBOARD_DEBUG, MAX_THREATS_IN_UI

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates")
CORS(app)

# Injected at runtime by main.py
_db            = None
_intel         = None
_port_scanner  = None
_exporter      = None
_session_started_at: float | None = None  # used to scope "this session" vuln report
_latest_snapshot = None
_snapshot_lock  = threading.Lock()

# SSE subscriber queues
_sse_clients: list[Queue] = []
_sse_lock = threading.Lock()


def init_app(db, intel, port_scanner, exporter):
    """Called by main.py to inject dependencies."""
    global _db, _intel, _port_scanner, _exporter, _session_started_at
    _db           = db
    _intel        = intel
    _port_scanner = port_scanner
    _exporter     = exporter
    _session_started_at = time.time()


def push_event_to_sse(event_dict: dict):
    """Called by alert manager to broadcast threats to all SSE clients."""
    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(event_dict)
            except Exception:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


def update_snapshot(snapshot):
    """Called by monitor agent to keep latest snapshot available."""
    global _latest_snapshot
    with _snapshot_lock:
        _latest_snapshot = snapshot


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    with _snapshot_lock:
        snap = _latest_snapshot
    if snap is None:
        return jsonify({"status": "warming_up"})

    return jsonify({
        "status": "ok",
        "cpu_percent": snap.cpu_percent,
        "memory_percent": snap.memory_percent,
        "memory_available_mb": round(snap.memory_available_mb, 1),
        "num_processes": snap.num_processes,
        "num_connections": len(snap.connections),
        "num_listening_ports": len(snap.listening_ports),
        "listening_ports": snap.listening_ports[:20],
        "timestamp": snap.timestamp,
    })


@app.route("/api/threats")
def api_threats():
    if _db is None:
        return jsonify([])
    limit    = min(int(request.args.get("limit", 50)), MAX_THREATS_IN_UI)
    severity = request.args.get("severity")
    threats  = _db.get_threats(limit=limit, severity=severity)
    counts   = _db.get_threat_counts()
    return jsonify({"threats": threats, "counts": counts})


@app.route("/api/risk")
def api_risk():
    """
    Returns a lightweight snapshot of the latest risk posture for UI widgets.
    """
    if _db is None:
        return jsonify({"latest": None})
    threats = _db.get_threats(limit=1)
    latest = threats[0] if threats else None
    return jsonify({"latest": latest})


@app.route("/api/vulnerabilities")
def api_vulnerabilities():
    if _db is None:
        return jsonify([])
    limit = min(int(request.args.get("limit", 50)), 200)
    # Default: unique vulns seen in this dashboard session (since init_app).
    # Use ?all=1 for full historical table (still deduped by port/service/detail).
    all_hist = request.args.get("all", "").lower() in ("1", "true", "yes")
    since = None if all_hist else _session_started_at
    return jsonify(_db.get_vulnerabilities(limit=limit, since_timestamp=since))


@app.route("/api/intel-stats")
def api_intel_stats():
    if _intel is None:
        return jsonify({})
    return jsonify(_intel.stats())


@app.route("/api/stream")
def api_stream():
    """SSE endpoint — clients subscribe here for live threat push."""
    client_q: Queue = Queue(maxsize=100)
    with _sse_lock:
        _sse_clients.append(client_q)

    def generate():
        try:
            yield "data: {\"type\":\"connected\"}\n\n"
            while True:
                try:
                    event = client_q.get(timeout=20)
                    yield f"data: {json.dumps(event, default=str)}\n\n"
                except Empty:
                    yield ": heartbeat\n\n"   # keep-alive
        except GeneratorExit:
            pass
        finally:
            with _sse_lock:
                if client_q in _sse_clients:
                    _sse_clients.remove(client_q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/scan", methods=["POST"])
def api_scan():
    """Trigger an on-demand vulnerability scan in a background thread."""
    if _port_scanner is None:
        return jsonify({"error": "Scanner not initialised"}), 503

    def _run():
        from scanner.port_scanner import run_scan
        from scanner.config_auditor import run_config_audit
        results = run_scan()
        _port_scanner.last_results = results
        if _db:
            for r in results:
                _db.insert_vulnerability(
                    scanner=r["scanner"], port=r["port"], service=r["service"],
                    severity=r["severity"], detail=r["risk_description"],
                )
        audit_events = run_config_audit()
        for e in audit_events:
            if _db:
                _db.insert_threat(e)

    threading.Thread(target=_run, daemon=True, name="OnDemandScan").start()
    return jsonify({"status": "scan_started"})


@app.route("/api/export", methods=["POST"])
def api_export():
    if _exporter is None:
        return jsonify({"error": "Exporter not initialised"}), 503
    try:
        fmt = request.json.get("format", "both") if request.is_json else "both"
        if fmt == "json":
            path = _exporter.export_json()
            return jsonify({"status": "ok", "json": str(path)})
        elif fmt == "csv":
            path = _exporter.export_csv()
            return jsonify({"status": "ok", "csv": str(path)})
        else:
            paths = _exporter.export_both()
            return jsonify({"status": "ok", "json": str(paths["json"]), "csv": str(paths["csv"])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_dashboard():
    logger.info("Dashboard starting at http://%s:%d", DASHBOARD_HOST, DASHBOARD_PORT)
    app.run(
        host=DASHBOARD_HOST,
        port=DASHBOARD_PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


__all__ = ["app", "init_app", "run_dashboard", "push_event_to_sse", "update_snapshot"]
