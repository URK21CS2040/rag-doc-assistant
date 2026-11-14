from typing import Dict, Any
import uuid

class InMemoryFeedbackRepository:
    def __init__(self) -> None:
        self._storage: Dict[str, Dict[str, Any]] = {}

    def save_feedback(self, session_id: str, rating: str, comment: str | None) -> str:
        feedback_id = str(uuid.uuid4())
        self._storage[feedback_id] = {
            "session_id": session_id,
            "rating": rating,
            "comment": comment
        }
        return feedback_id
