import json
import tempfile
from pathlib import Path

from src.database import DatabaseManager, BASE_DIR
from src.knowledge import KnowledgeEngine


def test_database_and_knowledge():
    db = DatabaseManager(BASE_DIR / "data" / "test_knowledge.db")
    db.init_db()

    note_id = db.add_note(
        title="Python Study Notes",
        content="Python is a popular language. It is used for data analysis and automation.",
        source_type="manual",
        tags="python, data",
        summary="Python is useful for data analysis.",
    )

    notes = db.search_notes("python")
    assert len(notes) >= 1
    assert notes[0]["title"] == "Python Study Notes"

    engine = KnowledgeEngine()
    summary = engine.summarize_text(
        "Python is very useful. It helps in automation and analysis. Data science depends on Python.",
        max_sentences=2,
    )
    assert "Python" in summary

    answer = engine.answer_question("What is Python used for?", notes)
    assert "source_title" in answer

    backup_path = db.export_backup()
    assert Path(backup_path).exists()

    with open(backup_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    assert "notes" in data

    db.delete_note(note_id)
    print("Database and knowledge tests passed.")


if __name__ == "__main__":
    test_database_and_knowledge()
