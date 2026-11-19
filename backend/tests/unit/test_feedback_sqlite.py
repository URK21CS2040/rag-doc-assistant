from pathlib import Path
from app.storage.repositories import SQLiteFeedbackRepository

def test_sqlite_feedback_persistence(tmp_path: Path):
    db_file = tmp_path / "feedback_test.db"
    repo1 = SQLiteFeedbackRepository(db_path=str(db_file))

    f_id = repo1.save_feedback(
        session_id="session_123",
        rating="thumbs_up",
        comment="Accurate answer with citations",
        question="What is the critical threshold?",
        answer="The threshold is 0.85 [1]."
    )
    assert f_id is not None

    record = repo1.get_feedback(f_id)
    assert record is not None
    assert record["session_id"] == "session_123"
    assert record["rating"] == "thumbs_up"
    assert record["comment"] == "Accurate answer with citations"
    assert record["question"] == "What is the critical threshold?"

    # Simulate backend restart by creating a new repository instance pointing to the same SQLite DB
    repo2 = SQLiteFeedbackRepository(db_path=str(db_file))
    reloaded_record = repo2.get_feedback(f_id)
    assert reloaded_record is not None
    assert reloaded_record["id"] == f_id
    assert reloaded_record["rating"] == "thumbs_up"
    assert reloaded_record["comment"] == "Accurate answer with citations"

