import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any


DEFAULT_DB_PATH = os.environ.get("SUBJECTS_DB_PATH", "subjects.db")
SLOT_COUNT = 5
SUBJECTS_KEY = "subjects"

# In-memory cache for the latest saved subjects payload.
subjects: dict[str, dict[str, str]] = {}


@contextmanager
def _get_connection(db_path: str = DEFAULT_DB_PATH):
    connection = sqlite3.connect(db_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    with _get_connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS subject_entries (
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_subjects(subject_data: dict[str, str], db_path: str = DEFAULT_DB_PATH) -> None:
    if not isinstance(subject_data, dict):
        raise TypeError("subject_data must be a dict of {name: value}.")

    init_db(db_path)
    with _get_connection(db_path) as connection:
        connection.executemany(
            """
            INSERT INTO subject_entries (name, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            [(name, value) for name, value in subject_data.items()],
        )


def save_subject(name: str, value: str, db_path: str = DEFAULT_DB_PATH) -> None:
    if not name:
        raise ValueError("name must be a non-empty string.")

    init_db(db_path)
    with _get_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO subject_entries (name, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (name, value),
        )


def load_subjects(db_path: str = DEFAULT_DB_PATH) -> dict[str, str]:
    init_db(db_path)
    with _get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT name, value FROM subject_entries ORDER BY name"
        ).fetchall()
    return {name: value for name, value in rows}


def _normalize_subject_payload(
    subject_list: list[dict[str, Any] | None],
    slot_count: int = SLOT_COUNT,
) -> dict[str, dict[str, str]]:
    if not isinstance(subject_list, list):
        raise TypeError("subject_list must be a list.")
    if len(subject_list) != slot_count:
        raise ValueError(f"Expected {slot_count} slots, got {len(subject_list)}.")

    normalized: dict[str, dict[str, str]] = {}
    for index, item in enumerate(subject_list):
        if not item:
            continue
        if not isinstance(item, dict):
            raise TypeError(f"subject_list[{index}] must be a dict or null.")
        normalized[str(index)] = {
            "subject": str(item.get("subject", "")).strip(),
            "current": str(item.get("current", "")).strip(),
            "target": str(item.get("target", "")).strip(),
        }
    return normalized


def save_subjects_snapshot(
    subject_list: list[dict[str, Any] | None],
    db_path: str = DEFAULT_DB_PATH,
    slot_count: int = SLOT_COUNT,
) -> None:
    global subjects
    subjects = _normalize_subject_payload(subject_list, slot_count)
    save_subject(SUBJECTS_KEY, json.dumps(subjects), db_path=db_path)


def load_subjects_snapshot(
    db_path: str = DEFAULT_DB_PATH,
    slot_count: int = SLOT_COUNT,
) -> list[dict[str, str] | None]:
    global subjects
    init_db(db_path)
    with _get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT value FROM subject_entries WHERE name = ?",
            (SUBJECTS_KEY,),
        ).fetchone()

    subjects = {}
    if row and row[0]:
        try:
            stored = json.loads(row[0])
        except json.JSONDecodeError:
            stored = {}
        if isinstance(stored, dict):
            for key, value in stored.items():
                if not isinstance(value, dict):
                    continue
                subjects[str(key)] = {
                    "subject": str(value.get("subject", "")).strip(),
                    "current": str(value.get("current", "")).strip(),
                    "target": str(value.get("target", "")).strip(),
                }

    return [subjects.get(str(i)) for i in range(slot_count)]


__all__ = [
    "DEFAULT_DB_PATH",
    "init_db",
    "save_subjects",
    "save_subject",
    "load_subjects",
    "save_subjects_snapshot",
    "load_subjects_snapshot",
    "subjects",
]
