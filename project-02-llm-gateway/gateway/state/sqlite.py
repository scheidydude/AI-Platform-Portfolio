from __future__ import annotations
from datetime import datetime, timezone
import aiosqlite
from .base import QuotaStore

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS team_quota (
    team        TEXT    NOT NULL,
    month       TEXT    NOT NULL,
    tokens_used INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (team, month)
);

CREATE TABLE IF NOT EXISTS request_log (
    request_id        TEXT    PRIMARY KEY,
    team              TEXT    NOT NULL,
    model             TEXT    NOT NULL,
    backend           TEXT    NOT NULL DEFAULT '',
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_tokens  INTEGER NOT NULL DEFAULT 0,
    latency_ms        INTEGER NOT NULL DEFAULT 0,
    status            TEXT    NOT NULL,
    cost_usd          REAL    NOT NULL DEFAULT 0.0,
    created_at        TEXT    NOT NULL
);
"""


class SqliteQuotaStore(QuotaStore):
    def __init__(self, path: str = "gateway.db"):
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(_SCHEMA)
            # Additive migration: add cost_usd if upgrading from Phase 1 DB
            try:
                await db.execute(
                    "ALTER TABLE request_log ADD COLUMN cost_usd REAL NOT NULL DEFAULT 0.0"
                )
                await db.commit()
            except Exception:
                pass  # Column already exists — expected on fresh installs using _SCHEMA above

    async def get_usage(self, team: str, month: str) -> int:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT tokens_used FROM team_quota WHERE team=? AND month=?",
                (team, month),
            ) as cur:
                row = await cur.fetchone()
        return row[0] if row else 0

    async def increment(self, team: str, month: str, tokens: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO team_quota (team, month, tokens_used) VALUES (?, ?, ?)
                   ON CONFLICT(team, month)
                   DO UPDATE SET tokens_used = tokens_used + excluded.tokens_used""",
                (team, month, tokens),
            )
            await db.commit()
            async with db.execute(
                "SELECT tokens_used FROM team_quota WHERE team=? AND month=?",
                (team, month),
            ) as cur:
                row = await cur.fetchone()
        return row[0] if row else tokens

    async def reset(self, team: str, month: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE team_quota SET tokens_used=0 WHERE team=? AND month=?",
                (team, month),
            )
            await db.commit()

    async def log_request(
        self,
        *,
        request_id: str,
        team: str,
        model: str,
        backend: str,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_tokens: int,
        latency_ms: int,
        status: str,
        cost_usd: float,
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT OR IGNORE INTO request_log
                   (request_id, team, model, backend, prompt_tokens, completion_tokens,
                    estimated_tokens, latency_ms, status, cost_usd, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    request_id, team, model, backend,
                    prompt_tokens, completion_tokens, estimated_tokens,
                    latency_ms, status, cost_usd,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await db.commit()

    async def get_all_usage(self, month: str) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT team, tokens_used FROM team_quota WHERE month=? ORDER BY tokens_used DESC",
                (month,),
            ) as cur:
                rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def get_all_usage_with_cost(self, month: str) -> dict[str, dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT
                       tq.team,
                       tq.tokens_used,
                       COALESCE(rl.cost_usd, 0.0) AS cost_usd
                   FROM team_quota tq
                   LEFT JOIN (
                       SELECT team, SUM(cost_usd) AS cost_usd
                       FROM request_log
                       WHERE created_at LIKE ?
                       GROUP BY team
                   ) rl ON rl.team = tq.team
                   WHERE tq.month = ?""",
                (f"{month}%", month),
            ) as cur:
                rows = await cur.fetchall()
        return {r["team"]: dict(r) for r in rows}

    async def get_daily_usage(self, month: str) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT
                       date(created_at) AS date,
                       SUM(prompt_tokens + completion_tokens) AS tokens,
                       COUNT(*) AS requests,
                       SUM(cost_usd) AS cost_usd
                   FROM request_log
                   WHERE created_at LIKE ?
                   GROUP BY date(created_at)
                   ORDER BY date""",
                (f"{month}%",),
            ) as cur:
                rows = await cur.fetchall()
        return [dict(r) for r in rows]
