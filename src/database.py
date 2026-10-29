import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "knowledge.db"
BACKUP_DIR = BASE_DIR / "backups"


class DatabaseManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_type TEXT DEFAULT 'manual',
                    source_path TEXT,
                    tags TEXT,
                    summary TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_notes_tags ON notes(tags)"
            )

    def add_note(
        self,
        title: str,
        content: str,
        source_type: str = "manual",
        source_path: Optional[str] = None,
        tags: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> int:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notes (title, content, source_type, source_path, tags, summary, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title.strip() or "Untitled Note",
                    content.strip(),
                    source_type,
                    source_path,
                    tags or "",
                    summary or "",
                    timestamp,
                    timestamp,
                ),
            )
            return int(cursor.lastrowid)

    def get_all_notes(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM notes ORDER BY updated_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_note_by_id(self, note_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM notes WHERE id = ?",
                (note_id,),
            ).fetchone()
            return dict(row) if row else None

    def search_notes(self, query: str = "", tag: str = "") -> List[Dict[str, Any]]:
        query = (query or "").strip()
        tag = (tag or "").strip()

        sql = "SELECT * FROM notes WHERE 1=1"
        params: List[Any] = []

        if query:
            sql += " AND (LOWER(title) LIKE LOWER(?) OR LOWER(content) LIKE LOWER(?) OR LOWER(tags) LIKE LOWER(?))"
            like_query = f"%{query}%"
            params.extend([like_query, like_query, like_query])

        if tag:
            sql += " AND LOWER(tags) LIKE LOWER(?)"
            params.append(f"%{tag}%")

        sql += " ORDER BY updated_at DESC"

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def delete_note(self, note_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            return cursor.rowcount > 0

    def update_note(self, note_id: int, title: str, content: str, tags: Optional[str] = None, summary: Optional[str] = None) -> bool:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE notes
                SET title = ?, content = ?, tags = ?, summary = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    title.strip() or "Untitled Note",
                    content.strip(),
                    tags or "",
                    summary or "",
                    timestamp,
                    note_id,
                ),
            )
            return cursor.rowcount > 0

    def get_dashboard_stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            total_notes = conn.execute("SELECT COUNT(*) AS count FROM notes").fetchone()["count"]
            latest = conn.execute(
                "SELECT title, created_at FROM notes ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            tags = conn.execute(
                "SELECT tags FROM notes WHERE tags IS NOT NULL AND tags != ''"
            ).fetchall()

        tag_list: List[str] = []
        for row in tags:
            tag_list.extend([item.strip() for item in row["tags"].split(",") if item.strip()])

        return {
            "total_notes": total_notes,
            "latest_note": dict(latest) if latest else None,
            "tag_count": len(set(tag_list)),
            "top_tags": self._top_tags(tag_list),
        }

    @staticmethod
    def _top_tags(tag_list: List[str], limit: int = 6) -> List[str]:
        counts: Dict[str, int] = {}
        for tag in tag_list:
            counts[tag] = counts.get(tag, 0) + 1
        sorted_tags = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [tag for tag, _ in sorted_tags[:limit]]

    def export_backup(self) -> str:
        note_data = self.get_all_notes()
        payload = {
            "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "notes": note_data,
        }
        file_name = f"knowledge_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = BACKUP_DIR / file_name
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(file_path)

    def restore_backup(self, file_path: str) -> int:
        restore_path = Path(file_path)
        with restore_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        count = 0
        for note in payload.get("notes", []):
            title = note.get("title", "Untitled Note")
            content = note.get("content", "")
            tags = note.get("tags", "")
            summary = note.get("summary", "")
            source_type = note.get("source_type", "manual")
            source_path = note.get("source_path")

            self.add_note(
                title=title,
                content=content,
                source_type=source_type,
                source_path=source_path,
                tags=tags,
                summary=summary,
            )
            count += 1
        return count
