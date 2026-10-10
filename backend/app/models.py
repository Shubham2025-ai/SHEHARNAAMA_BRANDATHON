"""Data-access functions for registrations (parameterised SQL only)."""

import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from . import database

STATUS_VALUES = ("INTEREST_RECEIVED", "CONTACTED", "WAITLISTED", "CLOSED")
EXPERIENCE_TYPES = ("peth-stories-walk", "private-group")
SESSION_STATUS_VALUES = ("DRAFT", "PUBLISHED", "CANCELLED", "COMPLETED")

_LIST_COLUMNS = (
    "r.id, r.public_reference, r.full_name, r.email, r.experience_type, "
    "r.preferred_date, r.guest_count, r.status, r.created_at, "
    "r.session_id, ws.title AS session_title"
)


def today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def generate_reference() -> str:
    """Server-generated public reference, e.g. SH-2026-9F4C2A."""
    year = datetime.now(timezone.utc).strftime("%Y")
    return f"SH-{year}-{secrets.token_hex(3).upper()}"


def create_registration(
    *,
    full_name: str,
    email: str,
    preferred_date: Optional[str],
    guest_count: int,
    experience_type: str,
    notes: Optional[str],
    idempotency_key: Optional[str],
    session_id: Optional[int] = None,
) -> dict[str, Any]:
    """Insert a registration. Honours idempotency keys; never overwrites."""
    now = utcnow()
    with database.get_connection() as conn:
        if idempotency_key:
            existing = conn.execute(
                "SELECT * FROM registrations WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing:
                return {"record": dict(existing), "idempotent": True}

        reference = generate_reference()
        for _ in range(6):
            try:
                conn.execute(
                    """
                    INSERT INTO registrations (
                        public_reference, full_name, email, preferred_date,
                        guest_count, experience_type, notes, consent, status,
                        idempotency_key, session_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'INTEREST_RECEIVED', ?, ?, ?, ?)
                    """,
                    (
                        reference,
                        full_name,
                        email,
                        preferred_date,
                        guest_count,
                        experience_type,
                        notes,
                        idempotency_key,
                        session_id,
                        now,
                        now,
                    ),
                )
                break
            except sqlite3.IntegrityError as exc:
                # Race on the idempotency key: return the original record.
                if idempotency_key:
                    existing = conn.execute(
                        "SELECT * FROM registrations WHERE idempotency_key = ?",
                        (idempotency_key,),
                    ).fetchone()
                    if existing:
                        return {"record": dict(existing), "idempotent": True}
                # Otherwise assume a rare reference collision and retry.
                reference = generate_reference()
        else:
            raise RuntimeError("Could not allocate a unique registration reference.")

        row = conn.execute(
            "SELECT * FROM registrations WHERE public_reference = ?", (reference,)
        ).fetchone()
        return {"record": dict(row), "idempotent": False}


def get_registration(registration_id: int) -> Optional[dict[str, Any]]:
    with database.get_connection() as conn:
        row = conn.execute(
            """SELECT r.*, ws.title AS session_title
               FROM registrations r LEFT JOIN walk_sessions ws ON r.session_id = ws.id
               WHERE r.id = ?""",
            (registration_id,),
        ).fetchone()
        return dict(row) if row else None


def get_registration_by_reference(reference: str) -> Optional[dict[str, Any]]:
    with database.get_connection() as conn:
        row = conn.execute(
            """SELECT r.*, ws.title AS session_title
               FROM registrations r LEFT JOIN walk_sessions ws ON r.session_id = ws.id
               WHERE r.public_reference = ?""",
            (reference,),
        ).fetchone()
        return dict(row) if row else None


def list_registrations(
    *,
    query: Optional[str] = None,
    status: Optional[str] = None,
    session_id: Optional[int] = None,
    page: int = 1,
    per_page: int = 25,
) -> dict[str, Any]:
    page = max(1, page)
    per_page = min(max(1, per_page), 100)
    clauses: list[str] = []
    params: list[Any] = []

    if query:
        like = f"%{query.strip()}%"
        clauses.append(
            "(r.full_name LIKE ? OR r.email LIKE ? OR r.public_reference LIKE ?)"
        )
        params.extend([like, like, like])
    if status:
        clauses.append("r.status = ?")
        params.append(status)
    if session_id is not None:
        clauses.append("r.session_id = ?")
        params.append(session_id)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with database.get_connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM registrations r LEFT JOIN walk_sessions ws "
            f"ON r.session_id = ws.id {where}",
            params,
        ).fetchone()["n"]
        offset = (page - 1) * per_page
        rows = conn.execute(
            f"SELECT {_LIST_COLUMNS} FROM registrations r "
            f"LEFT JOIN walk_sessions ws ON r.session_id = ws.id {where} "
            "ORDER BY r.created_at DESC, r.id DESC LIMIT ? OFFSET ?",
            [*params, per_page, offset],
        ).fetchall()

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),
    }


def registration_counts() -> dict[str, int]:
    with database.get_connection() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM registrations GROUP BY status"
        ).fetchall()
        counts = {status: 0 for status in STATUS_VALUES}
        for row in rows:
            counts[row["status"]] = row["n"]
        counts["total"] = sum(counts.values())
        return counts


def update_status(registration_id: int, status: str) -> Optional[dict[str, Any]]:
    with database.get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM registrations WHERE id = ?", (registration_id,)
        ).fetchone()
        if not existing:
            return None
        conn.execute(
            "UPDATE registrations SET status = ?, updated_at = ? WHERE id = ?",
            (status, utcnow(), registration_id),
        )
        row = conn.execute(
            "SELECT * FROM registrations WHERE id = ?", (registration_id,)
        ).fetchone()
        return dict(row)


