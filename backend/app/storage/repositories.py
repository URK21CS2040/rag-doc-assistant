import sqlite3
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from app.config import settings

logger = logging.getLogger(__name__)

class SQLiteFeedbackRepository:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or settings.feedback_db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(path))

    def _init_db(self) -> None:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        rating TEXT NOT NULL,
                        comment TEXT,
                        question TEXT,
                        answer TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception:
            logger.exception("Failed to initialize SQLite feedback table")

    def save_feedback(
        self,
        session_id: str,
        rating: str,
        comment: Optional[str] = None,
        question: Optional[str] = None,
        answer: Optional[str] = None,
    ) -> str:
        feedback_id = str(uuid.uuid4())
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO feedback (id, session_id, rating, comment, question, answer)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (feedback_id, session_id, rating, comment, question, answer),
                )
                conn.commit()
            return feedback_id
        except Exception:
            logger.exception("Error saving feedback to SQLite")
            raise

    def get_feedback(self, feedback_id: str) -> Optional[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, session_id, rating, comment, question, answer, created_at FROM feedback WHERE id = ?",
                    (feedback_id,),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "session_id": row[1],
                        "rating": row[2],
                        "comment": row[3],
                        "question": row[4],
                        "answer": row[5],
                        "created_at": row[6],
                    }
        except Exception:
            logger.exception("Error fetching feedback by ID")
        return None

    def get_all_feedback(self) -> List[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, session_id, rating, comment, question, answer, created_at FROM feedback ORDER BY created_at DESC")
                rows = cursor.fetchall()
                return [
                    {
                        "id": r[0],
                        "session_id": r[1],
                        "rating": r[2],
                        "comment": r[3],
                        "question": r[4],
                        "answer": r[5],
                        "created_at": r[6],
                    }
                    for r in rows
                ]
        except Exception:
            logger.exception("Error fetching all feedback")
            return []


class InMemoryFeedbackRepository:
    def __init__(self) -> None:
        self._storage: Dict[str, Dict[str, Any]] = {}

    def save_feedback(
        self,
        session_id: str,
        rating: str,
        comment: Optional[str] = None,
        question: Optional[str] = None,
        answer: Optional[str] = None,
    ) -> str:
        feedback_id = str(uuid.uuid4())
        self._storage[feedback_id] = {
            "id": feedback_id,
            "session_id": session_id,
            "rating": rating,
            "comment": comment,
            "question": question,
            "answer": answer,
        }
        return feedback_id
