"""PostgreSQL helpers for the parser service."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import psycopg2
from psycopg2.extras import RealDictCursor

from config import DATABASE_URL


@contextmanager
def get_conn() -> Iterator[Any]:
    """Yield a PostgreSQL connection with commit/rollback."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn.set_client_encoding("UTF8")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(conn, query: str, params: tuple | None = None) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def fetch_one(conn, query: str, params: tuple | None = None) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None


def execute(conn, query: str, params: tuple | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(query, params)
