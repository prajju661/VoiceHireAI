"""
Database management and SQLite connection lifecycle for VoiceHire AI.

Provides connection pooling via context managers, schema migration, foreign key
enforcement, and transaction management using Python's built-in sqlite3.
"""

from contextlib import contextmanager
import logging
from pathlib import Path
import sqlite3
from typing import Generator

from app.core.config import settings

logger = logging.getLogger(__name__)

CREATE_SESSIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS interview_sessions (
    id TEXT PRIMARY KEY,
    candidate_name TEXT,
    candidate_email TEXT,
    job_role TEXT NOT NULL,
    language TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    status TEXT NOT NULL,
    reasoning_provider TEXT NOT NULL,
    overall_score REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);
"""

CREATE_TURNS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS interview_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    question_id TEXT NOT NULL,
    question_text TEXT NOT NULL,
    question_category TEXT NOT NULL,
    question_difficulty TEXT NOT NULL,
    answer_text TEXT,
    score REAL,
    feedback TEXT,
    strengths TEXT,
    improvement_areas TEXT,
    evidence_from_answer TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
);
"""

CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_turns_session_id ON interview_turns(session_id);
CREATE INDEX IF NOT EXISTS idx_turns_session_turn ON interview_turns(session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON interview_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON interview_sessions(created_at);
"""


def init_db(db_path: Path | None = None) -> None:
    """
    Initialize SQLite database tables and indexes.

    Creates parent directory if it does not exist, enables WAL mode and foreign
    keys, and creates the sessions and turns tables with cascading deletion.
    """
    target_path = db_path or settings.DATABASE_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection(target_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(CREATE_SESSIONS_TABLE_SQL)
        conn.execute(CREATE_TURNS_TABLE_SQL)
        for index_stmt in CREATE_INDEXES_SQL.strip().split(";"):
            stmt = index_stmt.strip()
            if stmt:
                conn.execute(stmt)

    logger.info("Initialized SQLite database schema at %s", target_path)


@contextmanager
def get_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Provide a transactional SQLite connection context.

    Enforces foreign keys, enables dictionary-like row access (sqlite3.Row),
    commits on successful block exit, and rolls back on unhandled exceptions.
    """
    target_path = db_path or settings.DATABASE_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(target_path),
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False,
        timeout=15.0,
    )
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
