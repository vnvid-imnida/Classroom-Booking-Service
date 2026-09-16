"""Sync RUZ room schedules into bookings (source=RUZ)."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from psycopg2 import errors as pg_errors

from config import BUILDING_CODE_TO_RUZ_ABBR, RUZ_BASE_URL, RUZ_SYNC_WEEKS
from db import execute, fetch_all, fetch_one, get_conn
from ruz_client import RuzClient

logger = logging.getLogger(__name__)

try:
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")
except ZoneInfoNotFoundError:
    MOSCOW_TZ = timezone(timedelta(hours=3))

_sync_lock = threading.Lock()
_last_result: dict | None = None


@dataclass
class SyncStats:
    sync_run_id: int | None = None
    mapped_rooms: int = 0
    imported: int = 0
    updated: int = 0
    completed_stale: int = 0
    conflicts: int = 0
    skipped_unmapped: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "sync_run_id": self.sync_run_id,
            "mapped_rooms": self.mapped_rooms,
            "imported": self.imported,
            "updated": self.updated,
            "completed_stale": self.completed_stale,
            "conflicts": self.conflicts,
            "skipped_unmapped": self.skipped_unmapped,
            "errors": self.errors[:20],
            "error_count": len(self.errors),
        }


def _moscow_pair_bounds(day: str, time_start: str, time_end: str) -> tuple[datetime, datetime]:
    """Convert Moscow wall-clock pair times to aware UTC datetimes."""
    start_local = datetime.strptime(f"{day} {time_start}", "%Y-%m-%d %H:%M").replace(tzinfo=MOSCOW_TZ)
    end_local = datetime.strptime(f"{day} {time_end}", "%Y-%m-%d %H:%M").replace(tzinfo=MOSCOW_TZ)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _external_event_id(ruz_room_id: int, day: str, time_start: str, time_end: str, subject: str) -> str:
    # Stable key: RUZ has no lesson id; room+day+interval is unique enough in practice.
    subj = (subject or "").strip().replace("|", "/")[:80]
    return f"ruz:{ruz_room_id}:{day}:{time_start}-{time_end}:{subj}"


def _week_anchor_dates(weeks: int, today: date | None = None) -> list[str]:
    """Return YYYY-MM-DD anchors (Mondays) for the next ``weeks`` weeks including current."""
    base = today or datetime.now(MOSCOW_TZ).date()
    monday = base - timedelta(days=base.weekday())  # Mon=0
    return [(monday + timedelta(weeks=i)).isoformat() for i in range(max(1, weeks))]


def _load_local_rooms(conn) -> list[dict]:
    return fetch_all(
        conn,
        """
        SELECT r.id AS room_id, r.room_number, b.id AS building_id, b.code AS building_code
        FROM rooms r
        JOIN buildings b ON b.id = r.building_id
        WHERE r.is_active = true
        ORDER BY b.code, r.room_number
        """,
    )


def _map_rooms(client: RuzClient, local_rooms: list[dict], stats: SyncStats) -> list[dict]:
    """Attach RUZ building/room ids to local rooms via abbr + room name."""
    ruz_buildings = client.buildings()
    abbr_to_id = {str(b.get("abbr") or "").strip(): int(b["id"]) for b in ruz_buildings if b.get("id")}

    # Cache rooms per RUZ building.
    rooms_by_building: dict[int, dict[str, int]] = {}

    mapped: list[dict] = []
    for room in local_rooms:
        code = room["building_code"]
        abbr = BUILDING_CODE_TO_RUZ_ABBR.get(code)
        if not abbr:
            stats.skipped_unmapped += 1
            continue
        ruz_building_id = abbr_to_id.get(abbr)
        if ruz_building_id is None:
            stats.errors.append(f"RUZ building not found for abbr={abbr!r} (local code={code!r})")
            stats.skipped_unmapped += 1
            continue

        if ruz_building_id not in rooms_by_building:
            name_to_id: dict[str, int] = {}
            for rr in client.rooms(ruz_building_id):
                name = str(rr.get("name") or "").strip()
                if name and rr.get("id") is not None:
                    name_to_id[name] = int(rr["id"])
            rooms_by_building[ruz_building_id] = name_to_id

        ruz_room_id = rooms_by_building[ruz_building_id].get(str(room["room_number"]).strip())
        if ruz_room_id is None:
            stats.skipped_unmapped += 1
            continue

        mapped.append(
            {
                **room,
                "ruz_building_id": ruz_building_id,
                "ruz_room_id": ruz_room_id,
            }
        )

    stats.mapped_rooms = len(mapped)
    return mapped


def _upsert_lesson(
    conn,
    *,
    room_id: int,
    title: str,
    description: str | None,
    starts_at: datetime,
    ends_at: datetime,
    external_event_id: str,
    sync_run_id: int,
    stats: SyncStats,
) -> None:
    existing = fetch_one(
        conn,
        """
        SELECT id::text, starts_at, ends_at, title, status
        FROM bookings
        WHERE source = 'RUZ' AND external_event_id = %s
        """,
        (external_event_id,),
    )
    try:
        if existing:
            execute(
                conn,
                """
                UPDATE bookings
                SET title = %s,
                    description = %s,
                    starts_at = %s,
                    ends_at = %s,
                    status = 'ACTIVE',
                    sync_run_id = %s,
                    cancelled_by = NULL,
                    cancelled_at = NULL,
                    cancel_reason = NULL
                WHERE id = %s::uuid
                """,
                (title, description, starts_at, ends_at, sync_run_id, existing["id"]),
            )
            stats.updated += 1
        else:
            execute(
                conn,
                """
                INSERT INTO bookings (
                    room_id, title, description, starts_at, ends_at,
                    source, status, external_event_id, sync_run_id
                )
                VALUES (%s, %s, %s, %s, %s, 'RUZ', 'ACTIVE', %s, %s)
                """,
                (room_id, title, description, starts_at, ends_at, external_event_id, sync_run_id),
            )
            stats.imported += 1
    except pg_errors.ExclusionViolation:
        # Caller rolls back to a savepoint and counts the conflict.
        raise


def run_sync(*, weeks: int | None = None, client: RuzClient | None = None) -> dict:
    """Pull RUZ schedules for mapped rooms and upsert into bookings.

    Returns:
        Stats dict including sync_run_id and counts.
    """
    global _last_result
    if not _sync_lock.acquire(blocking=False):
        return {"status": "busy", "message": "Sync already running", **((_last_result or {}))}

    stats = SyncStats()
    weeks = weeks if weeks is not None else RUZ_SYNC_WEEKS
    client = client or RuzClient()
    anchors = _week_anchor_dates(weeks)
    window_start = datetime.strptime(anchors[0], "%Y-%m-%d").replace(tzinfo=MOSCOW_TZ).astimezone(timezone.utc)
    window_end = (
        datetime.strptime(anchors[-1], "%Y-%m-%d").replace(tzinfo=MOSCOW_TZ) + timedelta(days=7)
    ).astimezone(timezone.utc)

    try:
        with get_conn() as conn:
            run = fetch_one(
                conn,
                """
                INSERT INTO ruz_sync_runs (status, source_url, imported_slots_count)
                VALUES ('RUNNING', %s, 0)
                RETURNING id
                """,
                (RUZ_BASE_URL,),
            )
            assert run is not None
            sync_run_id = int(run["id"])
            stats.sync_run_id = sync_run_id

            local_rooms = _load_local_rooms(conn)

        # Network I/O outside a long DB transaction.
        mapped = _map_rooms(client, local_rooms, stats)
        seen_external_ids: set[str] = set()
        pending: list[dict] = []

        for room in mapped:
            for anchor in anchors:
                try:
                    payload = client.room_scheduler(room["ruz_building_id"], room["ruz_room_id"], anchor)
                except Exception as exc:  # noqa: BLE001 — collect and continue
                    msg = f"scheduler room={room['room_number']} building={room['building_code']}: {exc}"
                    logger.warning(msg)
                    stats.errors.append(msg)
                    continue

                for day in payload.get("days") or []:
                    day_str = str(day.get("date") or "")
                    if not day_str:
                        continue
                    for lesson in day.get("lessons") or []:
                        t0 = str(lesson.get("time_start") or "")
                        t1 = str(lesson.get("time_end") or "")
                        subject = str(lesson.get("subject") or lesson.get("subject_short") or "Занятие")
                        if not t0 or not t1:
                            continue
                        try:
                            starts_at, ends_at = _moscow_pair_bounds(day_str, t0, t1)
                        except ValueError as exc:
                            stats.errors.append(f"bad time {day_str} {t0}-{t1}: {exc}")
                            continue
                        if ends_at <= starts_at:
                            continue
                        ext_id = _external_event_id(room["ruz_room_id"], day_str, t0, t1, subject)
                        seen_external_ids.add(ext_id)
                        type_name = ""
                        type_obj = lesson.get("typeObj") or {}
                        if isinstance(type_obj, dict):
                            type_name = str(type_obj.get("abbr") or type_obj.get("name") or "")
                        title = f"{subject}" + (f" ({type_name})" if type_name else "")
                        teachers = lesson.get("teachers") or []
                        teacher_names = ", ".join(
                            str(t.get("full_name") or "").strip() for t in teachers if t.get("full_name")
                        )
                        pending.append(
                            {
                                "room_id": room["room_id"],
                                "title": title[:500],
                                "description": teacher_names or None,
                                "starts_at": starts_at,
                                "ends_at": ends_at,
                                "external_event_id": ext_id,
                            }
                        )

        with get_conn() as conn:
            for item in pending:
                try:
                    # Nested savepoint so one exclusion conflict does not abort the batch.
                    with conn.cursor() as cur:
                        cur.execute("SAVEPOINT ruz_lesson")
                    try:
                        _upsert_lesson(conn, sync_run_id=stats.sync_run_id, stats=stats, **item)
                        with conn.cursor() as cur:
                            cur.execute("RELEASE SAVEPOINT ruz_lesson")
                    except pg_errors.ExclusionViolation:
                        with conn.cursor() as cur:
                            cur.execute("ROLLBACK TO SAVEPOINT ruz_lesson")
                        stats.conflicts += 1
                        logger.info(
                            "Skip RUZ slot overlapping MANUAL booking: %s",
                            item["external_event_id"],
                        )
                except Exception as exc:  # noqa: BLE001
                    stats.errors.append(f"upsert {item['external_event_id']}: {exc}")
                    try:
                        with conn.cursor() as cur:
                            cur.execute("ROLLBACK TO SAVEPOINT ruz_lesson")
                    except Exception:  # noqa: BLE001
                        pass

            if seen_external_ids:
                # Complete ACTIVE RUZ slots in the window that disappeared from RUZ.
                rows = fetch_all(
                    conn,
                    """
                    SELECT id::text, external_event_id
                    FROM bookings
                    WHERE source = 'RUZ'
                      AND status = 'ACTIVE'
                      AND starts_at >= %s
                      AND starts_at < %s
                    """,
                    (window_start, window_end),
                )
                stale_ids = [r["id"] for r in rows if r["external_event_id"] not in seen_external_ids]
                for booking_id in stale_ids:
                    execute(
                        conn,
                        """
                        UPDATE bookings
                        SET status = 'COMPLETED', sync_run_id = %s
                        WHERE id = %s::uuid AND source = 'RUZ' AND status = 'ACTIVE'
                        """,
                        (stats.sync_run_id, booking_id),
                    )
                    stats.completed_stale += 1
            else:
                # If RUZ returned nothing for all rooms, do not wipe the window.
                logger.warning("No RUZ lessons collected; skipping stale completion")

            status = "FAILED" if stats.mapped_rooms == 0 and stats.errors else "SUCCESS"

            execute(
                conn,
                """
                UPDATE ruz_sync_runs
                SET finished_at = now(),
                    status = %s,
                    imported_slots_count = %s,
                    error_message = %s
                WHERE id = %s
                """,
                (
                    status,
                    stats.imported + stats.updated,
                    "; ".join(stats.errors[:5]) if stats.errors else None,
                    stats.sync_run_id,
                ),
            )

        result = {"status": "ok", **stats.as_dict()}
        _last_result = result
        logger.info("RUZ sync finished: %s", result)
        return result
    except Exception as exc:
        logger.exception("RUZ sync failed")
        try:
            with get_conn() as conn:
                if stats.sync_run_id:
                    execute(
                        conn,
                        """
                        UPDATE ruz_sync_runs
                        SET finished_at = now(), status = 'FAILED', error_message = %s
                        WHERE id = %s AND status = 'RUNNING'
                        """,
                        (str(exc)[:1000], stats.sync_run_id),
                    )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to mark sync run as FAILED")
        result = {"status": "error", "message": str(exc), **stats.as_dict()}
        _last_result = result
        return result
    finally:
        _sync_lock.release()


def last_sync_result() -> dict | None:
    return _last_result


def is_sync_running() -> bool:
    acquired = _sync_lock.acquire(blocking=False)
    if acquired:
        _sync_lock.release()
        return False
    return True
