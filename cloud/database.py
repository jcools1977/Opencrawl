"""
ConvoYield Cloud Database — SQLite-powered analytics storage.

Zero infrastructure cost. The entire analytics platform runs on a single
SQLite file. At scale, swap to PostgreSQL with zero code changes to queries.
"""

from __future__ import annotations

import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


DB_PATH = os.environ.get("CONVOYIELD_DB", str(Path.home() / ".convoyield" / "analytics.db"))


class Database:
    def __init__(self, db_path: str = DB_PATH):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                company TEXT,
                tier TEXT DEFAULT 'free',
                api_key TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                active_playbooks TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS yield_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                turn_number INTEGER,
                timestamp TEXT NOT NULL,
                sentiment REAL,
                sentiment_delta REAL,
                momentum REAL,
                estimated_yield REAL,
                captured_yield REAL,
                phase TEXT,
                risk_level REAL,
                recommended_play TEXT,
                arbitrage_types TEXT DEFAULT '[]',
                micro_conversion_types TEXT DEFAULT '[]',
                user_message_length INTEGER DEFAULT 0,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );

            CREATE TABLE IF NOT EXISTS conversions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                conversion_type TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                session_id TEXT UNIQUE NOT NULL,
                total_turns INTEGER,
                estimated_yield REAL,
                captured_yield REAL,
                final_phase TEXT,
                final_sentiment REAL,
                duration_seconds REAL,
                plays_recommended TEXT DEFAULT '[]',
                arbitrage_detected TEXT DEFAULT '[]',
                conversions_captured TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );

            CREATE TABLE IF NOT EXISTS webhooks (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                url TEXT NOT NULL,
                events TEXT DEFAULT '[]',
                threshold REAL DEFAULT 100.0,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );

            CREATE INDEX IF NOT EXISTS idx_events_account ON yield_events(account_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_session ON yield_events(session_id);
            CREATE INDEX IF NOT EXISTS idx_conversions_account ON conversions(account_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_sessions_account ON sessions(account_id, created_at);
        """)
        self._conn.commit()

    # ── Account Management ────────────────────────────────────────────────

    def create_account(self, account_id: str, email: str, company: Optional[str],
                       tier: str, api_key: str):
        self._conn.execute(
            "INSERT INTO accounts (id, email, company, tier, api_key) VALUES (?, ?, ?, ?, ?)",
            (account_id, email, company, tier, api_key),
        )
        self._conn.commit()

    def get_account_by_key(self, api_key: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM accounts WHERE api_key = ?", (api_key,)
        ).fetchone()
        return dict(row) if row else None

    def activate_playbook(self, account_id: str, playbook_id: str):
        row = self._conn.execute(
            "SELECT active_playbooks FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if row:
            playbooks = json.loads(row["active_playbooks"])
            if playbook_id not in playbooks:
                playbooks.append(playbook_id)
            self._conn.execute(
                "UPDATE accounts SET active_playbooks = ? WHERE id = ?",
                (json.dumps(playbooks), account_id),
            )
            self._conn.commit()

    # ── Event Ingestion ───────────────────────────────────────────────────

    def insert_yield_event(self, **kwargs):
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" * len(kwargs))
        self._conn.execute(
            f"INSERT INTO yield_events ({cols}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        self._conn.commit()

    def insert_conversion(self, **kwargs):
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" * len(kwargs))
        self._conn.execute(
            f"INSERT INTO conversions ({cols}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        self._conn.commit()

    def insert_session_summary(self, **kwargs):
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" * len(kwargs))
        self._conn.execute(
            f"INSERT OR REPLACE INTO sessions ({cols}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        self._conn.commit()

    # ── Analytics Queries ─────────────────────────────────────────────────

    def get_overview_stats(self, account_id: str, since: str) -> dict:
        row = self._conn.execute("""
            SELECT
                COUNT(DISTINCT session_id) as total_sessions,
                COUNT(*) as total_turns,
                COALESCE(SUM(estimated_yield), 0) as total_estimated_yield,
                COALESCE(SUM(captured_yield), 0) as total_captured_yield,
                COALESCE(AVG(estimated_yield), 0) as avg_yield_per_session,
                COALESCE(AVG(sentiment), 0) as avg_sentiment,
                COALESCE(AVG(momentum), 0) as avg_momentum,
                COALESCE(AVG(risk_level), 0) as avg_risk
            FROM yield_events
            WHERE account_id = ? AND timestamp >= ?
        """, (account_id, since)).fetchone()
        return dict(row) if row else {
            "total_sessions": 0, "total_turns": 0,
            "total_estimated_yield": 0, "total_captured_yield": 0,
            "avg_yield_per_session": 0, "avg_sentiment": 0,
            "avg_momentum": 0, "avg_risk": 0,
        }

    def get_play_stats(self, account_id: str, since: str) -> list[dict]:
        rows = self._conn.execute("""
            SELECT
                recommended_play as play,
                COUNT(*) as count,
                AVG(estimated_yield) as avg_yield,
                AVG(captured_yield) as avg_captured
            FROM yield_events
            WHERE account_id = ? AND timestamp >= ? AND recommended_play IS NOT NULL
            GROUP BY recommended_play
            ORDER BY count DESC
        """, (account_id, since)).fetchall()
        return [dict(r) for r in rows]

    def get_arbitrage_stats(self, account_id: str, since: str) -> list[dict]:
        rows = self._conn.execute("""
            SELECT arbitrage_types, estimated_yield
            FROM yield_events
            WHERE account_id = ? AND timestamp >= ? AND arbitrage_types != '[]'
        """, (account_id, since)).fetchall()

        type_stats: dict[str, dict] = {}
        for row in rows:
            types = json.loads(row["arbitrage_types"])
            for t in types:
                if t not in type_stats:
                    type_stats[t] = {"type": t, "count": 0, "total_yield": 0.0}
                type_stats[t]["count"] += 1
                type_stats[t]["total_yield"] += row["estimated_yield"]

        result = sorted(type_stats.values(), key=lambda x: x["count"], reverse=True)
        return result

    def get_conversion_stats(self, account_id: str, since: str) -> list[dict]:
        rows = self._conn.execute("""
            SELECT
                conversion_type,
                COUNT(*) as count,
                SUM(value) as total_value,
                AVG(value) as avg_value
            FROM conversions
            WHERE account_id = ? AND timestamp >= ?
            GROUP BY conversion_type
            ORDER BY total_value DESC
        """, (account_id, since)).fetchall()
        return [dict(r) for r in rows]

    def get_yield_timeline(self, account_id: str, since: str,
                           granularity: str = "hour") -> list[dict]:
        if granularity == "hour":
            time_fmt = "%Y-%m-%d %H:00"
        elif granularity == "day":
            time_fmt = "%Y-%m-%d"
        else:
            time_fmt = "%Y-%m-%d %H:00"

        rows = self._conn.execute(f"""
            SELECT
                strftime('{time_fmt}', timestamp) as period,
                COUNT(DISTINCT session_id) as sessions,
                SUM(estimated_yield) as estimated,
                SUM(captured_yield) as captured,
                AVG(sentiment) as avg_sentiment,
                AVG(momentum) as avg_momentum
            FROM yield_events
            WHERE account_id = ? AND timestamp >= ?
            GROUP BY period
            ORDER BY period
        """, (account_id, since)).fetchall()
        return [dict(r) for r in rows]

    def get_sessions(self, account_id: str, limit: int = 50,
                     offset: int = 0) -> list[dict]:
        rows = self._conn.execute("""
            SELECT * FROM sessions
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (account_id, limit, offset)).fetchall()
        return [dict(r) for r in rows]

    def get_leaderboard(self, account_id: str, since: str) -> list[dict]:
        rows = self._conn.execute("""
            SELECT
                session_id,
                MAX(estimated_yield) as peak_yield,
                MAX(captured_yield) as captured,
                COUNT(*) as turns,
                MAX(phase) as last_phase
            FROM yield_events
            WHERE account_id = ? AND timestamp >= ?
            GROUP BY session_id
            ORDER BY peak_yield DESC
            LIMIT 20
        """, (account_id, since)).fetchall()
        return [dict(r) for r in rows]

    def count_events_today(self, account_id: str) -> int:
        row = self._conn.execute("""
            SELECT COUNT(*) as cnt FROM yield_events
            WHERE account_id = ? AND timestamp >= date('now')
        """, (account_id,)).fetchone()
        return row["cnt"] if row else 0

    def create_webhook(self, account_id: str, webhook_id: str, url: str,
                       events: str, threshold: float):
        self._conn.execute(
            "INSERT INTO webhooks (id, account_id, url, events, threshold) VALUES (?, ?, ?, ?, ?)",
            (webhook_id, account_id, url, events, threshold),
        )
        self._conn.commit()

    def close(self):
        self._conn.close()