def export_rows(
    *, query: Optional[str] = None, status: Optional[str] = None
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if query:
        like = f"%{query.strip()}%"
        clauses.append("(r.full_name LIKE ? OR r.email LIKE ? OR r.public_reference LIKE ?)")
        params.extend([like, like, like])
    if status:
        clauses.append("r.status = ?")
        params.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with database.get_connection() as conn:
        rows = conn.execute(
            "SELECT r.public_reference, r.full_name, r.email, r.experience_type, "
            "r.preferred_date, r.guest_count, r.status, r.created_at, r.updated_at, "
            "r.notes, ws.title AS session_title "
            "FROM registrations r LEFT JOIN walk_sessions ws ON r.session_id = ws.id "
            f"{where} ORDER BY r.created_at DESC",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def delete_registration(registration_id: int) -> bool:
    """Administrative cleanup helper (used to remove test records)."""
    with database.get_connection() as conn:
        cursor = conn.execute("DELETE FROM registrations WHERE id = ?", (registration_id,))
        return cursor.rowcount > 0


# --------------------------------------------------------------------------
# Walk sessions
# --------------------------------------------------------------------------

_SESSION_PUBLIC_COLUMNS = (
    "id, title, description, walk_date, start_time, duration_minutes, "
    "meeting_point, capacity, inclusions, status"
)

_SESSION_ADMIN_COLUMNS = (
    "ws.*, (SELECT COUNT(*) FROM registrations r WHERE r.session_id = ws.id) AS enquiry_count"
)


def create_session(
    *,
    title: str,
    description: str,
    walk_date: str,
    start_time: str,
    duration_minutes: int,
    meeting_point: str,
    capacity: Optional[int],
    inclusions: Optional[str],
) -> dict[str, Any]:
    """Create a session in DRAFT state (never published by accident)."""
    now = utcnow()
    with database.get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO walk_sessions (
                title, description, walk_date, start_time, duration_minutes,
                meeting_point, capacity, inclusions, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?)
            """,
            (
                title, description, walk_date, start_time, duration_minutes,
                meeting_point, capacity, inclusions, now, now,
            ),
        )
        row = conn.execute(
            "SELECT * FROM walk_sessions WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)


def get_session(session_id: int) -> Optional[dict[str, Any]]:
    with database.get_connection() as conn:
        row = conn.execute(
            f"SELECT {_SESSION_ADMIN_COLUMNS} FROM walk_sessions ws WHERE ws.id = ?",
            (session_id,),
        ).fetchone()
        return dict(row) if row else None


def update_session(
    session_id: int,
    *,
    title: str,
    description: str,
    walk_date: str,
    start_time: str,
    duration_minutes: int,
    meeting_point: str,
    capacity: Optional[int],
    inclusions: Optional[str],
) -> Optional[dict[str, Any]]:
    with database.get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM walk_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE walk_sessions SET
                title = ?, description = ?, walk_date = ?, start_time = ?,
                duration_minutes = ?, meeting_point = ?, capacity = ?,
                inclusions = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                title, description, walk_date, start_time, duration_minutes,
                meeting_point, capacity, inclusions, utcnow(), session_id,
            ),
        )
        row = conn.execute(
            "SELECT * FROM walk_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row)


def set_session_status(session_id: int, status: str) -> Optional[dict[str, Any]]:
    with database.get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM walk_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not existing:
            return None
        conn.execute(
            "UPDATE walk_sessions SET status = ?, updated_at = ? WHERE id = ?",
            (status, utcnow(), session_id),
        )
        row = conn.execute(
            "SELECT * FROM walk_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row)


def public_sessions() -> list[dict[str, Any]]:
    """Published, upcoming sessions only — what visitors may see."""
    with database.get_connection() as conn:
        rows = conn.execute(
            f"SELECT {_SESSION_PUBLIC_COLUMNS} FROM walk_sessions "
            "WHERE status = 'PUBLISHED' AND walk_date >= ? "
            "ORDER BY walk_date ASC, start_time ASC",
            (today_iso(),),
        ).fetchall()
        return [dict(r) for r in rows]


def list_sessions(
    *, query: Optional[str] = None, status: Optional[str] = None
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if query:
        like = f"%{query.strip()}%"
        clauses.append("(ws.title LIKE ? OR ws.meeting_point LIKE ?)")
        params.extend([like, like])
    if status:
        clauses.append("ws.status = ?")
        params.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with database.get_connection() as conn:
        rows = conn.execute(
            f"SELECT {_SESSION_ADMIN_COLUMNS} FROM walk_sessions ws {where} "
            "ORDER BY ws.walk_date DESC, ws.start_time DESC",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def session_counts() -> dict[str, int]:
    with database.get_connection() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM walk_sessions GROUP BY status"
        ).fetchall()
        counts = {status: 0 for status in SESSION_STATUS_VALUES}
        for row in rows:
            counts[row["status"]] = row["n"]
        counts["total"] = sum(counts.values())
        return counts


def session_eligible_for_interest(session: dict[str, Any]) -> bool:
    """A session accepts interest only when published and not in the past."""
    return (
        session is not None
        and session["status"] == "PUBLISHED"
        and session["walk_date"] >= today_iso()
    )


def delete_session(session_id: int) -> bool:
    """Administrative cleanup helper for test/demo records.

    Registrations that pointed at the session are kept and become general
    interest (session_id set to NULL) — nothing is deleted silently.
    """
    with database.get_connection() as conn:
        conn.execute(
            "UPDATE registrations SET session_id = NULL, updated_at = ? WHERE session_id = ?",
            (utcnow(), session_id),
        )
        cursor = conn.execute("DELETE FROM walk_sessions WHERE id = ?", (session_id,))
        return cursor.rowcount > 0