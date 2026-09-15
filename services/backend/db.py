# Uses PEP 8
# Tools: black, flake8, mypy

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import psycopg2
from psycopg2.extras import RealDictCursor

_env_file = Path(__file__).resolve().parents[2] / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://notification_user:notification_password@127.0.0.1:5432/booking",
)


@contextmanager
def get_conn() -> Iterator[Any]:
    """Yield a PostgreSQL connection with auto-commit/rollback.

    Yields:
        psycopg2 connection using RealDictCursor rows.

    Raises:
        Exception: Re-raised after rollback on query errors.
    """
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
    """Run a SELECT and return all rows as dicts.

    Args:
        conn: Open database connection.
        query: SQL query with optional placeholders.
        params: Query parameters.

    Returns:
        List of row dictionaries.
    """
    with conn.cursor() as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def fetch_one(conn, query: str, params: tuple | None = None) -> dict | None:
    """Run a SELECT and return the first row or None.

    Args:
        conn: Open database connection.
        query: SQL query with optional placeholders.
        params: Query parameters.

    Returns:
        First row as a dict, or None if no rows.
    """
    with conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None


def execute(conn, query: str, params: tuple | None = None) -> None:
    """Run a mutating SQL statement (INSERT/UPDATE/DELETE).

    Args:
        conn: Open database connection.
        query: SQL statement with optional placeholders.
        params: Query parameters.
    """
    with conn.cursor() as cur:
        cur.execute(query, params)
