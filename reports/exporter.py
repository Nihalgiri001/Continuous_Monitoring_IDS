"""
reports/exporter.py — Report Export Engine

Exports threat data and vulnerability reports to:
  - JSON  (machine-readable, full fidelity)
  - CSV   (spreadsheet-friendly, summary columns)

Usage:
    from reports.exporter import ReportExporter
    exporter = ReportExporter(db)
    path = exporter.export_json()
    path = exporter.export_csv()
"""

import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import REPORTS_DIR

logger = logging.getLogger(__name__)


def _timestamp_str() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class ReportExporter:
    def __init__(self, db):
        self._db = db

    def _build_report_data(self) -> dict:
        threats = self._db.get_threats(limit=1000)
        vulns   = self._db.get_vulnerabilities(limit=500)
        counts  = self._db.get_threat_counts()
        snaps   = self._db.get_snapshots(limit=100)

        return {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_threats": len(threats),
                "severity_breakdown": counts,
                "total_vulnerabilities": len(vulns),
                "snapshots_collected": len(snaps),
            },
            "threats": threats,
            "vulnerabilities": vulns,
        }

    # ── JSON Export ───────────────────────────────────────────────────────────

    def export_json(self, filename: str | None = None) -> Path:
        filename = filename or f"report_{_timestamp_str()}.json"
        out_path = REPORTS_DIR / filename

        data = self._build_report_data()
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info("JSON report exported → %s", out_path)
        return out_path

    # ── CSV Export ────────────────────────────────────────────────────────────

    def export_csv(self, filename: str | None = None) -> Path:
        filename = filename or f"report_{_timestamp_str()}.csv"
        out_path = REPORTS_DIR / filename

        data = self._build_report_data()
        threats = data["threats"]
        vulns   = data["vulnerabilities"]

        with open(out_path, "w", newline="") as f:
            writer = csv.writer(f)

            # ── Metadata header ──
            writer.writerow(["CyberCBP Security Report"])
            writer.writerow(["Generated At", data["generated_at"]])
            writer.writerow(["Total Threats", data["summary"]["total_threats"]])
            writer.writerow(["Total Vulnerabilities", data["summary"]["total_vulnerabilities"]])
            writer.writerow([])

            # ── Threats table ──
            writer.writerow(["=== THREATS ==="])
            writer.writerow(["ID", "Timestamp", "Severity", "Rule ID", "Source", "Description"])
            for t in threats:
                ts = datetime.fromtimestamp(t["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([
                    t["id"][:8] + "…",
                    ts,
                    t["severity"],
                    t["rule_id"],
                    t.get("source", ""),
                    t.get("description", ""),
                ])
            writer.writerow([])

            # ── Vulnerabilities table ──
            writer.writerow(["=== VULNERABILITIES ==="])
            writer.writerow(["ID", "Timestamp", "Scanner", "Port", "Service", "Severity", "Detail"])
            for v in vulns:
                ts = datetime.fromtimestamp(v["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([
                    v["id"],
                    ts,
                    v.get("scanner", ""),
                    v.get("port", ""),
                    v.get("service", ""),
                    v.get("severity", ""),
                    v.get("detail", ""),
                ])

        logger.info("CSV report exported → %s", out_path)
        return out_path

    def export_both(self) -> dict[str, Path]:
        """Export both formats and return paths dict."""
        ts = _timestamp_str()
        return {
            "json": self.export_json(f"report_{ts}.json"),
            "csv":  self.export_csv(f"report_{ts}.csv"),
        }


__all__ = ["ReportExporter"]
