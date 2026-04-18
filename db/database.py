"""
db/database.py — SQLite Persistence Layer

Provides a thread-safe DatabaseManager that:
- Creates the schema on first run
- Stores threats, vulnerabilities, snapshots, and alert logs
- Exposes query helpers used by the dashboard API
"""

import sqlite3
import threading
import json
import logging
from pathlib import Path
from typing import Optional

import sys, os
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_PATH

logger = logging.getLogger(__name__)


class DatabaseManager:
    _lock = threading.Lock()

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ── Schema ────────────────────────────────────────────────────────────────

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS threats (
                    id          TEXT PRIMARY KEY,
                    timestamp   REAL NOT NULL,
                    severity    TEXT NOT NULL,
                    rule_id     TEXT NOT NULL,
                    source      TEXT DEFAULT 'rules_engine',
                    description TEXT,
                    raw_data    TEXT,
                    resolved    INTEGER DEFAULT 0,
                    risk_score  INTEGER,
                    risk_label  TEXT,
                    mitre_tactic TEXT,
                    mitre_technique TEXT,
                    auto_action_taken TEXT,
                    resolved_status INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS threat_explanations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    threat_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    method TEXT,
                    reasons TEXT,
                    feature_contributions TEXT,
                    FOREIGN KEY(threat_id) REFERENCES threats(id)
                );

                CREATE TABLE IF NOT EXISTS vulnerabilities (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   REAL NOT NULL,
                    scanner     TEXT,
                    port        INTEGER,
                    service     TEXT,
                    severity    TEXT,
                    detail      TEXT
                );

                CREATE TABLE IF NOT EXISTS system_snapshots (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp           REAL NOT NULL,
                    cpu_percent         REAL,
                    memory_percent      REAL,
                    num_processes       INTEGER,
                    num_connections     INTEGER,
                    num_listening_ports INTEGER
                );

                CREATE TABLE IF NOT EXISTS alert_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   REAL NOT NULL,
                    threat_id   TEXT,
                    channel     TEXT,
                    status      TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_threats_ts    ON threats(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_vulns_ts      ON vulnerabilities(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_snapshots_ts  ON system_snapshots(timestamp DESC);
            """)
            self._ensure_columns(conn)
            # Indexes that depend on migrated columns must be created after migration.
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_threats_risk ON threats(risk_score DESC)")
            except Exception:
                pass
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_explain_threat ON threat_explanations(threat_id)")
            except Exception:
                pass
        logger.info("Database schema ready at %s", self.db_path)

    def _ensure_columns(self, conn: sqlite3.Connection) -> None:
        """
        Lightweight migration for existing SQLite files.
        Adds missing columns without destroying data.
        """
        def _cols(table: str) -> set[str]:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return {r["name"] for r in rows}

        # threats table migrations
        tcols = _cols("threats")
        add_cols: list[tuple[str, str]] = []
        if "risk_score" not in tcols:
            add_cols.append(("risk_score", "INTEGER"))
        if "risk_label" not in tcols:
            add_cols.append(("risk_label", "TEXT"))
        if "mitre_tactic" not in tcols:
            add_cols.append(("mitre_tactic", "TEXT"))
        if "mitre_technique" not in tcols:
            add_cols.append(("mitre_technique", "TEXT"))
        if "auto_action_taken" not in tcols:
            add_cols.append(("auto_action_taken", "TEXT"))
        if "resolved_status" not in tcols:
            add_cols.append(("resolved_status", "INTEGER DEFAULT 0"))

        for name, spec in add_cols:
            try:
                conn.execute(f"ALTER TABLE threats ADD COLUMN {name} {spec}")
            except Exception:
                pass

        # threat_explanations may not exist in older DBs
        try:
            conn.execute(
                "SELECT 1 FROM threat_explanations LIMIT 1"
            ).fetchone()
        except Exception:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS threat_explanations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    threat_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    method TEXT,
                    reasons TEXT,
                    feature_contributions TEXT,
                    FOREIGN KEY(threat_id) REFERENCES threats(id)
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Threats ───────────────────────────────────────────────────────────────

    def insert_threat(self, event) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO threats
                       (id, timestamp, severity, rule_id, source, description, raw_data, resolved,
                        risk_score, risk_label, mitre_tactic, mitre_technique, auto_action_taken, resolved_status)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        event.id,
                        event.timestamp,
                        (event.computed_severity or event.severity.value),
                        event.rule_id,
                        event.source,
                        event.description,
                        json.dumps(event.raw_data),
                        int(event.resolved),
                        int(event.risk_score) if event.risk_score is not None else None,
                        event.risk_label,
                        event.mitre_tactic,
                        event.mitre_technique,
                        event.auto_action_taken,
                        int(event.resolved) if getattr(event, "resolved", False) else 0,
                    ),
                )

                # If this event carries ML explanations, persist them separately.
                try:
                    exp = (event.raw_data or {}).get("explanation")
                    if isinstance(exp, dict) and exp.get("reasons"):
                        conn.execute(
                            """INSERT INTO threat_explanations
                               (threat_id, timestamp, method, reasons, feature_contributions)
                               VALUES (?,?,?,?,?)""",
                            (
                                event.id,
                                event.timestamp,
                                exp.get("method"),
                                json.dumps(exp.get("reasons")),
                                json.dumps(exp.get("feature_contributions")),
                            ),
                        )
                except Exception:
                    pass

    def get_threats(self, limit: int = 200, severity: Optional[str] = None) -> list[dict]:
        with self._connect() as conn:
            if severity:
                rows = conn.execute(
                    "SELECT * FROM threats WHERE severity=? ORDER BY timestamp DESC LIMIT ?",
                    (severity, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM threats ORDER BY timestamp DESC LIMIT ?", (limit,)
                ).fetchall()
        return [dict(r) for r in rows]

    def get_threat_counts(self) -> dict:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT severity, COUNT(*) as cnt FROM threats GROUP BY severity"
            ).fetchall()
        return {r["severity"]: r["cnt"] for r in rows}

    # ── Vulnerabilities ───────────────────────────────────────────────────────

    def insert_vulnerability(self, scanner: str, port: int, service: str,
                              severity: str, detail: str) -> None:
        import time
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """INSERT INTO vulnerabilities
                       (timestamp, scanner, port, service, severity, detail)
                       VALUES (?,?,?,?,?,?)""",
                    (time.time(), scanner, port, service, severity, detail),
                )

    def get_vulnerabilities(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM vulnerabilities ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Snapshots ─────────────────────────────────────────────────────────────

    def insert_snapshot(self, snapshot) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """INSERT INTO system_snapshots
                       (timestamp, cpu_percent, memory_percent, num_processes,
                        num_connections, num_listening_ports)
                       VALUES (?,?,?,?,?,?)""",
                    (
                        snapshot.timestamp,
                        snapshot.cpu_percent,
                        snapshot.memory_percent,
                        snapshot.num_processes,
                        len(snapshot.connections),
                        len(snapshot.listening_ports),
                    ),
                )

    def get_snapshots(self, limit: int = 60) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM system_snapshots ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Alert Log ─────────────────────────────────────────────────────────────

    def log_alert(self, threat_id: str, channel: str, status: str) -> None:
        import time
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO alert_log (timestamp, threat_id, channel, status) VALUES (?,?,?,?)",
                    (time.time(), threat_id, channel, status),
                )

    def get_alert_log(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM alert_log ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


# Module-level singleton
db = DatabaseManager()

__all__ = ["DatabaseManager", "db"]
