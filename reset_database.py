#!/usr/bin/env python3
"""
reset_database.py — Clear SQLite event data (does NOT touch ML models)

Safe for ML:
  The trained model lives in ml_engine/models/baseline.pkl (and backups).
  This script only empties tables in db/cybercbp.db.

Usage:
  python3 reset_database.py              # interactive confirm
  python3 reset_database.py --yes      # no prompt
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DB_PATH


def clear_tables(conn: sqlite3.Connection) -> None:
    # Order respects FK from threat_explanations → threats
    conn.execute("DELETE FROM threat_explanations")
    conn.execute("DELETE FROM alert_log")
    conn.execute("DELETE FROM system_snapshots")
    conn.execute("DELETE FROM vulnerabilities")
    conn.execute("DELETE FROM threats")
    conn.commit()


def main() -> None:
    ap = argparse.ArgumentParser(description="Clear CyberCBP SQLite tables")
    ap.add_argument("--yes", action="store_true", help="Skip confirmation")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    if not args.yes:
        s = input(f"Delete ALL threats/vulns/snapshots/alerts from {DB_PATH}? [y/N]: ")
        if s.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    conn = sqlite3.connect(str(DB_PATH))
    try:
        clear_tables(conn)
    finally:
        conn.close()

    print("Database cleared. ML model files in ml_engine/models/ were not modified.")


if __name__ == "__main__":
    main()
