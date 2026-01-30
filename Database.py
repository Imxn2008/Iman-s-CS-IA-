import os
import sqlite3
from typing import Any

from flask import Flask, jsonify, request



DB_PATH = os.path.join(os.path.dirname(__file__), "subjects.db")
SLOT_COUNT = 5

app = Flask(__name__)


def _get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS subject_slots (
                slot INTEGER PRIMARY KEY,
                subject TEXT NOT NULL,
                current TEXT NOT NULL,
                target TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY,
                goal TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _load_subjects() -> list[dict[str, Any] | None]:
    init_db()
    subjects: list[dict[str, Any] | None] = [None] * SLOT_COUNT
    with _get_connection() as connection:
        rows = connection.execute(
            "SELECT slot, subject, current, target FROM subject_slots ORDER BY slot"
        ).fetchall()
    for row in rows:
        if 0 <= row["slot"] < SLOT_COUNT:
            subjects[row["slot"]] = {
                "subject": row["subject"],
                "current": row["current"],
                "target": row["target"],
            }
    return subjects


def _save_subjects(subjects: list[dict[str, Any] | None]) -> None:
    init_db()
    if len(subjects) != SLOT_COUNT:
        raise ValueError(f"Expected {SLOT_COUNT} slots, got {len(subjects)}.")

    with _get_connection() as connection:
        connection.execute("DELETE FROM subject_slots")
        for slot, item in enumerate(subjects):
            if not item:
                continue
            connection.execute(
                """
                INSERT INTO subject_slots (slot, subject, current, target)
                VALUES (?, ?, ?, ?)
                """,
                (
                    slot,
                    str(item.get("subject", "")),
                    str(item.get("current", "")),
                    str(item.get("target", "")),
                ),
            )


def save_goal(goal: str) -> None:
    init_db()
    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO goals (id, goal)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET
                goal = excluded.goal,
                updated_at = CURRENT_TIMESTAMP
            """,
            (goal,),
        )


def load_goal() -> str:
    init_db()
    with _get_connection() as connection:
        row = connection.execute(
            "SELECT goal FROM goals WHERE id = 1"
        ).fetchone()
    return row["goal"] if row else ""


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/api/subjects", methods=["GET"])
def get_subjects():
    return jsonify(_load_subjects())


@app.route("/api/subjects", methods=["POST"])
def set_subjects():
    payload = request.get_json(silent=True)
    if not isinstance(payload, list):
        return jsonify({"error": "Payload must be a list."}), 400

    try:
        _save_subjects(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"status": "ok"})


@app.route("/api/goal", methods=["GET"])
def get_goal():
    return jsonify({"goal": load_goal()})


@app.route("/api/goal", methods=["POST"])
def set_goal():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or "goal" not in payload:
        return jsonify({"error": "Payload must be a dict with 'goal' key."}), 400

    save_goal(payload["goal"])
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True) 


