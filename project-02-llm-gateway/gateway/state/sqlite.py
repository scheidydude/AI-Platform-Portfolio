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
    request_id        TEXT PRIMARY KEY,
    team              TEXT    NOT NULL,
    model             TEXT    NOT NULL,
    backend           TEXT    NOT NULL DEFAULT '',
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_tokens  INTEGER NOT NULL DEFAULT 0,
    latency_ms        INTEGER NOT NULL DEFAULT 0,
    status            TEXT    NOT NULL,
    created_at        TEXT    NOT NULL
);
"""


class SqliteQuotaStore(QuotaStore):
    def __init__(self, path: str = "gateway.db"):
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(_SCHEMA)
            await db.commit()

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
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT OR IGNORE INTO request_log
                   (request_id, team, model, backend, prompt_tokens, completion_tokens,
                    estimated_tokens, latency_ms, status, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    request_id, team, model, backend,
                    prompt_tokens, completion_tokens, estimated_tokens,
                    latency_ms, status,
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
