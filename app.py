from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.database import DatabaseManager
from src.knowledge import KnowledgeEngine


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "knowledge.db"


st.set_page_config(page_title="Smart Knowledge Assistant", page_icon="🧠", layout="wide")


@st.cache_resource
def get_db_manager() -> DatabaseManager:
    return DatabaseManager(DB_PATH)


@st.cache_resource
def get_knowledge_engine() -> KnowledgeEngine:
    return KnowledgeEngine()


db = get_db_manager()
engine = get_knowledge_engine()


st.title("Smart Personal Knowledge Management Assistant")
st.caption("A beginner-friendly local knowledge base for notes, files, search, and answers.")

with st.sidebar:
    st.header("Quick actions")

    with st.form("manual_note_form"):
        st.subheader("Add a note")
        title = st.text_input("Title")
        content = st.text_area("Content", height=180)
        tags = st.text_input("Tags (comma separated)")
        submitted = st.form_submit_button("Save note")
        if submitted and content.strip():
            note_tags = tags or ", ".join(engine.suggest_tags(title, content, limit=5))
            note_id = db.add_note(
                title=title or "Untitled note",
                content=content,
                source_type="manual",
                tags=note_tags,
                summary=engine.summarize_text(content, max_sentences=2),
            )
            st.success(f"Saved note #{note_id}.")
            st.rerun()

    st.markdown("---")

    uploaded_file = st.file_uploader(
        "Upload a PDF, DOCX, or TXT file",
        type=["txt", "pdf", "docx"],
        accept_multiple_files=False,
    )
    if uploaded_file is not None:
        temp_path = BASE_DIR / "data" / uploaded_file.name
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(uploaded_file.getvalue())

        try:
            text = engine.extract_text_from_file(temp_path)
            suggested_tags = ", ".join(engine.suggest_tags(uploaded_file.name, text, limit=5))
            st.write("Preview:")
            st.code(text[:500] + ("..." if len(text) > 500 else ""))

            if st.button("Save uploaded file to knowledge base"):
                db.add_note(
                    title=uploaded_file.name,
                    content=text,
                    source_type="file",
                    source_path=str(temp_path),
                    tags=suggested_tags,
                    summary=engine.summarize_text(text, max_sentences=3),
                )
                st.success("Uploaded file saved.")
                st.rerun()
        except Exception as exc:
            st.error(f"Could not read this file: {exc}")

    st.markdown("---")
    st.subheader("Suggested tags")
    note_text_sample = st.text_area("Type some text to preview tag suggestions", height=100)
    if note_text_sample.strip():
        suggested = engine.suggest_tags("Preview", note_text_sample, limit=6)
        st.markdown(", ".join(suggested) if suggested else "No suggestions yet")


notes = db.get_all_notes()

stats = db.get_dashboard_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total notes", stats["total_notes"])
col2.metric("Unique tags", stats["tag_count"])
col3.metric("Top tag", stats["top_tags"][0] if stats["top_tags"] else "-")
col4.metric("Latest note", stats["latest_note"]["title"] if stats["latest_note"] else "-")

search_term = st.text_input("Search notes", placeholder="Example: project plan or Python")
if search_term:
    filtered_notes = db.search_notes(query=search_term)
else:
    filtered_notes = notes

if not filtered_notes:
    st.info("No notes found. Add a note or upload a file to get started.")
else:
    st.subheader("Notes")
    note_titles = [note["title"] for note in filtered_notes]
    selected_title = st.selectbox("Choose a note", note_titles, index=0)
    selected_note = next((note for note in filtered_notes if note["title"] == selected_title), filtered_notes[0])

    st.write("### Summary")
    st.write(selected_note.get("summary") or engine.summarize_text(selected_note.get("content", ""), max_sentences=3))

    st.write("### Tags")
    tags_display = selected_note.get("tags") or ""
    st.write(tags_display if tags_display else "No tags assigned")

    st.write("### Content")
    st.write(selected_note.get("content", ""))

    related = engine.related_notes(notes, selected_note.get("id"), limit=5)
    if related:
        st.write("### Related notes")
        for related_note in related:
            st.markdown(f"- {related_note.get('title', 'Untitled')} ({related_note.get('tags', 'No tags')})")

    delete_id = st.button(f"Delete note: {selected_note['title']}", key=f"delete_{selected_note['id']}")
    if delete_id:
        db.delete_note(selected_note["id"])
        st.success("Note deleted.")
        st.rerun()

st.markdown("---")

question = st.text_input("Ask a question about your knowledge base", placeholder="Example: What are the main ideas in my notes?")
if question:
    answer = engine.answer_question(question, notes)
    st.subheader("Answer")
    st.write(answer["answer"])
    st.caption(f"Best match: {answer['source_title']} (score: {answer['score']:.3f})")

st.markdown("---")

st.subheader("Export and backup")
backup_path = st.button("Create backup JSON")
if backup_path:
    result = db.export_backup()
    st.success(f"Backup created: {result}")

uploaded_backup = st.file_uploader("Restore a backup file", type=["json"], key="backup_restore")
if uploaded_backup is not None:
    restore_target = BASE_DIR / "backups" / uploaded_backup.name
    restore_target.parent.mkdir(parents=True, exist_ok=True)
    restore_target.write_bytes(uploaded_backup.getvalue())
    if st.button("Restore backup"):
        count = db.restore_backup(str(restore_target))
        st.success(f"Restored {count} notes from backup.")
        st.rerun()
